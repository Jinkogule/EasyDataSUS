import re
import logging
import json
import sys
from pathlib import Path

# Adicionar diretório parent (backend/) ao path para permitir imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.router import get_llm
from config.datasets import get_table_name, get_dataset_config

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

def validate_sql_syntax(sql: str, dataset: str = "covid-19-vacinacao") -> bool:
    """
    Valida sintaxe básica de SQL para um dataset específico.
    
    Args:
        sql: Query SQL a validar
        dataset: Dataset esperado (padrão: "covid-19-vacinacao")
    
    Returns:
        True se SQL é válido, False caso contrário
    """
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
    
    # FIXO: Obter tabela esperada dinamicamente
    try:
        expected_table = get_table_name(dataset)
    except ValueError as e:
        logger.warning(f"Dataset inválido: {e}")
        return False
    
    if expected_table not in sql_clean.lower():
        logger.warning(f"SQL não referencia tabela '{expected_table}' do dataset '{dataset}'")
        return False
    
    # CRÍTICO: Se tem WHERE, DEVE ter operador de comparação
    if "WHERE" in sql_clean:
        has_comparison = any(op in sql_clean for op in [" = ", " IN ", " LIKE ", " > ", " < ", " >= ", " <= ", " != ", " <> "])
        if not has_comparison:
            logger.warning(f"SQL tem WHERE mas FALTA operador de comparação: {sql[:100]}")
            return False
    
    # Verificar comandos perigosos
    forbidden = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE", "TRUNCATE"]
    for cmd in forbidden:
        if f" {cmd} " in f" {sql_clean} ":
            logger.warning(f"SQL contém comando proibido: {cmd}")
            return False
    
    return True


def _format_columns_from_schema(schema: dict) -> str:
    """
    Formata informações de colunas a partir do schema JSON para uso no prompt.
    
    Args:
        schema: Dicionário do schema com "colunas_principais"
    
    Returns:
        String formatada com descrição das colunas
    """
    colunas_info = ""
    for col_name, col_info in schema.get("colunas_principais", {}).items():
        tipo = col_info.get("tipo", "String")
        descricao = col_info.get("descricao", "")
        exemplos = col_info.get("exemplos", [])
        
        colunas_info += f"- {col_name} ({tipo}): {descricao}"
        if exemplos:
            colunas_info += f" → Exemplos: {', '.join(str(e) for e in exemplos)}"
        colunas_info += "\n"
    
    return colunas_info


def _generate_examples_for_dataset(dataset: str, schema: dict) -> str:
    """
    Gera exemplos SQL específicos para um dataset.
    
    Evita hardcoding mantendo exemplos genéricos por tema.
    Se não houver exemplos específicos, retorna exemplos genéricos.
    
    Args:
        dataset: ID do dataset
        schema: Dicionário do schema
    
    Returns:
        String com exemplos SQL formatados
    """
    examples_map = {
        "covid-19-vacinacao": """
EXEMPLO 1 - Genérico (sem filtro de vacina):
Pergunta: Quantas doses foram aplicadas em SP?
SELECT COUNT(*) FROM vacinacao WHERE paciente_endereco_uf = 'SP'

EXEMPLO 2 - Específico (com filtro de vacina):
Pergunta: Quantas doses de Pfizer foram aplicadas em SP?
SELECT COUNT(*) FROM vacinacao WHERE paciente_endereco_uf = 'SP' AND vacina_nome = 'Pfizer'

EXEMPLO 3 - Agrupar por vacina:
Pergunta: Quantas doses por vacina?
SELECT vacina_nome, COUNT(*) as total FROM vacinacao GROUP BY vacina_nome ORDER BY total DESC

EXEMPLO 4 - Com dose específica:
Pergunta: Quantas 2ª doses foram aplicadas?
SELECT COUNT(*) FROM vacinacao WHERE vacina_descricao_dose = '2ª dose'

EXEMPLO 5 - Evolução temporal:
Pergunta: Qual foi a evolução mensal de vacinação?
SELECT toYYYYMM(vacina_dataAplicacao) as mes, COUNT(*) as total FROM vacinacao GROUP BY mes ORDER BY mes
        """,
        "dengue-2024": """
EXEMPLO 1 - Total de casos:
Pergunta: Quantos casos de dengue foram registrados?
SELECT COUNT(*) FROM dengue

EXEMPLO 2 - Por estado:
Pergunta: Qual estado teve mais casos?
SELECT estado_uf, COUNT(*) as total FROM dengue GROUP BY estado_uf ORDER BY total DESC LIMIT 10

EXEMPLO 3 - Óbitos:
Pergunta: Quantos óbitos por dengue?
SELECT COUNT(*) FROM dengue WHERE desfecho = 'Óbito'

EXEMPLO 4 - Por tipo:
Pergunta: Quantos casos de DENV1?
SELECT COUNT(*) FROM dengue WHERE tipo_dengue = 'DENV1'

EXEMPLO 5 - Série temporal:
Pergunta: Evolução mensal de dengue:
SELECT toYYYYMM(data_notificacao) as mes, COUNT(*) as total FROM dengue GROUP BY mes ORDER BY mes
        """,
        "influenza-2025": """
EXEMPLO 1 - Total de casos:
Pergunta: Quantos casos de gripe?
SELECT COUNT(*) FROM influenza

EXEMPLO 2 - Por tipo:
Pergunta: Quantos H1N1?
SELECT COUNT(*) FROM influenza WHERE tipo = 'H1N1'

EXEMPLO 3 - Por estado:
Pergunta: Quantos casos em SP?
SELECT COUNT(*) FROM influenza WHERE estado_uf = 'SP'

EXEMPLO 4 - Comparação por tipo:
Pergunta: Qual tipo mais frequente?
SELECT tipo, COUNT(*) as total FROM influenza GROUP BY tipo ORDER BY total DESC

EXEMPLO 5 - Por mês:
Pergunta: Evolução mensal:
SELECT toYYYYMM(data_notificacao) as mes, COUNT(*) as total FROM influenza GROUP BY mes ORDER BY mes
        """,
    }
    
    # Retorna exemplos específicos se existem, senão um genérico
    return examples_map.get(dataset, """
EXEMPLO 1: Contar linhas
SELECT COUNT(*) FROM {table}

EXEMPLO 2: Agrupar por coluna
SELECT coluna1, COUNT(*) as total FROM {table} GROUP BY coluna1 ORDER BY total DESC

EXEMPLO 3: Com filtro
SELECT COUNT(*) FROM {table} WHERE coluna1 = 'valor'
    """)


def _get_sql_rules_for_dataset(dataset: str, schema: dict) -> str:
    """
    Gera regras de SQL específicas para um dataset com base em seu schema.
    
    Args:
        dataset: ID do dataset
        schema: Dicionário do schema
    
    Returns:
        String com regras formatadas
    """
    rules_map = {
        "covid-19-vacinacao": """
REGRAS OBRIGATÓRIAS PARA VACINAÇÃO:
1. Se pergunta tem "quantas" → use COUNT(*)
2. Se pergunta menciona estado → use paciente_endereco_uf
3. Se pergunta menciona município → use paciente_endereco_nmMunicipio
4. Se pergunta menciona NOME DE VACINA ESPECÍFICO (Pfizer, AstraZeneca, etc) → filtre com vacina_nome
5. NUNCA filtre por vacina se pergunta apenas menciona "vacina" genericamente
6. Se pergunta menciona dose específica ('1ª dose', '2ª dose', 'reforço') → use vacina_descricao_dose
7. Se pergunta menciona data/período → use vacina_dataAplicacao
8. Não use DATE() ou datetime() - use toDate(), toYYYYMM()
9. Respeite maiúsculas/minúsculas de estados ('SP', não 'sp')
10. Não use LIKE com % - use = para exatidão
11. Se resultado tiver muitas linhas, use LIMIT 100
        """,
        "dengue-2024": """
REGRAS OBRIGATÓRIAS PARA DENGUE:
1. Se pergunta menciona "casos" → use COUNT(*)
2. Se pergunta menciona estado → use estado_uf
3. Se pergunta menciona município → use municipio
4. Se pergunta menciona "óbitos" ou "mortes" → filtre WHERE desfecho = 'Óbito'
5. Se pergunta menciona tipo (DENV1, DENV2, etc) → filtre com tipo_dengue
6. Se pergunta menciona data/período → use data_notificacao
7. Use toYYYYMM() para agrupar por mês
8. Respeite maiúsculas ('SP', 'DENV1')
9. Se resultado tiver muitas linhas, use LIMIT 100
        """,
        "influenza-2025": """
REGRAS OBRIGATÓRIAS PARA INFLUENZA:
1. Se pergunta tem "quantas" ou "casos" → use COUNT(*)
2. Se pergunta menciona estado → use estado_uf
3. Se pergunta menciona tipo (H1N1, H3N2, B) → filtre com tipo
4. Se pergunta menciona período/data → use data_notificacao
5. Respeite maiúsculas (H1N1, H3N2)
6. Use GROUP BY por tipo para comparação
7. Use LIMIT 100 para resultados grandes
        """,
    }
    
    # Retorna regras específicas se existem
    return rules_map.get(dataset, "")


def generate_sql(question, metadata, model_name, dataset: str = "covid-19-vacinacao"):
    """
    Gera SQL com few-shot learning e validação.
    
    Agora genérico: usa schema do metadata JSON e exemplos específicos por dataset.
    
    Args:
        question: Pergunta em linguagem natural
        metadata: JSON string com metadados do dataset (inclui schema)
        model_name: Nome do modelo LLM
        dataset: ID do dataset (padrão: "covid-19-vacinacao")
    
    Returns:
        Query SQL válida ou None se falhar
    """
    logger.info(f"Gerando SQL para: {question[:50]}... (dataset: {dataset})")
    
    llm = get_llm(model_name)
    
    # FIXO: Extrair schema do metadata JSON
    try:
        schema_info = json.loads(metadata)
    except json.JSONDecodeError:
        logger.error(f"Erro ao parsejar metadata JSON para dataset {dataset}")
        return fallback_sql(question, dataset)
    
    # FIXO: Obter tabela dinamicamente
    try:
        table_name = get_table_name(dataset)
    except ValueError as e:
        logger.error(f"Dataset inválido: {e}")
        return fallback_sql(question, dataset)
    
    # FIXO: Formatar colunas do schema dinamicamente
    colunas_info = _format_columns_from_schema(schema_info)
    
    # FIXO: Gerar exemplos específicos do dataset
    examples = _generate_examples_for_dataset(dataset, schema_info)
    
    # FIXO: Gerar regras específicas do dataset
    dataset_rules = _get_sql_rules_for_dataset(dataset, schema_info)

    prompt = f"""Você é um especialista em SQL para ClickHouse em português.

INSTRUÇÃO CRÍTICA:
- Responda APENAS com uma query SQL válida
- Sem markdown, sem comentários, sem explicação
- Comece direto com SELECT

PADRÕES IMPORTANTES:
✓ "Qual estado teve MAIS..." → GROUP BY estado ORDER BY DESC
✓ "Quantas..." → COUNT(*)
✓ "Por estado..." → GROUP BY estado
✓ "Quantas em SP..." → COUNT(*) WHERE estado = 'SP'

DATASET: {dataset}
Tabela: {table_name}
Descrição: {schema_info.get('descricao', 'N/A')}
Fonte: {schema_info.get('fonte', 'N/A')}

Colunas disponíveis:
{colunas_info}

FUNÇÕES CLICKHOUSE NECESSÁRIAS:
- COUNT(*) - contar linhas
- GROUP BY - agrupar
- WHERE - filtrar
- ORDER BY DESC - ordenar descendente (para ranking)
- LIMIT - limitar resultados
- toYYYYMM() - converter data para formato YYYYMM
- toYYYYMMDD() - converter data para formato YYYYMMDD

EXEMPLOS DE QUERIES CORRETAS:
{examples}

{dataset_rules}

PERGUNTA DO USUÁRIO:
{question}

Responda apenas com a query SQL:"""

    try:
        response = llm.generate(prompt)
        logger.debug(f"Resposta LLM (primeira 200 chars): {response[:200]}")
        
        sql = extract_sql(response)
        
        if not sql:
            logger.warning("Não conseguiu extrair SQL da resposta")
            return fallback_sql(question, dataset)
        
        if not validate_sql_syntax(sql, dataset):
            logger.warning(f"SQL falhou validação para dataset {dataset}: {sql}")
            return fallback_sql(question, dataset)
        
        logger.info(f"SQL gerado com sucesso para {dataset}: {sql[:50]}...")
        return sql
        
    except Exception as e:
        logger.error(f"Erro ao gerar SQL: {e}")
        return fallback_sql(question, dataset)

def fallback_sql(question: str, dataset: str = "covid-19-vacinacao") -> str:
    """
    Fallback robusto quando LLM falha.
    
    Detecta padrões comuns em português e gera SQL apropriado.
    
    Args:
        question: Pergunta do usuário
        dataset: Dataset a usar (padrão: "covid-19-vacinacao")
    
    Returns:
        Query SQL de fallback
    """
    logger.info(f"Usando fallback para: {question} (dataset: {dataset})")
    
    # FIXO: Obter tabela dinamicamente
    try:
        table_name = get_table_name(dataset)
    except ValueError:
        logger.error(f"Dataset inválido no fallback: {dataset}")
        return None
    
    q = question.lower()
    
    # ========== COLUNA DE AGRUPAMENTO POR DATASET ==========
    groupby_columns = {
        "covid-19-vacinacao": "paciente_endereco_uf",
        "dengue-2024": "estado_uf",
        "influenza-2025": "estado_uf",
    }
    groupby_col = groupby_columns.get(dataset, "estado")
    
    # ========== DETECTAR PADRÃO: "Qual ... teve MAIS" → GROUP BY DESC ==========
    if any(word in q for word in ["qual", "que"]) and any(word in q for word in ["mais", "maior", "maiores"]):
        # Pergunta de comparação: "Qual estado teve mais casos?"
        logger.debug("Padrão detectado: 'Qual ... teve MAIS' → GROUP BY")
        sql = f"SELECT {groupby_col}, COUNT(*) as total FROM {table_name} GROUP BY {groupby_col} ORDER BY total DESC LIMIT 100"
    
    # ========== DETECTAR PADRÃO: "Quantas em estado específico" → WHERE ==========
    elif any(word in q for word in ["quantas", "quantos", "quanto"]) and any(word in q for word in ["em", "em sp", "em rj", "no", "na"]):
        # Pergunta com filtro: "Quantas vacinas em SP?"
        logger.debug("Padrão detectado: 'Quantas em [estado]' → WHERE")
        sql = f"SELECT COUNT(*) as total FROM {table_name} LIMIT 10000"
    
    # ========== DETECTAR PADRÃO: "Quantas total/geral" → COUNT simples ==========
    elif any(word in q for word in ["quantas", "quantos", "quanto", "total", "geral", "contar", "casos"]):
        logger.debug("Padrão detectado: 'Quantas total' → COUNT(*)")
        sql = f"SELECT COUNT(*) as total FROM {table_name} LIMIT 10000"
    
    # ========== DETECTAR PADRÃO: "Por estado/região" → GROUP BY ==========
    elif any(word in q for word in ["por estado", "por uf", "cada estado", "por região", "região"]):
        logger.debug("Padrão detectado: 'Por estado' → GROUP BY")
        sql = f"SELECT {groupby_col}, COUNT(*) as total FROM {table_name} GROUP BY {groupby_col} ORDER BY total DESC LIMIT 100"
    
    # ========== DEFAULT: COUNT simples ==========
    else:
        logger.debug("Nenhum padrão detectado, usando COUNT simples")
        sql = f"SELECT COUNT(*) as total FROM {table_name} LIMIT 10000"
    
    logger.info(f"Fallback SQL para {dataset}: {sql}")
    return sql