from fastapi import APIRouter
from pydantic import BaseModel
import logging
import re
from typing import Optional

from services.sql_service import generate_sql
from db.clickhouse import run_query
from services.interpretation_service import interpret_result
from metadata.loader import load_metadata

logger = logging.getLogger(__name__)

router = APIRouter()

class AskRequest(BaseModel):
    question: str
    model: str = "deepseek-local"
    dataset: Optional[str] = None  # ← NOVO: Suporte a múltiplos datasets


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
    if "GROUP BY" not in sql.upper() and "LIMIT" not in sql.upper():
        if not re.search(r"LIMIT\s+\d+", sql, re.IGNORECASE):
            sql = sql.rstrip() + " LIMIT 10000"
    
    logger.debug(f"SQL depois de sanitizar: {sql}")
    return sql


def is_valid_sql(sql: str, dataset: str = "vacinacao-covid") -> bool:
    """
    Valida SQL de forma mais rigorosa.
    
    Args:
        sql: SQL a validar
        dataset: Dataset esperado (para validar referência à tabela)
    
    Mapeamento de dataset → tabela:
        - vacinacao-covid → vacinacao
        - dengue-2024 → dengue
        - influenza-2025 → influenza
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
        "vacinacao-covid": "vacinacao",
        "dengue-2024": "dengue",
        "influenza-2025": "influenza"
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
    3. Se falhar detecção, usa "vacinacao-covid" (padrão histórico)
    
    **Exemplos com frontend:**
    ```json
    // Pergunta pré-pronta selecionada no frontend
    {
      "question": "Quantas vacinas foram aplicadas em SP?",
      "model": "deepseek-local",
      "dataset": "vacinacao-covid"
    }
    
    // Pergunta customizada (detecção automática)
    {
      "question": "Qual estado teve mais casos de dengue?",
      "model": "deepseek-local"
      // dataset será detectado automaticamente
    }
    ```
    """
    
    logger.info(f"Pergunta recebida: {req.question}")
    logger.info(f"Modelo: {req.model}")
    if req.dataset:
        logger.info(f"Dataset especificado: {req.dataset}")
    
    try:
        # Determinar dataset a usar
        dataset_to_use = req.dataset or "vacinacao-covid"
        
        # Se dataset não foi fornecido, tentar detectar
        if not req.dataset:
            detected = _detect_dataset_for_question(req.question)
            if detected:
                dataset_to_use = detected
                logger.info(f"Dataset detectado automaticamente: {dataset_to_use}")
        
        # Carregar metadata do dataset
        try:
            metadata = load_metadata(dataset_to_use)
            logger.info(f"Metadata carregado para dataset: {dataset_to_use}")
        except FileNotFoundError:
            logger.error(f"Dataset error - Dataset não encontrado: {dataset_to_use}")
            return {
                "question": req.question,
                "dataset": dataset_to_use,
                "sql": None,
                "data": {"error": f"Dataset '{dataset_to_use}' não encontrado"},
                "insight": f"Desculpe, o dataset '{dataset_to_use}' não está disponível.",
                "success": False
            }
        
        # 1. Gerar SQL com LLM
        logger.info("Gerando SQL...")
        raw_sql = generate_sql(req.question, metadata, req.model, dataset_to_use)
        
        if not raw_sql:
            logger.error("Falha ao gerar SQL")
            return {
                "question": req.question,
                "dataset": dataset_to_use,
                "sql": None,
                "data": {"error": "Não foi possível gerar uma consulta válida"},
                "insight": "Desculpe, não consegui entender sua pergunta.",
                "success": False
            }
        
        logger.debug(f"SQL gerado (raw): {raw_sql}")
        
        # 2. Sanitizar
        logger.info("Sanitizando SQL...")
        sql = sanitize_sql(raw_sql)
        logger.debug(f"SQL sanitizado: {sql}")
        
        # 3. Validar
        logger.info("Validando SQL...")
        if not is_valid_sql(sql, dataset_to_use):
            logger.error(f"SQL inválido: {sql}")
            return {
                "question": req.question,
                "dataset": dataset_to_use,
                "sql": raw_sql,
                "data": {"error": "SQL inválido foi rejeitada"},
                "insight": "Desculpe, a consulta gerada não é válida para este banco de dados.",
                "success": False
            }
        
        # 4. Executar
        logger.info("Executando query no ClickHouse...")
        result = run_query(sql)
        
        # Verificar se houve erro
        if isinstance(result, dict) and "error" in result:
            logger.error(f"Erro na execução: {result['error']}")
            return {
                "question": req.question,
                "dataset": dataset_to_use,
                "sql": sql,
                "data": result,
                "insight": f"Erro ao executar a consulta: {result.get('message', result['error'])}",
                "success": False
            }
        
        logger.info(f"Query executada com sucesso. Resultado: {len(result)} linhas")
        
        # 5. Interpretar
        logger.info("Interpretando resultado...")
        insight = interpret_result(req.question, result, req.model)
        
        return {
            "question": req.question,
            "dataset": dataset_to_use,
            "sql": sql,
            "data": result,
            "insight": insight,
            "success": True
        }
    
    except Exception as e:
        logger.exception(f"Erro inesperado: {e}")
        return {
            "question": req.question,
            "dataset": req.dataset or "unknown",
            "sql": None,
            "data": {"error": str(e)},
            "insight": "Desculpe, ocorreu um erro inesperado ao processar sua pergunta.",
            "success": False
        }


def _detect_dataset_for_question(question: str) -> Optional[str]:
    """
    Detecta qual dataset seria mais apropriado para uma pergunta.
    
    Usa heurísticas simples de palavras-chave.
    Retorna None se nenhum dataset for detectado com confiança.
    """
    question_lower = question.lower()
    
    # Mapa de palavras-chave para datasets
    keywords_map = {
        "vacinacao-covid": [
            "vacina", "vacinação", "covid", "doses", "imunização", "aplicadas",
            "fabricante", "lote", "injeção", "pfizer", "astrazeneca", "dose"
        ],
        "dengue-2024": [
            "dengue", "aedes", "mosquito", "vetor", "epidemia", "surto",
            "sintomas", "febre", "casos dengue", "óbitos", "arbovirose"
        ],
        "influenza-2025": [
            "influenza", "gripe", "h1n1", "h3n2", "iav", "tipo a", "tipo b",
            "tosse", "resfriado", "antiviral"
        ]
    }
    
    # Calcular score para cada dataset
    scores = {}
    for dataset_id, keywords in keywords_map.items():
        score = sum(1 for kw in keywords if kw in question_lower)
        scores[dataset_id] = score
    
    # Retornar dataset com maior score
    best_dataset = max(scores, key=scores.get)
    best_score = scores[best_dataset]
    
    # Apenas retornar se houver alguma correspondência
    return best_dataset if best_score > 0 else None