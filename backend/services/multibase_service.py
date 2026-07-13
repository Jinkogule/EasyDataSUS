import json
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from config.datasets import DATASETS_CONFIG, get_table_name, get_dataset_config
from llm.router import get_llm
from metadata.loader import load_metadata
from services.relationship_service import Relationship, relationship_service
from services.sql_service import extract_sql

logger = logging.getLogger(__name__)

try:
    from sqlglot import exp, parse_one
except Exception as exc:  # pragma: no cover - fail closed when dependency is missing
    raise RuntimeError(
        "sqlglot is required for multibase SQL validation. Install backend requirements before running the application."
    ) from exc


@dataclass(frozen=True)
class DatasetSelection:
    datasets: List[str]
    cross_dataset: bool
    reason: str
    routing_mode: str


@dataclass(frozen=True)
class SqlValidationResult:
    valid: bool
    tables: List[str]
    joins: List[str]
    ctes: List[str]
    errors: List[str]


class MultibaseService:
    """Coordena seleção de datasets, prompt multibase e validação estrutural."""

    def __init__(self, relationship_service_instance=relationship_service):
        self.relationship_service = relationship_service_instance

    def select_datasets(self, question: str, model_name: str, candidate_datasets: Sequence[str]) -> DatasetSelection:
        candidates = [dataset for dataset in candidate_datasets if dataset in DATASETS_CONFIG]
        if not candidates:
            candidates = list(DATASETS_CONFIG.keys())

        prompt_lines = [
            "Selecione um ou mais datasets para a pergunta abaixo.",
            "Responda SOMENTE com JSON válido no formato:",
            '{"datasets": ["id"], "cross_dataset": false, "reason": "..."}',
            "Se a pergunta exigir mais de uma base, marque cross_dataset como true.",
            "Não invente datasets inexistentes.",
            "",
            f"Pergunta: {question}",
            "",
            "Datasets disponíveis:"
        ]

        for dataset_id in candidates:
            config = get_dataset_config(dataset_id)
            prompt_lines.append(
                f"- {dataset_id}: {config.get('name', '')} | {config.get('dominio', '')} | {config.get('description', '')}"
            )

        prompt_lines.append("")
        prompt_lines.append("Exemplos mínimos de intenção:")
        prompt_lines.append("- SRAG + UBS: comparar notificações com cobertura territorial/assistencial")
        prompt_lines.append("- Vacinação + Leitos: analisar cobertura versus capacidade hospitalar")

        try:
            llm = get_llm(model_name)
            response = llm.generate("\n".join(prompt_lines))
            parsed = self._parse_selection_response(response, candidates)
            if parsed:
                return parsed
        except Exception as exc:
            logger.warning(f"Falha na seleção por LLM: {exc}")

        fallback = self._fallback_selection(question, candidates)
        return DatasetSelection(
            datasets=fallback,
            cross_dataset=len(fallback) > 1,
            reason="Fallback heurístico por palavras-chave",
            routing_mode="fallback",
        )

    def _parse_selection_response(self, response: str, valid_datasets: Sequence[str]) -> Optional[DatasetSelection]:
        if not response:
            return None

        try:
            payload = json.loads(response)
        except Exception:
            match = re.search(r"\{.*\}", response, re.DOTALL)
            if not match:
                return None
            try:
                payload = json.loads(match.group(0))
            except Exception:
                return None

        datasets = payload.get("datasets")
        if not isinstance(datasets, list):
            return None

        validated = [dataset for dataset in datasets if dataset in valid_datasets and dataset in DATASETS_CONFIG]
        if not validated:
            return None

        reason = str(payload.get("reason", ""))
        cross_dataset = bool(payload.get("cross_dataset", len(validated) > 1))
        return DatasetSelection(
            datasets=validated,
            cross_dataset=cross_dataset,
            reason=reason,
            routing_mode="llm",
        )

    def _fallback_selection(self, question: str, candidate_datasets: Sequence[str]) -> List[str]:
        q = question.lower()
        detected = []
        keyword_map = {
            "covid-19-vacinacao": ["vacina", "vacinação", "covid", "dose", "pfizer", "astrazeneca"],
            "leitos": ["leito", "leitos", "uti", "hospital", "capacidade"],
            "surtos-srag": ["srag", "febre", "tosse", "dispneia", "notificação"],
            "atencao-basica": ["ubs", "atenção primária", "cnes", "bairro", "ibge"],
        }

        for dataset_id in candidate_datasets:
            keywords = keyword_map.get(dataset_id, [])
            if sum(1 for keyword in keywords if keyword in q) > 0:
                detected.append(dataset_id)

        return detected[:2] if detected else [candidate_datasets[0]]

    def build_multibase_context(self, datasets: Sequence[str], relationships: Sequence[Relationship]) -> Dict[str, object]:
        metadata_by_dataset = {}
        for dataset_id in datasets:
            metadata_by_dataset[dataset_id] = json.loads(load_metadata(dataset_id))

        return {
            "datasets": list(datasets),
            "metadata": metadata_by_dataset,
            "relationships": [relationship.__dict__ for relationship in relationships],
        }

    def build_multibase_prompt(
        self,
        question: str,
        selected_datasets: Sequence[str],
        relationships: Sequence[Relationship],
    ) -> str:
        context = self.build_multibase_context(selected_datasets, relationships)
        prompt_parts = [
            "Você é um especialista em SQL ClickHouse.",
            "Responda SOMENTE com SQL válido, sem explicações, sem markdown.",
            "Use somente os datasets e relacionamentos fornecidos.",
            "Se houver relacionamento muitos-para-muitos, faça pré-agregação antes do JOIN.",
            "Não crie joins nem colunas fora do contexto fornecido.",
            "",
            f"Pergunta: {question}",
            "",
            "Datasets selecionados:",
        ]

        for dataset_id in selected_datasets:
            config = get_dataset_config(dataset_id)
            metadata = context["metadata"][dataset_id]
            columns = metadata.get("colunas_principais") or metadata.get("columns") or {}
            prompt_parts.append(
                f"- {dataset_id} -> tabela {get_table_name(dataset_id)} | {config.get('dominio', '')} | {config.get('description', '')}"
            )
            prompt_parts.append(f"  Colunas permitidas: {', '.join(columns.keys())}")

        prompt_parts.append("")
        prompt_parts.append("Relacionamentos permitidos:")
        if relationships:
            for relationship in relationships:
                prompt_parts.append(
                    f"- {relationship.id}: {relationship.source_table}.{relationship.source_column} = {relationship.target_table}.{relationship.target_column} | "
                    f"cardinalidade {relationship.cardinality} | pré-agregação {relationship.requires_preaggregation}"
                )
        else:
            prompt_parts.append("- Nenhum relacionamento autorizado encontrado.")

        prompt_parts.append("")
        prompt_parts.append("Regras:")
        prompt_parts.append("- Use only SELECT or WITH followed by SELECT")
        prompt_parts.append("- Preserve os alias e colunas de junção permitidas")
        prompt_parts.append("- Para muitos-para-muitos, agregue cada lado antes do JOIN")
        prompt_parts.append("- Dialeto: ClickHouse")
        prompt_parts.append("- Retorne apenas SQL")

        return "\n".join(prompt_parts)

    def generate_sql(
        self,
        question: str,
        model_name: str,
        selected_datasets: Sequence[str],
        relationships: Sequence[Relationship],
    ) -> Tuple[Optional[str], str]:
        if len(selected_datasets) <= 1:
            return None, "single_dataset"

        if not relationships:
            return None, "no_relationship"

        prompt = self.build_multibase_prompt(question, selected_datasets, relationships)
        llm = get_llm(model_name)

        try:
            response = llm.generate(prompt)
        except Exception as exc:
            logger.warning(f"Falha ao gerar SQL multibase via LLM: {exc}")
            return None, "llm_error"

        sql = extract_sql(response)
        if not sql:
            return None, "empty_response"

        return sql, "llm"

    def build_deterministic_fallback_sql(
        self,
        selected_datasets: Sequence[str],
        relationships: Sequence[Relationship],
        question: str = "",
    ) -> Optional[str]:
        if set(selected_datasets) == {"surtos-srag", "atencao-basica"} and relationships:
            relationship = relationships[0]
            if relationship.requires_preaggregation:
                question_lower = question.lower()
                asks_municipality_count = (
                    "quantos municípios" in question_lower
                    or "quantos municipios" in question_lower
                    or "em quantos municípios" in question_lower
                    or "em quantos municipios" in question_lower
                )
                if asks_municipality_count:
                    return f"""
WITH
srag_municipalities AS (
    SELECT DISTINCT {relationship.source_column} AS ibge
    FROM {relationship.source_table}
),
ubs_municipalities AS (
    SELECT DISTINCT {relationship.target_column} AS ibge
    FROM {relationship.target_table}
)
SELECT COUNT(*) AS total_municipios
FROM srag_municipalities AS s
INNER JOIN ubs_municipalities AS u
    ON s.ibge = u.ibge
""".strip()

                return f"""
WITH
srag_by_municipality AS (
    SELECT
        {relationship.source_column} AS ibge,
        COUNT(*) AS total_srag
    FROM {relationship.source_table}
    GROUP BY {relationship.source_column}
),
ubs_by_municipality AS (
    SELECT
        {relationship.target_column} AS ibge,
        COUNT(DISTINCT cnes) AS total_ubs
    FROM {relationship.target_table}
    GROUP BY {relationship.target_column}
)
SELECT
    s.ibge,
    s.total_srag,
    u.total_ubs
FROM srag_by_municipality AS s
INNER JOIN ubs_by_municipality AS u
    ON s.ibge = u.ibge
ORDER BY s.total_srag DESC
LIMIT 100
""".strip()

        return None

    def validate_sql(self, sql: str, selected_datasets: Sequence[str], relationships: Sequence[Relationship]) -> SqlValidationResult:
        if not sql:
            return SqlValidationResult(False, [], [], [], ["SQL vazio"])

        sql_clean = sql.strip()
        if ";" in sql_clean.rstrip(";"):
            return SqlValidationResult(False, [], [], [], ["Múltiplas instruções não são permitidas"])

        if re.search(r"--|/\*|\*/", sql_clean):
            return SqlValidationResult(False, [], [], [], ["Comentários não são permitidos"])

        try:
            parsed = parse_one(sql_clean, read="clickhouse")
        except Exception as exc:
            return SqlValidationResult(False, [], [], [], [f"Falha ao parsear SQL: {exc}"])

        if not isinstance(parsed, (exp.Select, exp.With)):
            return SqlValidationResult(False, [], [], [], ["A consulta deve começar com SELECT ou WITH seguido de SELECT"])

        cte_names = {cte.alias_or_name for cte in parsed.find_all(exp.CTE)} if hasattr(parsed, "find_all") else set()
        table_nodes = [node for node in parsed.find_all(exp.Table)]
        physical_tables = []
        alias_to_table = {}
        for table_node in table_nodes:
            table_name = table_node.name
            table_alias = table_node.alias_or_name
            if table_name not in cte_names:
                physical_tables.append(table_name)
                alias_to_table[table_alias.lower()] = table_name

        allowed_tables = {get_table_name(dataset) for dataset in selected_datasets}
        invalid_tables = [table for table in physical_tables if table not in allowed_tables]
        if invalid_tables:
            return SqlValidationResult(False, physical_tables, [], list(cte_names), [f"Tabelas não autorizadas: {', '.join(invalid_tables)}"])

        missing_tables = sorted(allowed_tables - set(physical_tables))
        if len(selected_datasets) > 1 and missing_tables:
            return SqlValidationResult(False, physical_tables, [], list(cte_names), [f"Tabelas selecionadas ausentes da consulta: {', '.join(missing_tables)}"])

        joins = []
        allowed_pairs = self._allowed_join_pairs(relationships)
        selected_columns = self._allowed_columns_by_dataset(selected_datasets)
        selected_columns_lower = {column.lower() for column in selected_columns}
        output_aliases = {alias.lower() for alias in self._extract_output_aliases(parsed)}

        for column_ref in self._extract_column_references(parsed):
            column_name = column_ref["column"]
            table_alias = column_ref.get("table")

            if table_alias and table_alias.lower() in cte_names:
                continue

            if table_alias and table_alias.lower() in alias_to_table:
                allowed_columns = {
                    allowed_column.lower()
                    for allowed_column in self._allowed_columns_for_table(alias_to_table[table_alias.lower()]).keys()
                }
                if column_name.lower() not in allowed_columns:
                    return SqlValidationResult(False, physical_tables, joins, list(cte_names), [f"Coluna não autorizada: {table_alias}.{column_name}"])
                continue

            if column_name.lower() in selected_columns_lower or column_name.lower() in output_aliases:
                continue

            return SqlValidationResult(False, physical_tables, joins, list(cte_names), [f"Coluna não autorizada: {column_name}"])

        if self._contains_write_operation(parsed):
            return SqlValidationResult(False, physical_tables, joins, list(cte_names), ["Comando de escrita não permitido"])

        join_nodes = list(parsed.find_all(exp.Join))
        if len(selected_datasets) > 1 and not join_nodes:
            return SqlValidationResult(False, physical_tables, joins, list(cte_names), ["Consulta multibase sem JOIN reconhecível"])

        preaggregated_pairs: Dict[str, set[str]] = {}
        for relationship in relationships:
            if relationship.requires_preaggregation and {
                relationship.source_dataset,
                relationship.target_dataset,
            }.issubset(set(selected_datasets)):
                pairs = self._preaggregated_join_pairs(parsed, relationship)
                if not pairs:
                    return SqlValidationResult(
                        False,
                        physical_tables,
                        joins,
                        list(cte_names),
                        [f"Relacionamento {relationship.id} exige pré-agregação dos dois lados antes do JOIN"],
                    )
                preaggregated_pairs[relationship.id] = pairs

        for join_node in join_nodes:
            on_expression = join_node.args.get("on")
            if on_expression is None:
                return SqlValidationResult(False, physical_tables, joins, list(cte_names), ["JOIN sem condição ON não é permitido"])
            if join_node.args.get("kind") and str(join_node.args.get("kind")).upper() == "CROSS":
                return SqlValidationResult(False, physical_tables, joins, list(cte_names), ["CROSS JOIN não autorizado"])

            join_text = on_expression.sql(dialect="clickhouse")
            joins.append(join_text)
            normalized = self._normalize_join_condition(join_text)

            if any(normalized in pairs for pairs in preaggregated_pairs.values()):
                continue

            if normalized not in allowed_pairs:
                return SqlValidationResult(False, physical_tables, joins, list(cte_names), [f"JOIN não autorizado: {join_text}"])

        return SqlValidationResult(True, physical_tables, joins, list(cte_names), [])

    def _allowed_join_pairs(self, relationships: Sequence[Relationship]) -> List[str]:
        allowed_pairs = []
        for relationship in relationships:
            allowed_pairs.append(f"{relationship.source_column}={relationship.target_column}")
            allowed_pairs.append(f"{relationship.target_column}={relationship.source_column}")
        return allowed_pairs

    def _allowed_columns_by_dataset(self, selected_datasets: Sequence[str]) -> List[str]:
        allowed_columns = []
        for dataset_id in selected_datasets:
            allowed_columns.extend(self._allowed_columns_for_table(get_table_name(dataset_id)).keys())
        return allowed_columns

    @staticmethod
    def _allowed_columns_for_table(table_name: str) -> Dict[str, dict]:
        table_to_dataset = {get_table_name(dataset_id): dataset_id for dataset_id in DATASETS_CONFIG.keys()}
        dataset_id = table_to_dataset.get(table_name)
        if not dataset_id:
            return {}
        metadata = json.loads(load_metadata(dataset_id))
        schema_columns = metadata.get("colunas_principais") or metadata.get("columns") or {}
        return schema_columns if isinstance(schema_columns, dict) else {}

    @staticmethod
    def _extract_column_references(parsed) -> List[Dict[str, Optional[str]]]:
        column_names = []
        for column_node in parsed.find_all(exp.Column):
            column_name = column_node.name
            if column_name:
                table_name = column_node.table or None
                column_names.append({"table": table_name, "column": column_name})
        return column_names

    @staticmethod
    def _extract_output_aliases(parsed) -> List[str]:
        aliases = []
        for alias_node in parsed.find_all(exp.Alias):
            alias_name = alias_node.alias
            if alias_name:
                aliases.append(alias_name)
        return aliases

    @staticmethod
    def _contains_write_operation(parsed) -> bool:
        forbidden_names = ["Insert", "Update", "Delete", "Drop", "Create", "Alter", "Truncate"]
        forbidden_classes = []
        for class_name in forbidden_names:
            expression_class = getattr(exp, class_name, None)
            if expression_class is not None:
                forbidden_classes.append(expression_class)

        if not forbidden_classes:
            return False

        return any(isinstance(node, tuple(forbidden_classes)) for node in parsed.walk())

    @staticmethod
    def _normalize_join_condition(join_text: str) -> str:
        normalized = re.sub(r"\b[a-zA-Z_][\w]*\.", "", join_text.lower())
        normalized = re.sub(r"\s+", "", normalized)
        normalized = normalized.replace("`", "")
        return normalized

    @staticmethod
    def _preaggregated_join_pairs(parsed, relationship: Relationship) -> set[str]:
        """Retorna pares de chaves de saída de CTEs que agregam cada lado da relação."""

        def cte_key_alias(cte, physical_table: str, relationship_column: str) -> Optional[str]:
            query = cte.this
            table_names = {table.name.lower() for table in query.find_all(exp.Table)}
            if physical_table.lower() not in table_names:
                return None

            group = query.args.get("group")
            is_distinct = bool(query.args.get("distinct"))
            if group is not None:
                grouped_columns = {column.name.lower() for column in group.find_all(exp.Column)}
            elif is_distinct:
                grouped_columns = {
                    column.name.lower()
                    for expression in query.expressions
                    for column in expression.find_all(exp.Column)
                }
            else:
                return None

            if relationship_column.lower() not in grouped_columns:
                return None

            if not is_distinct and not any(isinstance(node, exp.AggFunc) for node in query.walk()):
                return None

            for expression in query.expressions:
                if isinstance(expression, exp.Alias):
                    source_columns = list(expression.this.find_all(exp.Column))
                    if any(column.name.lower() == relationship_column.lower() for column in source_columns):
                        return expression.alias.lower()
                if isinstance(expression, exp.Column) and expression.name.lower() == relationship_column.lower():
                    return expression.name.lower()

            return None

        source_aliases = []
        target_aliases = []
        for cte in parsed.find_all(exp.CTE):
            source_alias = cte_key_alias(cte, relationship.source_table, relationship.source_column)
            if source_alias:
                source_aliases.append(source_alias)

            target_alias = cte_key_alias(cte, relationship.target_table, relationship.target_column)
            if target_alias:
                target_aliases.append(target_alias)

        pairs = set()
        for source_alias in source_aliases:
            for target_alias in target_aliases:
                pairs.add(f"{source_alias}={target_alias}")
                pairs.add(f"{target_alias}={source_alias}")
        return pairs

    @staticmethod
    def _is_preaggregated_srag_ubs_query(sql: str, selected_datasets: Sequence[str], normalized_join: str) -> bool:
        selected_set = set(selected_datasets)
        if selected_set != {"surtos-srag", "atencao-basica"}:
            return False

        sql_lower = sql.lower()
        if "count(*) as total_srag" not in sql_lower:
            return False

        if "count(distinct cnes) as total_ubs" not in sql_lower and "count(distinct a.cnes) as total_ubs" not in sql_lower:
            return False

        return normalized_join == "ibge=ibge"

    @staticmethod
    def _extract_tables_with_regex(sql: str, cte_names: Optional[Sequence[str]] = None) -> List[str]:
        tables = []
        cte_name_set = {name.lower() for name in cte_names or []}
        for match in re.finditer(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][\w]*)", sql, re.IGNORECASE):
            table_name = match.group(1).lower()
            if table_name not in cte_name_set:
                tables.append(table_name)
        return tables

    @staticmethod
    def _extract_joins_with_regex(sql: str) -> List[str]:
        joins = []
        for match in re.finditer(r"\bON\s+(.+?)(?:\bJOIN\b|\bWHERE\b|\bGROUP BY\b|\bORDER BY\b|\bLIMIT\b|$)", sql, re.IGNORECASE | re.DOTALL):
            join_text = re.sub(r"\s+", " ", match.group(1).strip())
            joins.append(join_text)
        return joins

    @staticmethod
    def _extract_cte_names_with_regex(sql: str) -> List[str]:
        return [match.group(1).lower() for match in re.finditer(r"\b([a-zA-Z_][\w]*)\s+AS\s*\(", sql, re.IGNORECASE)]


multibase_service = MultibaseService()
