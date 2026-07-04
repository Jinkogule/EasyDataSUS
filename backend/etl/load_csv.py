#!/usr/bin/env python3
"""Carga unificada e substitutiva dos datasets configurados no EasyDataSUS."""

import argparse
import csv
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import clickhouse_connect
from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from config.datasets import DATASETS_CONFIG, get_table_name


load_dotenv(BACKEND_DIR / ".env")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

ENCODINGS = ("utf-8-sig", "latin-1", "cp1252")
NULL_MARKERS = {"", "null", "none", "nan", "nat", "n/a"}
DATE32_COLUMNS = {
    "vacinacao": {"paciente_dataNascimento"},
    "srag": {"dt_nasc"},
}


def get_clickhouse_client():
    return clickhouse_connect.get_client(
        host=os.getenv("CLICKHOUSE_HOST", "localhost"),
        port=int(os.getenv("CLICKHOUSE_PORT", "8123")),
        username=os.getenv("CLICKHOUSE_ADMIN_USER", "easydatasus_admin"),
        password=os.getenv("CLICKHOUSE_ADMIN_PASSWORD", "easydatasus_admin"),
        database=os.getenv("CLICKHOUSE_DATABASE", "default"),
        connect_timeout=10,
    )


def _dataset_files(dataset: str, explicit_file: str = None) -> List[Path]:
    if explicit_file:
        path = Path(explicit_file).expanduser().resolve()
        return [path]

    configured = DATASETS_CONFIG[dataset].get("csv_path")
    configured_path = (PROJECT_ROOT / configured).resolve() if configured else None
    dataset_dir = BACKEND_DIR / "data" / "datasets" / dataset
    files = sorted(dataset_dir.glob("*.csv"))
    if configured_path and configured_path.exists() and configured_path not in files:
        files.insert(0, configured_path)
    return files


def _open_csv(path: Path):
    last_error = None
    for encoding in ENCODINGS:
        try:
            handle = path.open("r", encoding=encoding, newline="")
            handle.read(65536)
            handle.seek(0)
            reader = csv.DictReader(handle, delimiter=";")
            if reader.fieldnames:
                return handle, reader, encoding
            handle.close()
        except UnicodeDecodeError as exc:
            last_error = exc
    raise ValueError(f"Não foi possível ler {path} com os encodings suportados: {last_error}")


def _table_schema(client, table_name: str) -> List[Tuple[str, str]]:
    rows = client.query(f"DESCRIBE TABLE {table_name}").result_rows
    return [(str(row[0]), str(row[1])) for row in rows]


def _ensure_date32_columns(client, datasets: Sequence[str]) -> None:
    selected_tables = {get_table_name(dataset) for dataset in datasets}
    for table_name, columns in DATE32_COLUMNS.items():
        if table_name not in selected_tables:
            continue
        schema = dict(_table_schema(client, table_name))
        for column_name in columns:
            if schema.get(column_name) == "Nullable(Date)":
                logger.info(
                    "Atualizando %s.%s de Nullable(Date) para Nullable(Date32)...",
                    table_name,
                    column_name,
                )
                client.command(
                    f"ALTER TABLE {table_name} MODIFY COLUMN {column_name} Nullable(Date32)"
                )


def _base_type(type_name: str) -> Tuple[str, bool]:
    nullable = type_name.startswith("Nullable(")
    base = type_name[len("Nullable("):-1] if nullable else type_name
    if base.startswith("LowCardinality("):
        base = base[len("LowCardinality("):-1]
    return base, nullable


def _parse_date(value: str, nullable: bool, base_type: str = "Date"):
    normalized = value.strip()
    if base_type == "Date32":
        minimum, maximum = date(1900, 1, 1), date(2299, 12, 31)
    else:
        minimum, maximum = date(1970, 1, 1), date(2149, 6, 6)

    if normalized.lower() in NULL_MARKERS:
        return None if nullable else minimum
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y%m%d", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(normalized[:10], fmt).date()
            return parsed if minimum <= parsed <= maximum else (None if nullable else minimum)
        except ValueError:
            continue
    return None if nullable else minimum


def _convert_value(value, type_name: str):
    base_type, nullable = _base_type(type_name)
    normalized = "" if value is None else str(value).strip()
    is_null = normalized.lower() in NULL_MARKERS
    if is_null and nullable:
        return None

    if base_type in {"Date", "Date32"}:
        return _parse_date(normalized, nullable, base_type)
    if base_type.startswith(("Int", "UInt")):
        if is_null:
            return 0
        try:
            return int(float(normalized.replace(",", ".")))
        except ValueError:
            return None if nullable else 0
    if base_type.startswith("Float"):
        if is_null:
            return 0.0
        try:
            return float(normalized.replace(",", "."))
        except ValueError:
            return None if nullable else 0.0
    return "" if is_null and not nullable else (None if is_null else normalized)


def _header_mapping(fieldnames: Sequence[str], schema: Sequence[Tuple[str, str]]) -> Dict[str, str]:
    source_by_lower = {(name or "").strip().strip('"').lower(): name for name in fieldnames}
    return {
        column_name: source_by_lower[column_name.lower()]
        for column_name, _ in schema
        if column_name.lower() in source_by_lower
    }


def _preflight(client, datasets: Sequence[str], explicit_file: str = None):
    plans = {}
    for dataset in datasets:
        table_name = get_table_name(dataset)
        schema = _table_schema(client, table_name)
        files = _dataset_files(dataset, explicit_file if len(datasets) == 1 else None)
        if not files or any(not path.exists() for path in files):
            raise FileNotFoundError(f"CSV não encontrado para {dataset}: {files}")

        file_plans = []
        for path in files:
            handle, reader, encoding = _open_csv(path)
            try:
                mapping = _header_mapping(reader.fieldnames or [], schema)
            finally:
                handle.close()
            if not mapping:
                raise ValueError(f"Nenhuma coluna de {path.name} corresponde à tabela {table_name}")
            file_plans.append((path, encoding, mapping))
        plans[dataset] = {"table": table_name, "schema": schema, "files": file_plans}
    return plans


def _iter_batches(
    path: Path,
    encoding: str,
    schema: Sequence[Tuple[str, str]],
    mapping: Dict[str, str],
    batch_size: int,
) -> Iterable[List[Tuple]]:
    with path.open("r", encoding=encoding, newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        batch = []
        for row in reader:
            converted = tuple(
                _convert_value(row.get(mapping.get(column_name)), type_name)
                for column_name, type_name in schema
            )
            batch.append(converted)
            if len(batch) >= batch_size:
                yield batch
                batch = []
        if batch:
            yield batch


def _truncate_tables(client, plans) -> None:
    for plan in plans.values():
        logger.info("Limpando tabela %s...", plan["table"])
        client.command(f"TRUNCATE TABLE {plan['table']}")


def _load_plan(client, dataset: str, plan, batch_size: int) -> int:
    table_name = plan["table"]
    schema = plan["schema"]
    columns = [column_name for column_name, _ in schema]
    total = 0
    for path, encoding, mapping in plan["files"]:
        logger.info("Carregando %s em %s (%s)...", path.name, table_name, encoding)
        for batch in _iter_batches(path, encoding, schema, mapping, batch_size):
            client.insert(table_name, batch, column_names=columns)
            total += len(batch)
            if total % (batch_size * 10) == 0:
                logger.info("%s: %s registros carregados", dataset, f"{total:,}")
    database_total = client.query(f"SELECT count() FROM {table_name}").result_rows[0][0]
    logger.info("%s concluído: %s registros", dataset, f"{database_total:,}")
    return int(database_total)


def reload_datasets(
    datasets: Sequence[str],
    explicit_file: str = None,
    batch_size: int = 5000,
    dry_run: bool = False,
) -> Dict[str, int]:
    unknown = [dataset for dataset in datasets if dataset not in DATASETS_CONFIG]
    if unknown:
        raise ValueError(f"Datasets não configurados: {', '.join(unknown)}")
    if explicit_file and len(datasets) != 1:
        raise ValueError("--file exige exatamente um --dataset")

    client = get_clickhouse_client()
    if not dry_run:
        _ensure_date32_columns(client, datasets)
    plans = _preflight(client, datasets, explicit_file)
    for dataset, plan in plans.items():
        logger.info(
            "Pré-validação %s: tabela=%s, arquivos=%s, colunas=%d",
            dataset,
            plan["table"],
            ", ".join(path.name for path, _, _ in plan["files"]),
            len(plan["schema"]),
        )

    if dry_run:
        logger.info("Dry-run concluído: nenhuma tabela foi alterada")
        return {}

    _truncate_tables(client, plans)
    return {
        dataset: _load_plan(client, dataset, plan, batch_size)
        for dataset, plan in plans.items()
    }


def load_csv(csv_path: str = None, dataset: str = None, batch_size: int = 5000):
    """Compatibilidade programática: sem dataset recarrega todas as bases."""
    datasets = [dataset] if dataset else list(DATASETS_CONFIG.keys())
    return reload_datasets(datasets, explicit_file=csv_path, batch_size=batch_size)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Substitui integralmente os dados das bases selecionadas no ClickHouse"
    )
    parser.add_argument("--dataset", choices=sorted(DATASETS_CONFIG), help="Recarrega somente este dataset")
    parser.add_argument("--file", help="CSV alternativo; exige --dataset")
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument("--dry-run", action="store_true", help="Valida arquivos e schemas sem apagar dados")
    args = parser.parse_args()

    datasets = [args.dataset] if args.dataset else list(DATASETS_CONFIG.keys())
    try:
        results = reload_datasets(
            datasets,
            explicit_file=args.file,
            batch_size=args.batch_size,
            dry_run=args.dry_run,
        )
    except Exception as exc:
        logger.exception("Carga abortada: %s", exc)
        return 1

    if results:
        logger.info("Carga completa: %s", ", ".join(f"{key}={value:,}" for key, value in results.items()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
