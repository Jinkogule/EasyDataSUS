import re
import logging
from llm.router import get_llm

logger = logging.getLogger(__name__)

def extract_sql(text: str) -> str:
    """Extrai SQL da resposta do LLM com múltiplas estratégias"""
    
    if not text:
        return None
    
    # 1. Try markdown code block ```sql
    match = re.search(r"```(?:sql)?\s*(SELECT\s+.+?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        sql = match.group(1).strip()
        logger.debug(f"SQL extraído do bloco markdown: {sql[:50]}...")
        return sql
    
    # 2. Extract SELECT ... LIMIT pattern (mais específico e robusto)
    # Procura por SELECT ... até LIMIT ou fim
    match = re.search(
        r"(SELECT\s+.+?(?:LIMIT\s+\d+)?)\s*(?:$|\n\n)",
        text,
        re.DOTALL | re.IGNORECASE
    )
    if match:
        sql = match.group(1).strip()
        # Validar que tem WHERE com comparação se necessário
        if "WHERE" in sql.upper():
            # Se tem WHERE, deve ter = ou IN ou LIKE
            if not any(op in sql.upper() for op in [" = ", " IN ", " LIKE ", " > ", " < "]):
                logger.warning(f"SQL tem WHERE mas sem operador de comparação: {sql[:100]}")
                return None
        logger.debug(f"SQL extraído com regex SELECT...LIMIT: {sql[:50]}...")
        return sql
    
    # 3. Fallback simples: tudo que começa com SELECT até primeira quebra de linha dupla
    if "SELECT" in text.upper():
        idx = text.upper().find("SELECT")
        # Pegar desde SELECT até LIMIT ou fim de parágrafo
        candidate = text[idx:].split("\n\n")[0].strip()
        
        # Validar mínima integridade
        if candidate.upper().startswith("SELECT") and "FROM" in candidate.upper():
            logger.debug(f"SQL extraído por fallback simples: {candidate[:50]}...")
            return candidate
    
    logger.warning(f"Não conseguiu extrair SQL válido de: {text[:100]}")
    return None

def validate_sql_syntax(sql: str) -> bool:
    """Valida sintaxe básica de SQL"""
    if not sql:
        return False
    
    sql_clean = sql.strip().upper()
    
    # Regras de validação
    if not sql_clean.startswith("SELECT"):
        logger.warning("SQL não começa com SELECT")
        return False
    
    if "FROM" not in sql_clean:
        logger.warning("SQL não possui FROM")
        return False
    
    # Verificar se referencia vacinacao (case-insensitive)
    if "vacinacao" not in sql_clean.lower():
        logger.warning("SQL não referencia tabela 'vacinacao'")
        return False
    
    # CRÍTICO: Se tem WHERE, DEVE ter operador de comparação
    if "WHERE" in sql_clean:
        has_comparison = any(op in sql_clean for op in [" = ", " IN ", " LIKE ", " > ", " < ", " >= ", " <= ", " != ", " <> "])
        if not has_comparison:
            logger.warning(f"⚠️ SQL tem WHERE mas FALTA operador de comparação: {sql[:100]}")
            return False
    
    # Verificar comandos perigosos
    forbidden = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE"]
    for cmd in forbidden:
        if f" {cmd} " in f" {sql_clean} ":
            logger.warning(f"SQL contém comando proibido: {cmd}")
            return False
    
    return True

def generate_sql(question, metadata, model_name):
    """Gera SQL com few-shot learning e validação"""
    
    logger.info(f"Gerando SQL para: {question[:50]}...")
    
    llm = get_llm(model_name)

    # Few-shot examples para melhor performance
    examples = """
EXEMPLO 1:
Pergunta: quantas vacinas foram aplicadas em SP?
SELECT COUNT(*) FROM vacinacao WHERE paciente_endereco_uf = 'SP'

EXEMPLO 2:
Pergunta: quantas doses por vacina?
SELECT vacina_nome, COUNT(*) as total FROM vacinacao GROUP BY vacina_nome

EXEMPLO 3:
Pergunta: qual foi a evolução mensal?
SELECT toYYYYMM(vacina_dataAplicacao) as mes, COUNT(*) as total FROM vacinacao GROUP BY mes ORDER BY mes

EXEMPLO 4:
Pergunta: quantas aplicações em Fluorianópolis?
SELECT COUNT(*) as total FROM vacinacao WHERE paciente_endereco_nmMunicipio = 'Florianópolis'
"""

    prompt = f"""Você é um especialista em SQL para ClickHouse.

INSTRUÇÃO CRÍTICA:
- Responda APENAS com uma query SQL válida
- Sem markdown, sem comentários, sem explicação
- Comece direto com SELECT

SCHEMA DO BANCO:
Tabela: vacinacao

Colunas disponíveis:
- paciente_endereco_uf (Estado: 'SP', 'RJ', 'SC', etc)
- paciente_endereco_nmMunicipio (Nome do município)
- paciente_idade (Idade como Int32)
- paciente_dataNascimento (Data como YYYY-MM-DD)
- paciente_enumSexoBiologico (Sexo: 'M', 'F')
- vacina_dataAplicacao (Data da aplicação: YYYY-MM-DD)
- vacina_nome (Nome da vacina: 'Pfizer', 'AstraZeneca', etc)
- vacina_descricao_dose (Dose: '1ª dose', '2ª dose', 'Reforço', etc)
- vacina_lote (Número do lote)
- estabelecimento_razaoSocial (Nome do estabelecimento)
- sistema_origem (Sistema: 'SIPNI', 'CONECTA-SUS', etc)

FUNÇÕES CLICKHOUSE NECESSÁRIAS:
- COUNT(*) - contar linhas
- GROUP BY - agrupar
- WHERE - filtrar
- ORDER BY - ordenar
- LIMIT - limitar resultados
- toYYYYMM() - converter data para formato YYYYMM
- toYYYYMMDD() - converter data para formato YYYYMMDD

EXEMPLOS DE QUERIES CORRETAS:
{examples}

REGRAS OBRIGATÓRIAS:
1. Se pergunta tem "quantas" → use COUNT(*)
2. Se pergunta menciona estado → use paciente_endereco_uf
3. Se pergunta menciona município → use paciente_endereco_nmMunicipio
4. Se pergunta menciona vacina → use vacina_nome
5. Se pergunta menciona dose → use vacina_descricao_dose
6. Se pergunta menciona data → use vacina_dataAplicacao com toDate() se necessário
7. Não use DATE() ou datetime() - use toDate(), toYYYYMM(), etc
8. Respeite maiúsculas/minúsculas de estados ('SP', não 'sp')
9. Não use LIKE com % - use = para exatidão
10. Se resultado tiver muitas linhas, use LIMIT 100

PERGUNTA DO USUÁRIO:
{question}

Responded apenas com a query SQL:"""

    try:
        response = llm.generate(prompt)
        logger.debug(f"Resposta LLM (primeira 200 chars): {response[:200]}")
        
        sql = extract_sql(response)
        
        if not sql:
            logger.warning("Não conseguiu extrair SQL da resposta")
            return fallback_sql(question)
        
        if not validate_sql_syntax(sql):
            logger.warning(f"SQL falhou validação: {sql}")
            return fallback_sql(question)
        
        logger.info(f"SQL gerado com sucesso: {sql[:50]}...")
        return sql
        
    except Exception as e:
        logger.error(f"Erro ao gerar SQL: {e}")
        return fallback_sql(question)

def fallback_sql(question: str) -> str:
    """Fallback robusto quando LLM falha"""
    
    logger.info(f"Usando fallback para: {question}")
    
    q = question.lower()
    
    # Estados brasileiros mapeados
    estados = {
        "sp": "SP", "são paulo": "SP",
        "rj": "RJ", "rio de janeiro": "RJ",
        "sc": "SC", "santa catarina": "SC",
        "es": "ES", "espírito santo": "ES",
        "ac": "AC", "acre": "AC",
        "mg": "MG", "minas gerais": "MG",
        "rs": "RS", "rio grande do sul": "RS",
        "ba": "BA", "bahia": "BA",
    }
    
    estado_detectado = None
    for key, value in estados.items():
        if key in q:
            estado_detectado = value
            break
    
    # Detectar intenção na pergunta
    if any(word in q for word in ["quantas", "quantidade", "total", "contar"]):
        if estado_detectado:
            sql = f"SELECT COUNT(*) FROM vacinacao WHERE paciente_endereco_uf = '{estado_detectado}'"
        else:
            sql = "SELECT COUNT(*) FROM vacinacao"
    
    elif any(word in q for word in ["por estado", "por uf", "cada estado"]):
        sql = "SELECT paciente_endereco_uf, COUNT(*) FROM vacinacao GROUP BY paciente_endereco_uf"
    
    elif any(word in q for word in ["por vacina", "cada vacina", "tipos"]):
        sql = "SELECT vacina_nome, COUNT(*) FROM vacinacao GROUP BY vacina_nome"
    
    else:
        sql = "SELECT COUNT(*) FROM vacinacao"
    
    logger.info(f"Fallback SQL: {sql}")
    return sql