from numbers import Number
import re
from typing import List, Sequence

from sqlglot import exp, parse_one


LABELS = {
    "uf": "UF",
    "municipio": "município",
    "município": "município",
    "ibge": "código IBGE",
    "regiao": "região",
    "região": "região",
    "total": "total",
    "total_registros": "total de registros",
    "leitos_sus": "leitos SUS",
    "leitos_totais": "total de leitos existentes",
    "percentual_sus": "proporção de leitos SUS (%)",
    "total_doses": "número de doses registradas",
    "total_uti_beds": "quantidade de leitos de UTI",
    "total_srag": "número de notificações de SRAG",
    "total_ubs": "quantidade de UBS",
    "total_municipios": "quantidade de municípios",
}

DIMENSION_COLUMNS = {
    "uf", "estado", "municipio", "município", "ibge", "co_mun_not",
    "co_mun_res", "cnes", "regiao", "região", "codigo", "código",
}

INSIGHT_PREVIEW_ROWS = 3


def extract_output_columns(sql: str) -> List[str]:
    try:
        parsed = parse_one(sql, read="clickhouse")
        select = parsed if isinstance(parsed, exp.Select) else parsed.find(exp.Select)
        if not select:
            return []
        columns = []
        for expression in select.expressions:
            name = expression.alias_or_name
            if name and name != "*":
                columns.append(name)
            elif isinstance(expression, exp.Count):
                columns.append("total_registros")
            elif isinstance(expression, exp.Sum):
                columns.append("total")
            elif isinstance(expression, exp.Avg):
                columns.append("media")
            else:
                columns.append(expression.sql(dialect="clickhouse"))
        return columns
    except Exception:
        return []


def _format_value(value) -> str:
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    if isinstance(value, float):
        return f"{value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    return str(value)


def _label(column: str) -> str:
    return LABELS.get(column.lower(), column.replace("_", " "))


def _format_dimension(column: str, value) -> str:
    normalized = column.lower()
    if normalized in {"cs_sexo", "sexo", "paciente_enumsexobiologico"}:
        labels = {
            "M": "Masculino",
            "F": "Feminino",
            "I": "Ignorado ou indeterminado",
        }
        return labels.get(str(value).upper(), str(value))
    if normalized in {"ibge", "co_mun_not", "co_mun_res"}:
        return f"município (código IBGE {value})"
    if normalized in {"municipio", "município"}:
        return str(value)
    if normalized == "cnes":
        return f"estabelecimento (CNES {value})"
    return str(value)


def _extract_limit(sql: str):
    match = re.search(r"\bLIMIT\s+(\d+)\b", sql, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _scalar_label(column: str, question: str) -> str:
    normalized = question.lower()
    if column.lower() == "total_registros":
        if any(term in normalized for term in ("vacina", "vacinação", "dose")):
            return "Total de registros de doses aplicadas"
        if "srag" in normalized:
            return "Total de registros de SRAG"
        if "ubs" in normalized:
            return "Total de UBS"
        return "Total de registros"
    return _label(column).capitalize()


def build_result_highlights(
    sql: str,
    rows: Sequence[Sequence],
    max_items: int = INSIGHT_PREVIEW_ROWS,
    question: str = "",
) -> List[str]:
    """Produz poucos destaques legíveis, mantendo a tabela como fonte do detalhe."""

    if not rows or max_items <= 0:
        return []
    normalized_rows = [tuple(row) if isinstance(row, (list, tuple)) else (row,) for row in rows]
    width = len(normalized_rows[0])
    columns = extract_output_columns(sql)
    if len(columns) != width:
        columns = [f"coluna_{index + 1}" for index in range(width)]

    numeric_indices = [
        index for index in range(width)
        if columns[index].lower() not in DIMENSION_COLUMNS
        and any(isinstance(row[index], Number) and not isinstance(row[index], bool) for row in normalized_rows)
    ]
    dimension_indices = [index for index in range(width) if index not in numeric_indices]

    highlights = []
    for row in normalized_rows[:max_items]:
        if dimension_indices and numeric_indices:
            dimension = ", ".join(
                _format_dimension(columns[index], row[index]) for index in dimension_indices
            )
            metrics = ", ".join(
                f"{_contextual_metric_label(columns[index], question)}: {_format_value(row[index])}"
                for index in numeric_indices
            )
            highlights.append(f"{dimension} — {metrics}")
        else:
            highlights.append(
                ", ".join(
                    f"{_label(column)}: {_format_value(value)}"
                    for column, value in zip(columns, row)
                )
            )
    return highlights


def _contextual_metric_label(column: str, question: str) -> str:
    normalized_column = column.lower()
    normalized_question = question.lower()
    if normalized_column == "total" and "srag" in normalized_question:
        return "casos de SRAG"
    if normalized_column == "total" and any(term in normalized_question for term in ("ubs", "unidade básica")):
        return "quantidade de UBS"
    return _label(column)


def build_factual_summary(sql: str, rows: Sequence[Sequence], question: str = "") -> str:
    """Produz uma descrição derivada somente dos valores retornados."""
    if not rows:
        return "Nenhum registro foi retornado."

    normalized_rows = [tuple(row) if isinstance(row, (list, tuple)) else (row,) for row in rows]
    width = len(normalized_rows[0])
    columns = extract_output_columns(sql)
    if len(columns) != width:
        columns = [f"coluna_{index + 1}" for index in range(width)]

    if width == 1:
        if len(normalized_rows) == 1:
            return f"{_scalar_label(columns[0], question)}: {_format_value(normalized_rows[0][0])}."
        values = ", ".join(_format_value(row[0]) for row in normalized_rows[:10])
        return f"Primeiros valores de {_label(columns[0])}: {values}."

    numeric_indices = [
        index for index in range(width)
        if columns[index].lower() not in DIMENSION_COLUMNS
        and any(isinstance(row[index], Number) and not isinstance(row[index], bool) for row in normalized_rows)
    ]
    dimension_indices = [index for index in range(width) if index not in numeric_indices]

    normalized_question = question.lower()
    is_distribution = any(
        term in normalized_question
        for term in ("distribuição", "distribuicao", "por sexo", "por categoria", "por tipo")
    )
    listing_terms = (
        "quais", "liste", "listar", "apresente", "respectivos",
        "por estado", "por uf", "por município", "por municipio", "por cidade",
        "por região", "por regiao",
    )
    is_listing = any(term in normalized_question for term in listing_terms)

    if is_distribution and len(numeric_indices) == 1 and dimension_indices:
        metric_index = numeric_indices[0]
        numeric_values = [
            row[metric_index]
            for row in normalized_rows
            if isinstance(row[metric_index], Number) and not isinstance(row[metric_index], bool)
        ]
        total = sum(numeric_values)
        preview = []
        for row in normalized_rows[:INSIGHT_PREVIEW_ROWS]:
            dimension = ", ".join(
                _format_dimension(columns[index], row[index]) for index in dimension_indices
            )
            value = row[metric_index]
            percentage = (float(value) / float(total) * 100.0) if total else 0.0
            preview.append(
                f"{dimension}: {_format_value(value)} ({_format_value(percentage)}%)"
            )
        remaining = len(normalized_rows) - len(preview)
        suffix = "" if remaining <= 0 else f" Consulte a tabela para as outras {remaining} categorias."
        return "Distribuição dos resultados: " + "; ".join(preview) + "." + suffix

    if dimension_indices and is_listing:
        preview = build_result_highlights(sql, normalized_rows, question=question)
        remaining = len(normalized_rows) - len(preview)
        suffix = "" if remaining <= 0 else f" Consulte a tabela para os outros {remaining} resultados retornados."
        result_word = "resultado" if len(normalized_rows) == 1 else "resultados"
        limit = _extract_limit(sql)
        if limit is not None and len(normalized_rows) >= limit:
            prefix = f"A consulta retornou os primeiros {len(normalized_rows)} {result_word} devido ao limite aplicado"
        else:
            prefix = f"Foram encontrados {len(normalized_rows)} {result_word}"
        return prefix + ". Destaques: " + "; ".join(preview) + "." + suffix

    if numeric_indices and dimension_indices:
        statements = []
        for metric_index in numeric_indices:
            candidates = [row for row in normalized_rows if isinstance(row[metric_index], Number)]
            if not candidates:
                continue
            leader = max(candidates, key=lambda row: row[metric_index])
            dimension = ", ".join(
                _format_dimension(columns[index], leader[index]) for index in dimension_indices
            )
            statements.append(
                f"maior {_label(columns[metric_index])}: {dimension} ({_format_value(leader[metric_index])})"
            )
        if statements:
            return "Nos dados retornados, " + "; ".join(statements) + "."

    first = normalized_rows[0]
    pairs = ", ".join(f"{_label(column)}={_format_value(value)}" for column, value in zip(columns, first))
    return f"Primeiro resultado: {pairs}."


def should_use_deterministic_interpretation(question: str, factual_summary: str) -> bool:
    """Evita LLM em rankings cuja resposta já pode ser derivada sem ambiguidade."""
    normalized = question.lower()
    ranking_terms = ("maior", "maiores", "mais ", "menor", "menores", "ranking", "highest", "lowest")
    is_ranking = factual_summary.startswith("Nos dados retornados, maior") and any(
        term in normalized for term in ranking_terms
    )
    is_listing = factual_summary.startswith(("Foram encontrados", "A consulta retornou os primeiros")) and any(
        term in normalized for term in (
            "quais", "liste", "listar", "apresente", "respectivos",
            "por estado", "por uf", "por município", "por municipio", "por cidade",
            "por região", "por regiao",
        )
    )
    is_scalar = factual_summary.lower().startswith(("total de ", "media:", "média:"))
    is_comparison = factual_summary.startswith("Nos dados retornados,") and any(
        term in normalized for term in ("compare", "comparar", "comparação", "comparacao", "versus")
    )
    is_distribution = factual_summary.startswith("Distribuição dos resultados:")
    return is_ranking or is_listing or is_scalar or is_comparison or is_distribution


def is_low_information_interpretation(insight: str, factual_summary: str) -> bool:
    """Detecta respostas genéricas que não aproveitam os fatos já calculados."""

    normalized = (insight or "").strip().lower()
    if not normalized:
        return True
    generic_markers = (
        "consulta retornou",
        "primeiros dados",
        "resultado da consulta está disponível",
        "consulte a tabela",
    )
    if any(marker in normalized for marker in generic_markers):
        return True
    return len(normalized) < 20 and len(factual_summary) > len(normalized)
