from fastapi import APIRouter
from pydantic import BaseModel
import logging
import re
import time
from typing import Optional, List, Dict, Tuple

from services.sql_service import generate_sql
from db.clickhouse import run_query
from services.interpretation_service import interpret_result
from services.multibase_service import multibase_service
from services.relationship_service import relationship_service
from services.result_formatter import (
    build_factual_summary,
    is_low_information_interpretation,
    should_use_deterministic_interpretation,
)
from metadata.loader import load_metadata, get_available_datasets, get_metadata_by_dataset
from config.datasets import DATASETS_CONFIG

logger = logging.getLogger(__name__)

router = APIRouter()

class AskRequest(BaseModel):
    question: str
    model: str = "deepseek-local"
    dataset: Optional[str] = None  # ← NOVO: Suporte a múltiplos datasets


def _error_response(
    question: str,
    datasets: List[str],
    message: str,
    insight: str,
    routing_mode: str = "unknown",
    sql_generation_mode: str = "none",
    relationships: Optional[List[str]] = None,
    validation: Optional[Dict[str, object]] = None,
    sql: Optional[str] = None,
) -> Dict[str, object]:
    """Mantém o mesmo contrato básico de resposta em todos os erros."""

    selected = datasets or ["unknown"]
    return {
        "question": question,
        "dataset": ",".join(selected),
        "datasets": selected,
        "cross_dataset": len(selected) > 1,
        "relationships": relationships or [],
        "routing_mode": routing_mode,
        "sql_generation_mode": sql_generation_mode,
        "llm_sql_attempted": sql_generation_mode in {"llm", "deterministic_fallback"},
        "validation": validation or {"valid": False, "tables": [], "joins": [], "errors": []},
        "sql": sql,
        "data": {"error": message},
        "insight": insight,
        "factual_summary": "",
        "interpretation_mode": "none",
        "success": False,
    }


def _detect_candidate_datasets(question: str) -> List[str]:
    """Retorna datasets ordenados por compatibilidade heurística com a pergunta."""

    return multibase_service._detect_keyword_datasets(
        question,
        list(DATASETS_CONFIG.keys()),
    )


def _build_interoperability_fallback_sql(question: str, detected_datasets: List[str]) -> Optional[Tuple[str, List[str]]]:
    """Monta um SQL determinístico de fallback para interoperabilidade conhecida."""

    q = question.lower()
    datasets_set = set(detected_datasets)

    if {"surtos-srag", "atencao-basica"}.issubset(datasets_set):
        if any(word in q for word in ["município", "municipio", "cidade", "ibge"]):
            sql = """
            WITH
            srag_by_municipality AS (
                SELECT
                    co_mun_not AS ibge,
                    COUNT(*) AS total_srag
                FROM srag
                GROUP BY co_mun_not
            ),
            ubs_by_municipality AS (
                SELECT
                    ibge,
                    COUNT(DISTINCT cnes) AS total_ubs
                FROM atencao_basica
                GROUP BY ibge
            )
            SELECT
                s.ibge,
                s.total_srag,
                u.total_ubs
            FROM srag_by_municipality AS s
            INNER JOIN ubs_by_municipality AS u ON s.ibge = u.ibge
            ORDER BY total_srag DESC
            LIMIT 100
            """.strip()
            return sql, ["surtos-srag", "atencao-basica"]

        if any(word in q for word in ["estado", "uf", "região", "regiao"]):
            sql = """
            WITH
            srag_by_uf AS (
                SELECT
                    sg_uf_not AS uf,
                    COUNT(*) AS total_srag
                FROM srag
                GROUP BY sg_uf_not
            ),
            ubs_by_uf AS (
                SELECT
                    uf,
                    COUNT(DISTINCT cnes) AS total_ubs,
                    COUNT(DISTINCT ibge) AS municipios_com_ubs
                FROM atencao_basica
                GROUP BY uf
            )
            SELECT
                s.uf,
                s.total_srag,
                u.municipios_com_ubs,
                u.total_ubs
            FROM srag_by_uf AS s
            INNER JOIN ubs_by_uf AS u ON s.uf = u.uf
            ORDER BY total_srag DESC
            LIMIT 100
            """.strip()
            return sql, ["surtos-srag", "atencao-basica"]

        sql = """
        WITH
        srag_by_municipality AS (
            SELECT
                co_mun_not AS ibge,
                COUNT(*) AS total_srag
            FROM srag
            GROUP BY co_mun_not
        ),
        ubs_by_municipality AS (
            SELECT
                ibge,
                COUNT(DISTINCT cnes) AS total_ubs
            FROM atencao_basica
            GROUP BY ibge
        )
        SELECT
            s.ibge,
            s.total_srag,
            u.total_ubs
        FROM srag_by_municipality AS s
        INNER JOIN ubs_by_municipality AS u ON s.ibge = u.ibge
        """.strip()
        return sql, ["surtos-srag", "atencao-basica"]

    return None


def sanitize_sql(sql: str) -> str:
    """Sanitização inteligente que preserva SQL válido"""
    
    logger.debug(f"SQL antes de sanitizar: {sql}")
    
    sql = sql.strip()
    
    # Remover comentários SQL
    sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    
    # Remover ponto e vírgula final (ClickHouse não precisa)
    sql = sql.rstrip(";")
    
    # CUIDADO: Não remover filtros de data válidos
    # Apenas corrigir funções incompatíveis
    
    # Corrigir DATE() para toDate()
    sql = re.sub(r"\bDATE\s*\(", "toDate(", sql, flags=re.IGNORECASE)
    
    # Corrigir datetime() para now()
    sql = re.sub(r"\bdatetime\s*\(\s*\)", "now()", sql, flags=re.IGNORECASE)
    
    # Corrigir CURRENT_DATE para today()
    sql = re.sub(r"\bCURRENT_DATE\b", "today()", sql, flags=re.IGNORECASE)
    
    # Garantir que LIMIT existe se não houver GROUP BY (segurança)
    has_scalar_aggregate = bool(
        re.search(r"\b(?:COUNT|SUM|AVG|MIN|MAX|MEDIAN|STDDEV)\s*\(", sql, re.IGNORECASE)
    ) and "GROUP BY" not in sql.upper()
    if "GROUP BY" not in sql.upper() and "LIMIT" not in sql.upper() and not has_scalar_aggregate:
        if not re.search(r"LIMIT\s+\d+", sql, re.IGNORECASE):
            sql = sql.rstrip() + " LIMIT 10000"
    
    logger.debug(f"SQL depois de sanitizar: {sql}")
    return sql


def is_valid_sql(sql: str, dataset: str = "covid-19-vacinacao") -> bool:
    """
    Valida SQL de forma mais rigorosa.
    
    Verifica:
    - SQL começa com SELECT (segurança)
    - Contém cláusula FROM
    - Referencia tabela correta do dataset
    
    Args:
        sql: SQL a validar
        dataset: Dataset esperado (para validar referência à tabela correta)
    
    Dataset→Tabela Mapping:
        - covid-19-vacinacao → vacinacao
        - leitos → leitos
    """
    
    if not sql:
        logger.warning("SQL vazio")
        return False
    
    sql_upper = sql.upper().strip()
    
    # Deve começar com SELECT
    if not sql_upper.startswith("SELECT"):
        logger.warning(f"SQL não começa com SELECT: {sql_upper[:50]}")
        return False
    
    # Deve conter FROM
    if "FROM" not in sql_upper:
        logger.warning("SQL não contém FROM")
        return False
    
    # Mapear dataset → tabela esperada
    dataset_table_map = {
        "covid-19-vacinacao": "vacinacao",
        "leitos": "leitos",
        "surtos-srag": "srag",
        "atencao-basica": "atencao_basica"
    }
    
    expected_table = dataset_table_map.get(dataset, "vacinacao")
    
    # Deve referenciar a tabela do dataset
    if expected_table not in sql.lower():
        logger.warning(f"SQL não referencia tabela '{expected_table}' do dataset '{dataset}'")
        return False
    
    # Verificar comandos perigosos
    forbidden = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "TRUNCATE", "CREATE"]
    for cmd in forbidden:
        if f" {cmd} " in f" {sql_upper} ":
            logger.warning(f"SQL contém comando proibido: {cmd}")
            return False
    
    # Sem markdown
    if "```" in sql:
        logger.warning("SQL contém marcadores markdown")
        return False
    
    return True


@router.post("/ask")
def ask(req: AskRequest):
    """
    Processa pergunta em linguagem natural e retorna resultado.
    
    **Body Parameters:**
    - `question`: Pergunta em português
    - `model`: Modelo LLM a usar (padrão: "deepseek-local")
    - `dataset`: Dataset a consultar (padrão: detecta automaticamente)
    
    **Fluxo:**
    1. Se dataset fornecido: usa diretamente
    2. Se não, tenta detectar do conteúdo da pergunta
    3. Se falhar detecção, usa "covid-19-vacinacao" (padrão histórico)
    
    **Exemplos com frontend:**
    ```json
    // Pergunta pré-pronta selecionada no frontend
    {
      "question": "Quantas vacinas foram aplicadas em SP?",
      "model": "deepseek-local",
      "dataset": "covid-19-vacinacao"
    }
    
    // Pergunta customizada sobre leitos (detecção automática)
    {
      "question": "Quais cidades têm UTI neonatal?",
      "model": "deepseek-local"
      // dataset será detectado automaticamente
    }
    ```
    """
    
    # ========== TIMING SETUP ==========
    time_start = time.time()
    timings = {
        "total_start": time_start,
        "stages": {}
    }
    
    logger.info(f"Pergunta recebida: {req.question}")
    logger.info(f"Modelo: {req.model}")
    if req.dataset:
        logger.info(f"Dataset especificado: {req.dataset}")
    
    try:
        detected_datasets = _detect_candidate_datasets(req.question)
        dataset_to_use = req.dataset or "covid-19-vacinacao"
        selected_datasets = [dataset_to_use]
        cross_dataset = False
        routing_mode = "single_dataset"
        sql_generation_mode = "llm"
        relationships_used: List[str] = []
        validation_payload: Dict[str, object] = {"valid": False, "tables": [], "joins": []}

        if not req.dataset:
            stage_start = time.time()
            selection = multibase_service.select_datasets(
                req.question,
                req.model,
                list(DATASETS_CONFIG.keys()),
            )
            timings["stages"]["dataset_selection"] = time.time() - stage_start

            selected_datasets = selection.datasets or (detected_datasets[:1] if detected_datasets else [dataset_to_use])
            cross_dataset = len(selected_datasets) > 1
            routing_mode = selection.routing_mode

            if cross_dataset:
                stage_start = time.time()
                relationships = relationship_service.find_relationships(selected_datasets)
                timings["stages"]["relationship_lookup"] = time.time() - stage_start

                if not relationships:
                    return {
                        "question": req.question,
                        "dataset": ",".join(selected_datasets),
                        "datasets": selected_datasets,
                        "cross_dataset": True,
                        "relationships": [],
                        "routing_mode": routing_mode,
                        "sql_generation_mode": "none",
                        "validation": {"valid": False, "tables": [], "joins": [], "errors": ["Nenhum relacionamento cadastrado para as bases selecionadas"]},
                        "data": {"error": "Não há relacionamento cadastrado para as bases selecionadas."},
                        "insight": "Não há um relacionamento validado para montar essa consulta entre bases.",
                        "success": False,
                    }

                relationships_used = [relationship.id for relationship in relationships]
                question_lower = req.question.lower()
                analytical_limitations = [
                    DATASETS_CONFIG[dataset].get("data_scope_note")
                    for dataset in selected_datasets
                    if DATASETS_CONFIG[dataset].get("data_scope_note")
                ]
                analytical_limitations.extend([
                    relationship.analytical_notes
                    for relationship in relationships
                    if relationship.analytical_notes
                    and relationship.limitation_keywords
                    and any(keyword.lower() in question_lower for keyword in relationship.limitation_keywords)
                ])
                analytical_limitations.extend(
                    note
                    for relationship in relationships
                    for note in relationship.result_notes
                )

                stage_start = time.time()
                multibase_context = multibase_service.build_multibase_context(selected_datasets, relationships)
                timings["stages"]["context_construction"] = time.time() - stage_start

                stage_start = time.time()
                raw_sql, sql_generation_mode = multibase_service.generate_sql(
                    req.question,
                    req.model,
                    selected_datasets,
                    relationships,
                )
                timings["stages"]["sql_generation"] = time.time() - stage_start

                if not raw_sql:
                    raw_sql = multibase_service.build_deterministic_fallback_sql(
                        selected_datasets,
                        relationships,
                        req.question,
                    )
                    if raw_sql:
                        sql_generation_mode = "deterministic_fallback"
                    else:
                        return {
                            "question": req.question,
                            "dataset": ",".join(selected_datasets),
                            "datasets": selected_datasets,
                            "cross_dataset": True,
                            "relationships": relationships_used,
                            "routing_mode": routing_mode,
                            "sql_generation_mode": sql_generation_mode,
                            "validation": {"valid": False, "tables": [], "joins": [], "errors": ["Não foi possível gerar SQL multibase"]},
                            "data": {"error": "Não foi possível gerar SQL multibase."},
                            "insight": "Não foi possível gerar uma consulta multibase válida.",
                            "success": False,
                        }

                stage_start = time.time()
                sql = sanitize_sql(raw_sql)
                try:
                    sql = multibase_service.canonicalize_sql_identifiers(sql, selected_datasets)
                except Exception as exc:
                    logger.warning("Não foi possível canonicalizar a SQL multibase: %s", exc)
                validation_result = multibase_service.validate_sql(sql, selected_datasets, relationships)
                timings["stages"]["validation"] = time.time() - stage_start

                if not validation_result.valid:
                    fallback_sql = multibase_service.build_deterministic_fallback_sql(
                        selected_datasets,
                        relationships,
                        req.question,
                    )
                    if fallback_sql:
                        sql = sanitize_sql(fallback_sql)
                        sql = multibase_service.canonicalize_sql_identifiers(sql, selected_datasets)
                        validation_result = multibase_service.validate_sql(sql, selected_datasets, relationships)
                        sql_generation_mode = "deterministic_fallback"
                    if not validation_result.valid:
                        return {
                            "question": req.question,
                            "dataset": ",".join(selected_datasets),
                            "datasets": selected_datasets,
                            "cross_dataset": True,
                            "relationships": relationships_used,
                            "routing_mode": routing_mode,
                            "sql_generation_mode": sql_generation_mode,
                            "validation": {
                                "valid": False,
                                "tables": validation_result.tables,
                                "joins": validation_result.joins,
                                "errors": validation_result.errors,
                            },
                            "data": {"error": "SQL multibase inválido"},
                            "insight": "A consulta multibase não passou na validação estrutural.",
                            "success": False,
                        }

                validation_payload = {
                    "valid": validation_result.valid,
                    "tables": validation_result.tables,
                    "joins": validation_result.joins,
                    "errors": validation_result.errors,
                }

                stage_start = time.time()
                logger.info("Executando consulta multibase no ClickHouse...")
                result = run_query(sql)
                timings["stages"]["database_execution"] = time.time() - stage_start

                if isinstance(result, dict) and "error" in result:
                    return {
                        "question": req.question,
                        "dataset": ",".join(selected_datasets),
                        "datasets": selected_datasets,
                        "cross_dataset": True,
                        "relationships": relationships_used,
                        "routing_mode": routing_mode,
                        "sql_generation_mode": sql_generation_mode,
                        "validation": validation_payload,
                        "sql": sql,
                        "data": result,
                        "insight": f"Erro ao executar a consulta multibase: {result.get('message', result['error'])}",
                        "success": False,
                    }

                stage_start = time.time()
                factual_summary = build_factual_summary(sql, result, req.question)
                if (
                    sql_generation_mode == "deterministic_fallback"
                    or should_use_deterministic_interpretation(req.question, factual_summary)
                ):
                    insight = factual_summary
                    interpretation_mode = "deterministic_factual"
                else:
                    insight = interpret_result(
                        req.question,
                        result,
                        req.model,
                        dataset=",".join(selected_datasets),
                        factual_summary=factual_summary,
                    )
                    interpretation_mode = "llm_grounded"
                    if is_low_information_interpretation(insight, factual_summary):
                        insight = factual_summary
                        interpretation_mode = "deterministic_fallback"
                if analytical_limitations:
                    insight = f"Limitação analítica: {' '.join(analytical_limitations)} {insight}"
                timings["stages"]["interpretation"] = time.time() - stage_start

                time_total = time.time() - time_start
                timings["total_ms"] = round(time_total * 1000, 2)

                return {
                    "question": req.question,
                    "dataset": ",".join(selected_datasets),
                    "datasets": selected_datasets,
                    "cross_dataset": True,
                    "relationships": relationships_used,
                    "analytical_limitations": analytical_limitations,
                    "routing_mode": routing_mode,
                    "sql_generation_mode": sql_generation_mode,
                    "llm_sql_attempted": sql_generation_mode in {"llm", "deterministic_fallback"},
                    "validation": validation_payload,
                    "sql": sql,
                    "data": result,
                    "insight": insight,
                    "factual_summary": factual_summary,
                    "interpretation_mode": interpretation_mode,
                    "success": True,
                    "timing_s": {
                        "dataset_selection": round(timings["stages"].get("dataset_selection", 0), 2),
                        "relationship_lookup": round(timings["stages"].get("relationship_lookup", 0), 2),
                        "context_construction": round(timings["stages"].get("context_construction", 0), 2),
                        "sql_generation": round(timings["stages"].get("sql_generation", 0), 2),
                        "sql_generation_llm": round(
                            timings["stages"].get("sql_generation", 0)
                            if sql_generation_mode in {"llm", "deterministic_fallback"}
                            else 0,
                            2,
                        ),
                        "validation": round(timings["stages"].get("validation", 0), 2),
                        "database_execution": round(timings["stages"].get("database_execution", 0), 2),
                        "interpretation_llm": round(timings["stages"].get("interpretation", 0), 2),
                        "total": round(timings["total_ms"] / 1000, 2),
                    },
                }

            if selected_datasets:
                dataset_to_use = selected_datasets[0]
                logger.info(f"Dataset detectado automaticamente: {dataset_to_use}")
        
        # Carregar metadata do dataset
        try:
            metadata = load_metadata(dataset_to_use)
            logger.info(f"Metadata carregado para dataset: {dataset_to_use}")
        except FileNotFoundError:
            logger.error(f"Dataset error - Dataset não encontrado: {dataset_to_use}")
            return _error_response(
                req.question,
                [dataset_to_use],
                f"Dataset '{dataset_to_use}' não encontrado",
                f"Desculpe, o dataset '{dataset_to_use}' não está disponível.",
                routing_mode=routing_mode,
            )
        
        # ========== 1. GERAR SQL COM LLM ==========
        stage_start = time.time()
        logger.info("Gerando SQL...")
        raw_sql, sql_generation_mode = generate_sql(
            req.question,
            metadata,
            req.model,
            dataset_to_use,
            return_mode=True,
        )
        time_sql_generation = time.time() - stage_start
        timings["stages"]["sql_generation"] = time_sql_generation
        
        if not raw_sql:
            logger.error("Falha ao gerar SQL")
            return _error_response(
                req.question,
                [dataset_to_use],
                "Não foi possível gerar uma consulta válida",
                "Desculpe, não consegui entender sua pergunta.",
                routing_mode=routing_mode,
                sql_generation_mode=sql_generation_mode,
            )
        
        logger.debug(f"SQL gerado (raw): {raw_sql}")
        
        # ========== 2. SANITIZAR ==========
        stage_start = time.time()
        logger.info("Sanitizando SQL...")
        sql = sanitize_sql(raw_sql)
        try:
            sql = multibase_service.canonicalize_sql_identifiers(sql, [dataset_to_use])
        except Exception as exc:
            logger.warning("Não foi possível canonicalizar os identificadores SQL: %s", exc)
        time_sanitization = time.time() - stage_start
        timings["stages"]["sanitization"] = time_sanitization
        logger.debug(f"SQL sanitizado: {sql}")
        
        # ========== 3. VALIDAR ==========
        stage_start = time.time()
        logger.info("Validando SQL...")
        single_validation = multibase_service.validate_sql(sql, [dataset_to_use], [])
        validation_payload = {
            "valid": single_validation.valid,
            "tables": single_validation.tables,
            "joins": single_validation.joins,
            "errors": single_validation.errors,
        }
        if not single_validation.valid:
            logger.error(f"SQL inválido: {sql}")
            return _error_response(
                req.question,
                [dataset_to_use],
                "SQL inválido foi rejeitado",
                "Desculpe, a consulta gerada não é válida para este banco de dados.",
                routing_mode=routing_mode,
                sql_generation_mode=sql_generation_mode,
                validation=validation_payload,
                sql=raw_sql,
            )
        time_validation = time.time() - stage_start
        timings["stages"]["validation"] = time_validation
        
        # ========== 4. EXECUTAR NO CLICKHOUSE ==========
        stage_start = time.time()
        logger.info("Executando query no ClickHouse...")
        result = run_query(sql)
        time_database = time.time() - stage_start
        timings["stages"]["database_execution"] = time_database
        
        # Verificar se houve erro
        if isinstance(result, dict) and "error" in result:
            logger.error(f"Erro na execução: {result['error']}")
            return _error_response(
                req.question,
                [dataset_to_use],
                result.get("message", result["error"]),
                f"Erro ao executar a consulta: {result.get('message', result['error'])}",
                routing_mode=routing_mode,
                sql_generation_mode=sql_generation_mode,
                validation=validation_payload,
                sql=sql,
            )
        
        logger.info(f"Query executada com sucesso. Resultado: {len(result)} linhas")
        
        # ========== 5. INTERPRETAR RESULTADO COM LLM ==========
        stage_start = time.time()
        logger.info("Interpretando resultado...")
        factual_summary = build_factual_summary(sql, result, req.question)
        if should_use_deterministic_interpretation(req.question, factual_summary):
            insight = factual_summary
            interpretation_mode = "deterministic_factual"
        else:
            insight = interpret_result(
                req.question,
                result,
                req.model,
                dataset=dataset_to_use,
                factual_summary=factual_summary,
            )
            interpretation_mode = "llm_grounded"
            if is_low_information_interpretation(insight, factual_summary):
                insight = factual_summary
                interpretation_mode = "deterministic_fallback"
        time_interpretation = time.time() - stage_start
        timings["stages"]["interpretation"] = time_interpretation
        
        # ========== CALCULAR TEMPOS TOTAIS ==========
        time_total = time.time() - time_start
        timings["total_ms"] = round(time_total * 1000, 2)
        
        # ========== PRINT TIMING REPORT NO TERMINAL ==========
        print("\n" + "="*70)
        print(f"⏱️  TIMING REPORT - {req.model.upper()}")
        print("="*70)
        print(f"Pergunta: {req.question[:60]}...")
        print(f"Dataset: {dataset_to_use}")
        print("-"*70)
        print(f"  SQL Generation ({sql_generation_mode}): {timings['stages']['sql_generation']:>8.2f} s")
        print(f"  SQL Sanitization:            {timings['stages']['sanitization']:>8.2f} s")
        print(f"  SQL Validation:              {timings['stages']['validation']:>8.2f} s")
        print(f"  Database Execution:          {timings['stages']['database_execution']:>8.2f} s")
        print(f"  Result Interpretation ({interpretation_mode}): {timings['stages']['interpretation']:>8.2f} s")
        print("-"*70)
        print(f"  TOTAL:                       {timings['total_ms']/1000:>8.2f} s")
        print("="*70 + "\n")
        
        # ========== LOG DETALHADO ==========
        logger.info(f"Timing - SQL Gen: {timings['stages']['sql_generation']:.2f}s, "
                   f"Sanitization: {timings['stages']['sanitization']:.2f}s, "
                   f"Validation: {timings['stages']['validation']:.2f}s, "
                   f"DB: {timings['stages']['database_execution']:.2f}s, "
                   f"Interpretation: {timings['stages']['interpretation']:.2f}s, "
                   f"TOTAL: {timings['total_ms']/1000:.2f}s")
        
        return {
            "question": req.question,
            "dataset": dataset_to_use,
            "datasets": [dataset_to_use],
            "cross_dataset": False,
            "relationships": [],
            "analytical_limitations": [
                DATASETS_CONFIG[dataset_to_use]["data_scope_note"]
            ] if DATASETS_CONFIG.get(dataset_to_use, {}).get("data_scope_note") else [],
            "routing_mode": routing_mode,
            "sql_generation_mode": sql_generation_mode,
            "llm_sql_attempted": sql_generation_mode in {"llm", "deterministic_fallback"},
            "validation": validation_payload,
            "sql": sql,
            "data": result,
            "insight": insight,
            "factual_summary": factual_summary,
            "interpretation_mode": interpretation_mode,
            "success": True,
            "timing_s": {
                "dataset_selection": round(timings['stages'].get('dataset_selection', 0), 2),
                "relationship_lookup": round(timings['stages'].get('relationship_lookup', 0), 2),
                "context_construction": round(timings['stages'].get('context_construction', 0), 2),
                "sql_generation": round(timings['stages']['sql_generation'], 2),
                "sql_generation_llm": round(
                    timings['stages']['sql_generation'] if sql_generation_mode in {"llm", "deterministic_fallback"} else 0,
                    2,
                ),
                "sanitization": round(timings['stages']['sanitization'], 2),
                "validation": round(timings['stages']['validation'], 2),
                "database_execution": round(timings['stages']['database_execution'], 2),
                "interpretation_llm": round(timings['stages']['interpretation'], 2),
                "total": round(timings['total_ms']/1000, 2)
            }
        }
    
    except Exception as e:
        logger.exception(f"Erro inesperado: {e}")
        return _error_response(
            req.question,
            selected_datasets if "selected_datasets" in locals() else [req.dataset or "unknown"],
            str(e),
            "Desculpe, ocorreu um erro inesperado ao processar sua pergunta.",
            routing_mode=routing_mode if "routing_mode" in locals() else "unknown",
            sql_generation_mode=sql_generation_mode if "sql_generation_mode" in locals() else "none",
            relationships=relationships_used if "relationships_used" in locals() else [],
            validation=validation_payload if "validation_payload" in locals() else None,
        )


def _detect_dataset_for_question(question: str) -> Optional[str]:
    """
    Detecta qual dataset seria mais apropriado para uma pergunta.
    
    Usa heurísticas simples de palavras-chave.
    Retorna None se nenhum dataset for detectado com confiança.
    
    Datasets suportados:
    - covid-19-vacinacao: Campanha Nacional de Vacinação COVID-19
    - leitos: Dados de leitos hospitalares
    - surtos-srag: Síndrome Respiratória Aguda Grave
    - atencao-basica: Unidades Básicas de Saúde (UBS)
    """
    detected = _detect_candidate_datasets(question)
    return detected[0] if detected else None
