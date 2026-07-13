import json
import re
import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

from config.datasets import DATASETS_CONFIG
from metadata.loader import load_metadata


def _ddl_tables() -> dict[str, set[str]]:
    sql = (PROJECT_ROOT / "init_all_tables.sql").read_text(encoding="utf-8")
    tables: dict[str, set[str]] = {}

    pattern = re.compile(
        r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\((.*?)\)\s*ENGINE",
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(sql):
        table_name = match.group(1).lower()
        columns = set()
        for raw_line in match.group(2).splitlines():
            line = raw_line.strip().rstrip(",")
            if not line or line.startswith("--"):
                continue
            columns.add(line.split()[0].strip("`").lower())
        tables[table_name] = columns

    return tables


class SchemaConsistencyTests(unittest.TestCase):
    def test_every_configured_table_exists_in_bootstrap(self):
        ddl_tables = _ddl_tables()
        missing = {
            dataset_id: config["table_name"]
            for dataset_id, config in DATASETS_CONFIG.items()
            if config["table_name"].lower() not in ddl_tables
        }
        self.assertEqual({}, missing)

    def test_every_prompted_metadata_column_exists_in_bootstrap(self):
        ddl_tables = _ddl_tables()
        missing_by_dataset = {}

        for dataset_id, config in DATASETS_CONFIG.items():
            metadata = json.loads(load_metadata(dataset_id))
            schema_columns = metadata.get("colunas_principais") or metadata.get("columns") or {}
            metadata_columns = {column.lower() for column in schema_columns}
            physical_columns = ddl_tables.get(config["table_name"].lower(), set())
            missing = sorted(metadata_columns - physical_columns)
            if missing:
                missing_by_dataset[dataset_id] = missing

        self.assertEqual({}, missing_by_dataset)


if __name__ == "__main__":
    unittest.main()
