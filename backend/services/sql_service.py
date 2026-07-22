import re
import logging
import json
import os
import sys
from pathlib import Path

# Adicionar diretório parent (backend/) ao path para permitir imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from llm.router import get_llm
from config.datasets import get_table_name, get_dataset_config

logger = logging.getLogger(__name__)


def _get_schema_columns(schema: dict) -> dict:
    """Retorna o mapa de colunas aceitando os formatos antigo e novo do schema."""

    if not isinstance(schema, dict):
        return {}

    for key in ("colunas_principais", "columns"):
        columns = schema.get(key)
        if isinstance(columns, dict) and columns:
            return columns

    return {}


def _get_schema_value(schema: dict, *keys: str, default=""):
    """Obtém o primeiro valor não vazio entre chaves alternativas do schema."""

    if not isinstance(schema, dict):
        return default

    for key in keys:
        value = schema.get(key)
        if value not in (None, "", {}, []):
            return value

    return default


def _get_column_text(column_info: dict, *keys: str, default=""):
    """Obtém o primeiro texto não vazio entre chaves alternativas da coluna."""

    if not isinstance(column_info, dict):
        return default

    for key in keys:
        value = column_info.get(key)
        if value not in (None, "", {}, []):
            return value

    return default


def _format_examples(examples) -> str:
    if isinstance(examples, list):
        return ", ".join(str(example) for example in examples)
    if examples not in (None, "", {}, []):
        return str(examples)
    return ""

def extract_sql(text: str) -> str:
    """Extrai SQL da resposta do LLM com múltiplas estratégias"""
    
    if not text:
        return None
    
    # Limpar backticks e artefatos no final de tudo
    text = text.rstrip().rstrip('`')
    
    # 1. Try markdown code block ```sql
    match = re.search(r"```(?:sql)?\s*((?:WITH|SELECT)\s+.+?)(?:```|$)", text, re.DOTALL | re.IGNORECASE)
    if match:
        sql = match.group(1).strip().rstrip('`')
        if sql and sql.upper().startswith("SELECT") and "FROM" in sql.upper():
            logger.debug(f"SQL extraído do bloco markdown: {sql[:50]}...")
            return sql
    
    # 2. Extract SELECT ... pattern (mais específico e robusto)
    # Procura por SELECT até uma quebra natural: fim de parágrafo (dupla quebra), backtick, ou fim do texto
    match = re.search(
        r"((?:WITH|SELECT)\s+.+?)(?:\n\n|```|$)",
        text,
        re.DOTALL | re.IGNORECASE
    )
    if match:
        sql = match.group(1).strip().rstrip('`').rstrip()
        # Remover qualquer explicação ou comentário no final
        sql = sql.split('\n\n')[0].strip()
        
        # Validar que tem WHERE com comparação se necessário
        if "WHERE" in sql.upper():
            # Se tem WHERE, deve ter = ou IN ou LIKE ou comparador
            if not any(op in sql.upper() for op in [" = ", " IN ", " LIKE ", " > ", " < "]):
                logger.warning(f"SQL tem WHERE mas sem operador de comparação: {sql[:100]}")
                return None
        if sql and (sql.upper().startswith("SELECT") or sql.upper().startswith("WITH")) and "FROM" in sql.upper():
            logger.debug(f"SQL extraído com regex SELECT...LIMIT: {sql[:50]}...")
            return sql
    
    # 3. Fallback simples: tudo que começa com SELECT até primeira quebra de linha dupla ou backtick
    if "SELECT" in text.upper() or "WITH" in text.upper():
        select_idx = text.upper().find("SELECT")
        with_idx = text.upper().find("WITH")
        if with_idx != -1 and (select_idx == -1 or with_idx < select_idx):
            idx = with_idx
        else:
            idx = select_idx
        # Pegar desde SELECT até LIMIT, backtick, ou fim de parágrafo
        raw = text[idx:]
        # Remove backticks
        raw = raw.rstrip('`')
        # Pega até quebra dupla, backtick, ou fim
        candidates = [
            raw.split("\n\n")[0],  # Até quebra dupla
            raw.split("```")[0],   # Até backtick
            raw.split("\n```")[0], # Até backtick com newline
        ]
        
        for candidate in candidates:
            candidate = candidate.strip().rstrip('`')
            # Validar mínima integridade
            if (candidate.upper().startswith("SELECT") or candidate.upper().startswith("WITH")) and "FROM" in candidate.upper():
                logger.debug(f"SQL extraído por fallback simples: {candidate[:50]}...")
                return candidate
    
    logger.warning(f"Não conseguiu extrair SQL válido de: {text[:100]}")
    return None

def validate_sql_syntax(sql: str, dataset: str = "covid-19-vacinacao", original_question: str = "") -> bool:
    """
    Valida sintaxe básica de SQL para um dataset específico.
    
    Args:
        sql: Query SQL a validar
        dataset: Dataset esperado (padrão: "covid-19-vacinacao")
        original_question: Pergunta original para validar consistência (ex: detectar SELECT * em "quantas...")
    
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
    
    # CRÍTICO: Validar que "SELECT *" não é usado para perguntas de contagem
    if original_question:
        original_lower = original_question.lower()
        is_count_question = any(original_lower.startswith(q) for q in ["quantas", "quantos", "qual é o total", "qual é a quantidade"])
        
        # Se é pergunta de contagem, NÃO pode ser SELECT *
        if is_count_question and "SELECT *" in sql_clean:
            logger.warning(f"ERRO CRÍTICO: Pergunta sobre 'quantas/quantos' gerou SELECT * (deve ser COUNT): {sql[:100]}")
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

    # Validação semântica mínima: impede agregações válidas sintaticamente,
    # mas incompatíveis com a intenção analítica da pergunta.
    question_lower = original_question.lower() if original_question else ""
    asks_by_state = any(term in question_lower for term in ("por estado", "por uf", "cada estado", "estados"))
    asks_municipality = any(term in question_lower for term in ("município", "municipio", "cidade"))
    asks_ranking = any(term in question_lower for term in ("maior", "maiores", "mais", "ranking", "top"))

    if dataset == "covid-19-vacinacao" and asks_by_state and asks_ranking:
        if "GROUP BY" not in sql_clean or "COUNT(" not in sql_clean:
            logger.warning("Ranking de vacinação por estado exige GROUP BY e COUNT")
            return False
        if "MAX(PACIENTE_ENDERECO_UF)" in sql_clean:
            logger.warning("Código de UF não pode ser maximizado como métrica")
            return False

    if dataset == "leitos" and "uti" in question_lower:
        if asks_by_state and (
            "SUM(UTI_" not in sql_clean
            or "GROUP BY" not in sql_clean
            or "MAX(COMP)" not in sql_clean
        ):
            logger.warning("Capacidade de UTI por estado exige SUM, GROUP BY e competência mais recente")
            return False
        if original_question.lower().startswith("quais") and asks_municipality:
            if "COUNT(*)" in sql_clean or "WHERE" not in sql_clean or "MAX(COMP)" not in sql_clean:
                logger.warning("Listagem de municípios com UTI exige filtro de capacidade e competência")
                return False

    asks_ratio = any(
        term in question_lower
        for term in ("proporção", "proporcao", "percentual", "porcentagem", "em relação")
    )
    if dataset == "leitos" and asks_ratio and "leitos sus" in question_lower:
        required_fragments = (
            "SUM(LEITOS_SUS)",
            "SUM(LEITOS_EXISTENTES)",
            "GROUP BY",
            "MAX(COMP)",
        )
        if not all(fragment in sql_clean for fragment in required_fragments) or "/" not in sql_clean:
            logger.warning("Proporção de leitos SUS exige somas, divisão, agrupamento e competência mais recente")
            return False

    if dataset == "surtos-srag" and asks_by_state:
        if "GROUP BY" not in sql_clean or "COUNT(" not in sql_clean:
            logger.warning("Notificações de SRAG por estado exigem GROUP BY e COUNT")
            return False

    if dataset == "atencao-basica" and asks_municipality and asks_ranking:
        if "GROUP BY" not in sql_clean or "COUNT(" not in sql_clean:
            logger.warning("Ranking municipal de UBS exige GROUP BY e COUNT")
            return False
        if "MAX(IBGE)" in sql_clean:
            logger.warning("Código IBGE não pode ser maximizado como métrica")
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
    for col_name, col_info in _get_schema_columns(schema).items():
        tipo = _get_column_text(col_info, "tipo", "type", default="String")
        descricao = _get_column_text(col_info, "descricao", "description", default="")
        exemplos = _get_column_text(col_info, "exemplos", "examples", "valores_possiveis", default=[])
        
        colunas_info += f"- {col_name} ({tipo}): {descricao}"
        formatted_examples = _format_examples(exemplos)
        if formatted_examples:
            colunas_info += f" → Exemplos: {formatted_examples}"
        colunas_info += "\n"
    
    return colunas_info


def _generate_examples_for_dataset(dataset: str, schema: dict, table_name: str) -> str:
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

EXEMPLO 6 - Estatísticas numéricas:
Pergunta: Qual é a idade média das pessoas vacinadas?
SELECT AVG(paciente_idade) as idade_media FROM vacinacao

Pergunta: Qual é a idade mínima e máxima?
SELECT MIN(paciente_idade) as minima, MAX(paciente_idade) as maxima FROM vacinacao
        """,
        "leitos": """
EXEMPLO 1 - Capacidade total:
Pergunta: Qual é a capacidade total de leitos?
SELECT SUM(LEITOS_EXISTENTES) as total_leitos FROM leitos

EXEMPLO 2 - Leitos por estado:
Pergunta: Qual estado tem mais leitos?
SELECT UF, SUM(LEITOS_EXISTENTES) as total_leitos FROM leitos GROUP BY UF ORDER BY total_leitos DESC

EXEMPLO 3 - Leitos SUS por estado:
Pergunta: Qual é a cobertura SUS por estado?
SELECT UF, SUM(LEITOS_EXISTENTES) as leitos_total, SUM(LEITOS_SUS) as leitos_sus, ROUND((SUM(LEITOS_SUS) / SUM(LEITOS_EXISTENTES)) * 100, 2) as percentual_sus FROM leitos GROUP BY UF ORDER BY percentual_sus DESC

EXEMPLO 4 - UTI disponível:
Pergunta: Quantos leitos de UTI adulto estão disponíveis pelo SUS?
SELECT SUM(UTI_ADULTO_SUS) as uti_adulto_sus FROM leitos

EXEMPLO 5 - UTI especializada com filtro:
Pergunta: Quais cidades têm UTI neonatal?
SELECT MUNICIPIO, UF, UTI_NEONATAL_EXIST FROM leitos WHERE UTI_NEONATAL_EXIST > 0 ORDER BY MUNICIPIO LIMIT 100

EXEMPLO 6 - Por tipo de gestão:
Pergunta: Qual é a distribuição de leitos por tipo de gestão?
SELECT TP_GESTAO, SUM(LEITOS_EXISTENTES) as total_leitos, SUM(LEITOS_SUS) as leitos_sus FROM leitos GROUP BY TP_GESTAO ORDER BY total_leitos DESC

EXEMPLO 7 - UTI por região:
Pergunta: Qual região tem mais leitos de UTI?
SELECT REGIAO, SUM(UTI_TOTAL_EXIST) as uti_total FROM leitos GROUP BY REGIAO ORDER BY uti_total DESC
        """,
        "surtos-srag": """
EXEMPLO 1 - Total de notificações por UF:
Pergunta: Quantos casos de SRAG foram notificados por estado?
SELECT SG_UF_NOT, COUNT(*) as total FROM srag GROUP BY SG_UF_NOT ORDER BY total DESC

EXEMPLO 2 - Casos por ano:
Pergunta: Qual ano teve mais notificações?
SELECT year(DT_NOTIFIC) as ano, COUNT(*) as total FROM srag GROUP BY ano ORDER BY total DESC

EXEMPLO 3 - Casos por sexo:
Pergunta: Qual a distribuição por sexo?
SELECT CS_SEXO, COUNT(*) as total FROM srag GROUP BY CS_SEXO ORDER BY total DESC

EXEMPLO 4 - Idade média:
Pergunta: Qual é a idade média dos casos?
SELECT AVG(NU_IDADE_N) as idade_media FROM srag
        """,
        "atencao-basica": """
EXEMPLO 1 - Total de UBS por UF:
Pergunta: Quantas UBS existem por estado?
SELECT UF, COUNT(*) as total FROM atencao_basica GROUP BY UF ORDER BY total DESC

EXEMPLO 2 - UBS por município:
Pergunta: Quais municípios têm mais UBS?
SELECT IBGE, COUNT(*) as total FROM atencao_basica GROUP BY IBGE ORDER BY total DESC

EXEMPLO 3 - UBS por bairro:
Pergunta: Qual é a distribuição de UBS por bairro?
SELECT BAIRRO, COUNT(*) as total FROM atencao_basica GROUP BY BAIRRO ORDER BY total DESC

EXEMPLO 4 - Coordenadas geográficas:
Pergunta: Quais UBS têm latitude e longitude válidas?
SELECT NOME, UF, IBGE, LATITUDE, LONGITUDE FROM atencao_basica WHERE LATITUDE IS NOT NULL AND LONGITUDE IS NOT NULL LIMIT 100
        """,
    }
    
    # Retorna exemplos específicos se existem, senão um genérico
    return examples_map.get(dataset, f"""
EXEMPLO 1: Contar linhas
SELECT COUNT(*) FROM {table_name or 'tabela'}

EXEMPLO 2: Agrupar por coluna
SELECT coluna1, COUNT(*) as total FROM {table_name or 'tabela'} GROUP BY coluna1 ORDER BY total DESC

EXEMPLO 3: Com filtro
SELECT COUNT(*) FROM {table_name or 'tabela'} WHERE coluna1 = 'valor'
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
8. Se pergunta menciona "idade" (média, mínima, máxima) → use paciente_idade com AVG/MIN/MAX
9. Se pergunta menciona "sexo" → use paciente_enumSexoBiologico com COUNT(*) GROUP BY
10. Não use DATE() ou datetime() - use toDate(), toYYYYMM()
11. Respeite maiúsculas/minúsculas de estados ('SP', não 'sp')
12. Não use LIKE com % - use = para exatidão
13. Se resultado tiver muitas linhas, use LIMIT 100
        """,
        "leitos": """
REGRAS OBRIGATÓRIAS PARA LEITOS:
1. Se pergunta menciona "leitos" genericamente → use LEITOS_EXISTENTES
2. Se pergunta menciona "leitos SUS" → use LEITOS_SUS
3. Se pergunta menciona "UTI" → use UTI_TOTAL_EXIST ou UTI_TOTAL_SUS
4. Se pergunta menciona "UTI adulto" → use UTI_ADULTO_EXIST ou UTI_ADULTO_SUS
5. Se pergunta menciona "UTI pediátrica" → use UTI_PEDIATRICO_EXIST ou UTI_PEDIATRICO_SUS
6. Se pergunta menciona "UTI neonatal" → use UTI_NEONATAL_EXIST ou UTI_NEONATAL_SUS
7. Se pergunta menciona "UTI queimados" → use UTI_QUEIMADO_EXIST ou UTI_QUEIMADO_SUS
8. Se pergunta menciona "UTI coronariana" → use UTI_CORONARIANA_EXIST ou UTI_CORONARIANA_SUS
9. SEMPRE use SUM() para qualquer coluna de leitos (LEITOS_*, UTI_*) quando agrupar por estado/região/município
10. Se pergunta menciona "qual tem mais", "qual estado", "ranking" com leitos → use SUM() + GROUP BY + ORDER BY DESC
11. Se pergunta menciona estado → use UF
12. Se pergunta menciona região → use REGIAO
13. Se pergunta menciona cidade/município → use MUNICIPIO
14. Se pergunta menciona "tipo de gestão" → use TP_GESTAO
15. Para calcular percentual SUS → (SUM(LEITOS_SUS) / SUM(LEITOS_EXISTENTES)) * 100
16. NUNCA use COUNT(*) para contar leitos - sempre use SUM() em colunas de capacidade
17. Use LIMIT 100 para resultados grandes
18. Leitos são fotografias por competência: ao agregar capacidade sem período explícito, filtre COMP = (SELECT MAX(COMP) FROM leitos)
19. Se a pergunta mencionar competência mais recente, o filtro pela maior COMP é obrigatório
        """,
    "surtos-srag": """
REGRAS OBRIGATÓRIAS PARA SRAG:
1. Se perguntar por estado/UF, use SG_UF_NOT
2. Se perguntar por município de notificação, use CO_MUN_NOT
3. Se perguntar por sexo, use CS_SEXO
4. Se perguntar por idade, use NU_IDADE_N
5. Se perguntar por notificação ou período, use DT_NOTIFIC
6. Se perguntar por início dos sintomas, use DT_SIN_PRI
7. Para séries temporais, agregue por year(), month() ou week() sobre DT_NOTIFIC
8. Para distribuição por categoria, use GROUP BY com COUNT(*)
9. Não assuma nomes de municípios quando a base só tiver código IBGE
    """,
    "atencao-basica": """
REGRAS OBRIGATÓRIAS PARA ATENÇÃO BÁSICA:
1. Se perguntar por quantidade de UBS, use COUNT(*)
2. Se perguntar por estado, use UF
3. Se perguntar por município, use IBGE
4. Se perguntar por nome da unidade, use NOME
5. Se perguntar por bairro, use BAIRRO
6. Se perguntar por geolocalização, use LATITUDE e LONGITUDE
7. Não use SUM() para contar unidades; use COUNT(*)
8. Para resultados grandes, use LIMIT 100
    """,
    }
    
    # Retorna regras específicas se existem
    return rules_map.get(dataset, "")


def generate_sql(
    question,
    metadata,
    model_name,
    dataset: str = "covid-19-vacinacao",
    return_mode: bool = False,
):
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

    def pack(sql_value, mode):
        return (sql_value, mode) if return_mode else sql_value

    question_lower = question.lower().strip()
    strategy = os.getenv("SQL_GENERATION_STRATEGY", "deterministic_first").lower()
    has_grouping_request = any(
        term in question_lower
        for term in (
            "por estado", "por uf", "por município", "por municipio",
            "por cidade", "cada estado", "cada município", "cada municipio",
        )
    )
    is_simple_count = any(
        question_lower.startswith(prefix)
        for prefix in ("quantas", "quantos", "qual é o total", "qual a quantidade")
    ) and not has_grouping_request and dataset in {"covid-19-vacinacao", "surtos-srag", "atencao-basica"}
    is_bed_availability_list = (
        dataset == "leitos"
        and question_lower.startswith("quais")
        and "uti" in question_lower
        and any(term in question_lower for term in ("têm", "tem", "possuem", "possui"))
    )
    is_supported_grouped_request = (
        (dataset == "covid-19-vacinacao" and "estado" in question_lower and any(term in question_lower for term in ("maior", "maiores", "mais doses")))
        or (dataset == "leitos" and "uti" in question_lower and has_grouping_request)
        or (dataset == "surtos-srag" and "srag" in question_lower and has_grouping_request)
        or (dataset == "atencao-basica" and any(term in question_lower for term in ("município", "municipio", "cidade")) and any(term in question_lower for term in ("maior", "maiores", "mais")))
    )
    if strategy == "deterministic_first" and (
        is_simple_count or is_bed_availability_list or is_supported_grouped_request
    ):
        return pack(fallback_sql(question, dataset), "deterministic_rule")
    
    llm = get_llm(model_name)
    
    # FIXO: Extrair schema do metadata JSON
    try:
        schema_info = json.loads(metadata)
    except json.JSONDecodeError:
        logger.error(f"Erro ao parsejar metadata JSON para dataset {dataset}")
        return pack(fallback_sql(question, dataset), "deterministic_fallback")
    
    # FIXO: Obter tabela dinamicamente
    try:
        table_name = get_table_name(dataset)
    except ValueError as e:
        logger.error(f"Dataset inválido: {e}")
        return pack(fallback_sql(question, dataset), "deterministic_fallback")
    
    # FIXO: Formatar colunas do schema dinamicamente
    colunas_info = _format_columns_from_schema(schema_info)
    schema_columns = _get_schema_columns(schema_info)
    schema_description = _get_schema_value(schema_info, "descricao", "description", default="N/A")
    schema_source = _get_schema_value(schema_info, "fonte", "source", default="N/A")
    
    # FIXO: Gerar exemplos específicos do dataset
    examples = _generate_examples_for_dataset(dataset, schema_info, table_name)
    
    # FIXO: Gerar regras específicas do dataset
    dataset_rules = _get_sql_rules_for_dataset(dataset, schema_info)

    # DETECÇÃO RÁPIDA DE PADRÃO: Se a pergunta começa com "quantas/quantos", força COUNT(*)
    question_lower = question.lower().strip()
    is_count_question = any(question_lower.startswith(q) for q in ["quantas", "quantos", "qual é o total", "qual é a quantidade"])
    
    if is_count_question:
        # Prompt SIMPLIFICADO para perguntas de contagem
        prompt = f"""Você é um especialista em SQL ClickHouse. Responda APENAS com SQL válido, nada mais.

TAREFA: Gerar COUNT(*) para: {question}

TABELA: {table_name}
COLUNAS: {', '.join(schema_columns.keys())}

REGRA ABSOLUTA: Para "quantas/quantos" → SEMPRE use COUNT(*)

Exemplo: 
  Pergunta: "Quantas vacinas em SP?"
  Resposta: SELECT COUNT(*) AS total_registros FROM vacinacao WHERE paciente_endereco_uf = 'SP'

COLUNAS MAIS USADAS:
{colunas_info}

SQL para "{question}":"""
    else:
        # Prompt COMPLETO para perguntas complexas
        prompt = f"""Você é um especialista em SQL para ClickHouse em português.

INSTRUÇÃO CRÍTICA:
- Responda APENAS com uma query SQL válida
- Sem markdown, sem comentários, sem explicação
- Comece direto com SELECT

PADRÕES IMPORTANTES:
✓ "Qual estado teve MAIS..." → GROUP BY estado ORDER BY DESC + SUM() para números
✓ "Quantas..." → COUNT(*)
✓ "Por estado..." → GROUP BY estado
✓ "Quantas em SP..." → COUNT(*) WHERE estado = 'SP'
✓ "Qual é a idade média..." → AVG(paciente_idade)
✓ "Qual é a idade mínima..." → MIN(paciente_idade)
✓ "Qual estado tem mais LEITOS" → SUM(LEITOS_*) GROUP BY estado ORDER BY DESC
✓ Para LEITOS: NUNCA use COUNT(*), sempre SUM() em colunas de capacidade
✓ SEMPRE adicione LIMIT 100 no final quando não usar GROUP BY com agregação

DATASET: {dataset}
Tabela: {table_name}
Descrição: {schema_description}
Fonte: {schema_source}

Colunas disponíveis:
{colunas_info}

EXEMPLOS DE QUERIES CORRETAS:
{examples}

{dataset_rules}

PERGUNTA DO USUÁRIO:
{question}

Responda apenas com a query SQL:"""

    try:
        response = llm.generate(
            prompt,
            num_predict=int(os.getenv("OLLAMA_SQL_NUM_PREDICT", "512")),
            temperature=0.0,
            timeout_s=int(os.getenv("OLLAMA_SQL_TIMEOUT", "60")),
            max_retries=1,
        )
        logger.debug(f"Resposta LLM (primeira 200 chars): {response[:200]}")
        
        sql = extract_sql(response)
        
        if not sql:
            logger.warning("Não conseguiu extrair SQL da resposta")
            return pack(fallback_sql(question, dataset), "deterministic_fallback")
        
        if not validate_sql_syntax(sql, dataset, question):
            logger.warning(f"SQL falhou validação para dataset {dataset}: {sql}")
            return pack(fallback_sql(question, dataset), "deterministic_fallback")
        
        logger.info(f"SQL gerado com sucesso para {dataset}: {sql[:50]}...")
        return pack(sql, "llm")
        
    except Exception as e:
        logger.error(f"Erro ao gerar SQL: {e}")
        return pack(fallback_sql(question, dataset), "deterministic_fallback")

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
    
    import re  # Adicionar import aqui para usar em toda a função
    
    q = question.lower()
    
    # ========== MAPEAMENTO DE COLUNAS POR DATASET ==========
    column_mappings = {
        "covid-19-vacinacao": {
            "fabricante": "vacina_nome",
            "vacina": "vacina_nome",
            "marca": "vacina_nome",
            "estado": "paciente_endereco_uf",
            "municipio": "paciente_endereco_nmMunicipio",
            "sexo": "paciente_enumSexoBiologico",
            "idade": "paciente_nrIdade",
            "dose": "vacina_descricao_dose",
            "mes": "vacina_dataAplicacao",
            "mês": "vacina_dataAplicacao",
            "meses": "vacina_dataAplicacao",
            "month": "vacina_dataAplicacao",
            "ano": "vacina_dataAplicacao",
            "anos": "vacina_dataAplicacao",
            "year": "vacina_dataAplicacao",
            "semana": "vacina_dataAplicacao",
            "semanas": "vacina_dataAplicacao",
            "week": "vacina_dataAplicacao",
        },
        "leitos": {
            "estado": "UF",
            "uf": "UF",
            "regiao": "REGIAO",
            "região": "REGIAO",
            "municipio": "MUNICIPIO",
            "município": "MUNICIPIO",
            "cidade": "MUNICIPIO",
            "leito": "LEITOS_EXISTENTES",
            "leitos": "LEITOS_EXISTENTES",
            "sus": "LEITOS_SUS",
            "uti": "UTI_TOTAL_EXIST",
            "gestao": "TP_GESTAO",
            "gestão": "TP_GESTAO",
            "tipo": "DS_TIPO_UNIDADE",
            "estabelecimento": "NOME_ESTABELECIMENTO",
            "hospital": "NOME_ESTABELECIMENTO",
        },
        "surtos-srag": {
            "estado": "SG_UF_NOT",
            "uf": "SG_UF_NOT",
            "sexo": "CS_SEXO",
            "idade": "NU_IDADE_N",
            "idade_n": "NU_IDADE_N",
            "notificacao": "DT_NOTIFIC",
            "notificacoes": "DT_NOTIFIC",
            "data": "DT_NOTIFIC",
            "ano": "DT_NOTIFIC",
            "anos": "DT_NOTIFIC",
            "mes": "DT_NOTIFIC",
            "mês": "DT_NOTIFIC",
            "meses": "DT_NOTIFIC",
            "semana": "DT_NOTIFIC",
            "semanas": "DT_NOTIFIC",
            "sintoma": "DT_SIN_PRI",
            "sintomas": "DT_SIN_PRI",
            "municipio": "CO_MUN_NOT",
            "município": "CO_MUN_NOT",
        },
        "atencao-basica": {
            "estado": "UF",
            "uf": "UF",
            "municipio": "IBGE",
            "município": "IBGE",
            "cidade": "IBGE",
            "bairro": "BAIRRO",
            "nome": "NOME",
            "ubs": "NOME",
            "cnes": "CNES",
            "latitude": "LATITUDE",
            "longitude": "LONGITUDE",
        },
    }
    
    current_mappings = column_mappings.get(dataset, {})
    groupby_columns = {
        "covid-19-vacinacao": "paciente_endereco_uf",
        "dengue-2024": "estado_uf",
        "influenza-2025": "estado_uf",
        "leitos": "UF",
        "surtos-srag": "SG_UF_NOT",
        "atencao-basica": "UF",
    }
    groupby_col = groupby_columns.get(dataset, "estado")

    state_columns = {
        "covid-19-vacinacao": "paciente_endereco_uf",
        "leitos": "UF",
        "surtos-srag": "SG_UF_NOT",
        "atencao-basica": "UF",
    }
    state_col = state_columns.get(dataset, "estado")

    state_code_aliases = {
        "atencao-basica": {
            "AC": "12",
            "AL": "27",
            "AP": "16",
            "AM": "13",
            "BA": "29",
            "CE": "23",
            "DF": "53",
            "ES": "32",
            "GO": "52",
            "MA": "21",
            "MT": "51",
            "MS": "50",
            "MG": "31",
            "PA": "15",
            "PB": "25",
            "PR": "41",
            "PE": "26",
            "PI": "22",
            "RJ": "33",
            "RN": "24",
            "RS": "43",
            "RO": "11",
            "RR": "14",
            "SC": "42",
            "SP": "35",
            "SE": "28",
            "TO": "17",
        }
    }

    # ========== PADRÕES ANALÍTICOS PRIORITÁRIOS ==========
    # Devem preceder MAX/MIN genéricos, pois códigos territoriais são dimensões.
    state_grouping = any(term in q for term in ("por estado", "por uf", "cada estado", "estados"))
    municipality_grouping = any(
        term in q for term in ("município", "municipio", "municípios", "municipios", "cidade", "cidades")
    )
    ranking_request = any(term in q for term in ("maior", "maiores", "mais", "ranking", "top"))

    ratio_request = any(
        term in q
        for term in ("proporção", "proporcao", "percentual", "porcentagem", "em relação")
    )

    if dataset == "leitos" and ratio_request and "leitos sus" in q:
        if any(term in q for term in ("região", "regiao")):
            dimension = "REGIAO"
            alias = "regiao"
        elif state_grouping:
            dimension = "UF"
            alias = "uf"
        else:
            dimension = "REGIAO"
            alias = "regiao"
        return (
            f"SELECT {dimension} AS {alias}, "
            "SUM(LEITOS_SUS) AS leitos_sus, "
            "SUM(LEITOS_EXISTENTES) AS leitos_totais, "
            "ROUND(100.0 * SUM(LEITOS_SUS) / nullIf(SUM(LEITOS_EXISTENTES), 0), 2) AS percentual_sus "
            "FROM leitos WHERE "
            f"{dimension} != '' AND COMP = (SELECT MAX(COMP) FROM leitos) "
            f"GROUP BY {dimension} ORDER BY percentual_sus DESC LIMIT 100"
        )

    if dataset == "covid-19-vacinacao" and state_grouping and ranking_request:
        valid_ufs = (
            "'AC','AL','AP','AM','BA','CE','DF','ES','GO','MA','MT','MS','MG',"
            "'PA','PB','PR','PE','PI','RJ','RN','RS','RO','RR','SC','SP','SE','TO'"
        )
        return (
            "SELECT paciente_endereco_uf AS uf, COUNT(*) AS total_doses "
            "FROM vacinacao "
            f"WHERE paciente_endereco_uf IN ({valid_ufs}) "
            "GROUP BY paciente_endereco_uf ORDER BY total_doses DESC LIMIT 10"
        )

    if dataset == "leitos" and "uti" in q and state_grouping:
        return (
            "SELECT UF AS uf, SUM(UTI_TOTAL_EXIST) AS total_uti_beds "
            "FROM leitos WHERE UF != '' "
            "AND COMP = (SELECT MAX(COMP) FROM leitos) "
            "GROUP BY UF ORDER BY total_uti_beds DESC LIMIT 100"
        )

    if dataset == "leitos" and q.startswith("quais") and "uti" in q and municipality_grouping:
        presence_terms = ("têm", "tem", "possuem", "possui", "com uti")
        if any(term in q for term in presence_terms):
            uti_column = "UTI_TOTAL_EXIST"
            for keyword, column in (
                ("neonatal", "UTI_NEONATAL_EXIST"),
                ("pediátrica", "UTI_PEDIATRICO_EXIST"),
                ("pediatrica", "UTI_PEDIATRICO_EXIST"),
                ("adulto", "UTI_ADULTO_EXIST"),
                ("coronariana", "UTI_CORONARIANA_EXIST"),
                ("queimado", "UTI_QUEIMADO_EXIST"),
            ):
                if keyword in q:
                    uti_column = column
                    break
            return (
                "SELECT DISTINCT MUNICIPIO, UF FROM leitos "
                f"WHERE {uti_column} > 0 "
                "AND COMP = (SELECT MAX(COMP) FROM leitos) "
                "ORDER BY MUNICIPIO LIMIT 5000"
            )

    if dataset == "surtos-srag" and state_grouping:
        return (
            "SELECT SG_UF_NOT AS uf, COUNT(*) AS total_srag FROM srag "
            "WHERE SG_UF_NOT != '' GROUP BY SG_UF_NOT "
            "ORDER BY total_srag DESC LIMIT 100"
        )

    if dataset == "atencao-basica" and municipality_grouping and ranking_request:
        return (
            "SELECT IBGE AS ibge, COUNT(DISTINCT CNES) AS total_ubs "
            "FROM atencao_basica WHERE IBGE > 0 GROUP BY IBGE "
            "ORDER BY total_ubs DESC LIMIT 10"
        )
    
    # ========== DETECTAR SE PERGUNTA BUSCA MENOR ("menor", "mínimo") vs MAIOR ==========
    is_asking_for_min = any(word in q for word in ["menor", "mínimo", "minima", "lowest", "least"])
    is_asking_for_max = any(word in q for word in ["maior", "máximo", "maxima", "highest", "most"])
    
    # Define o ORDER BY apropriado
    order_by_clause = "ORDER BY total" if is_asking_for_min else "ORDER BY total DESC"
    
    # ========== DETECTAR PADRÃO: "de cada X" ou "por cada X" → GROUP BY ==========
    patterns_groupby = [
        ("de cada", True),
        ("por cada", True),
        ("de cada", True),
        ("por ", True),
        ("cada ", True),
    ]
    
    for pattern, is_groupby in patterns_groupby:
        if pattern in q:
            # Tentar extrair coluna após "de cada X" ou "por X"
            # Exemplo: "doses de cada fabricante" → fabricante
            # Procura por "de cada PALAVRA" ou "por PALAVRA"
            regex_patterns = [
                r'de cada (\w+)',
                r'por (\w+)',
                r'cada (\w+)',
                r'por cada (\w+)',
            ]
            
            for regex in regex_patterns:
                match = re.search(regex, q)
                if match:
                    word = match.group(1).lower()
                    # Mapear palavra para coluna conhecida
                    if word in current_mappings:
                        col_name = current_mappings[word]
                        logger.debug(f"Padrão 'de cada/por {word}' detectado → GROUP BY {col_name}")
                        sql = f"SELECT {col_name}, COUNT(*) as total FROM {table_name} GROUP BY {col_name} {order_by_clause} LIMIT 100"
                        return sql
                    # Tentar match próximo
                    for key in current_mappings.keys():
                        if key.startswith(word) or word.startswith(key):
                            col_name = current_mappings[key]
                            logger.debug(f"Padrão 'de cada/por {word}' (partial match {key}) → GROUP BY {col_name}")
                            sql = f"SELECT {col_name}, COUNT(*) as total FROM {table_name} GROUP BY {col_name} {order_by_clause} LIMIT 100"
                            return sql
    
    # ========== DETECTAR PADRÃO: Períodos Temporais (anos, meses, semanas) ==========
    # MUST BE BEFORE STATISTICS to avoid "maior/menor" triggering MAX/MIN
    # Perguntas como: "Qual ano teve mais doses?", "Qual mês teve mais casos?", "em quais meses?"
    if any(word in q for word in ["ano", "anos", "mês", "meses", "mês", "mes", "semana", "semanas", "trimestre", "trimestres"]):
        # Detectar qual período extrair (ano, mês, semana, etc)
        period_functions = {
            "ano": ("year", "ano"),
            "anos": ("year", "ano"),
            "mês": ("month", "mes"),
            "mes": ("month", "mes"),
            "month": ("month", "mes"),
            "semana": ("week", "semana"),
            "semanas": ("week", "semana"),
            "trimestre": ("quarter", "trimestre"),
            "trimestres": ("quarter", "trimestre"),
        }
        
        # Encontrar qual período está na pergunta
        for period_word, (func_name, alias) in period_functions.items():
            if period_word in q:
                # Encontrar coluna de data apropriada para o dataset
                date_columns = {
                    "covid-19-vacinacao": "vacina_dataAplicacao",
                    "leitos": "COMP",
                    "surtos-srag": "DT_NOTIFIC",
                }
                date_col = date_columns.get(dataset)

                if not date_col:
                    continue
                
                logger.debug(f"Padrão detectado: Período '{period_word}' de {date_col} → {func_name}()")
                sql = f"SELECT {func_name}({date_col}) as {alias}, COUNT(*) as total FROM {table_name} GROUP BY {alias} {order_by_clause} LIMIT 100"
                return sql
    
    # ========== DETECTAR PADRÃO: Estatísticas de coluna ==========
    # Perguntas como: "Qual é a idade média?", "Qual é a idade mínima?", etc
    stats_patterns = {
        "média": ("AVG", ["média", "media", "average", "médio"]),
        "mínima": ("MIN", ["mínima", "minima", "mínimo", "minimo", "menor"]),
        "máxima": ("MAX", ["máxima", "maxima", "máximo", "maximo", "maior"]),
        "mediana": ("MEDIAN", ["mediana", "median"]),
        "desvio": ("STDDEV", ["desvio", "desvio padrão", "desvpack", "variância"]),
    }
    
    for stat_type, (sql_func, keywords) in stats_patterns.items():
        if any(kw in q for kw in keywords):
            # Procurar qual coluna (idade, altura, etc)
            for key in current_mappings.keys():
                if key in q:
                    col_name = current_mappings[key]
                    logger.debug(f"Padrão detectado: '{stat_type}' de {key} → {sql_func}({col_name})")
                    sql = f"SELECT {sql_func}({col_name}) as resultado FROM {table_name}"
                    return sql
            # Se não achou coluna específica, tentar idade como default
            default_stat_columns = {
                "covid-19-vacinacao": "paciente_idade",
                "surtos-srag": "NU_IDADE_N",
            }
            default_stat_col = default_stat_columns.get(dataset)
            if default_stat_col:
                logger.debug(f"Padrão detectado: '{stat_type}' com default {default_stat_col}")
                sql = f"SELECT {sql_func}({default_stat_col}) as resultado FROM {table_name}"
                return sql
    
    # ========== DETECTAR PADRÃO: "Quais ... têm" → Listar registros com filtro ==========
    # Exemplo: "Quais cidades têm UTI neonatal?"
    if q.startswith("quais") and any(word in q for word in ["têm ", "tem ", "têm", "tem"]):
        logger.debug("Padrão detectado: 'Quais ... têm' → SELECT com WHERE")
        
        # Detectar se é negação ("não têm", "nao tem")
        has_negation = any(word in q for word in ["não ", "nao ", "sem ", "nenhum"])
        
        # Para leitos: se menciona UTI específica, filtrar por >0 ou =0
        if dataset == "leitos":
            uti_keywords = {
                "neonatal": "UTI_NEONATAL_EXIST",
                "adulto": "UTI_ADULTO_EXIST",
                "pediátrica": "UTI_PEDIATRICO_EXIST",
                "pediatrica": "UTI_PEDIATRICO_EXIST",
                "queimado": "UTI_QUEIMADO_EXIST",
                "queimados": "UTI_QUEIMADO_EXIST",
                "coronariana": "UTI_CORONARIANA_EXIST",
                "uti": "UTI_TOTAL_EXIST",
            }
            
            for uti_type, uti_col in uti_keywords.items():
                if uti_type in q:
                    # Decidir condição baseado em negação
                    condition = "= 0" if has_negation else "> 0"
                    
                    # Detectar coluna de retorno (cidades/municípios, estados, etc)
                    if any(word in q for word in ["cidade", "cidades", "municipio", "municípios"]):
                        select_col = "DISTINCT MUNICIPIO, UF"
                        order_col = "MUNICIPIO"
                    elif any(word in q for word in ["estado", "estados", "uf"]):
                        select_col = "DISTINCT UF"
                        order_col = "UF"
                    else:
                        select_col = "DISTINCT MUNICIPIO, UF"
                        order_col = "MUNICIPIO"
                    
                    sql = (
                        f"SELECT {select_col} FROM {table_name} "
                        f"WHERE {uti_col} {condition} "
                        f"AND COMP = (SELECT MAX(COMP) FROM {table_name}) "
                        f"ORDER BY {order_col} LIMIT 5000"
                    )
                    logger.debug(f"Padrão 'Quais ... {'não ' if has_negation else ''}têm {uti_type}' → {sql[:60]}")
                    return sql
    
    # ========== DETECTAR PADRÃO: "Qual ... teve MAIS" → GROUP BY DESC ==========
    if any(word in q for word in ["qual", "que"]) and any(word in q for word in ["mais", "maior", "maiores"]):
        # Pergunta de comparação: "Qual estado teve mais casos?"
        logger.debug("Padrão detectado: 'Qual ... teve MAIS' → GROUP BY")
        sql = f"SELECT {groupby_col}, COUNT(*) as total FROM {table_name} GROUP BY {groupby_col} {order_by_clause} LIMIT 100"
    
    # ========== DETECTAR PADRÃO: "Quantas em estado específico" → WHERE ==========
    elif any(word in q for word in ["quantas", "quantos", "quanto"]) and any(word in q for word in ["em ", "em sp", "em rj", "no ", "na "]):
        # Pergunta com filtro: "Quantas vacinas em SP?"
        logger.debug("Padrão detectado: 'Quantas em [estado]' → WHERE")
        
        # Extrair o código de estado (ex: "SP" de "em SP")
        regex_patterns = [
            r'em\s+([a-z]{2})',      # "em SP", "em RJ"
            r'no\s+([a-z]{2})',      # "no SP", "no RJ"
            r'na\s+([a-z]{2})',      # "na SP", "na RJ"
            r'estado\s+[a-z]*\s+([a-z]{2})',  # "estado de SP", "estado SP"
        ]
        
        estado_code = None
        for regex in regex_patterns:
            match = re.search(regex, q, re.IGNORECASE)
            if match:
                estado_code = match.group(1).upper()
                break
        
        # Se encontrou estado, adicionar WHERE; senão usar COUNT simples
        valid_state_codes = {
            "AC", "AL", "AP", "AM", "BA", "CE", "DF", "ES", "GO", "MA", "MT", "MS",
            "MG", "PA", "PB", "PR", "PE", "PI", "RJ", "RN", "RS", "RO", "RR", "SC",
            "SP", "SE", "TO",
        }
        if estado_code not in valid_state_codes:
            estado_code = None

        if estado_code:
            mapped_state_code = state_code_aliases.get(dataset, {}).get(estado_code, estado_code)
            sql = f"SELECT COUNT(*) AS total_registros FROM {table_name} WHERE {state_col} = '{mapped_state_code}'"
            logger.debug(f"Estado '{estado_code}' extraído → WHERE {state_col} = '{mapped_state_code}'")
        else:
            sql = f"SELECT COUNT(*) AS total_registros FROM {table_name}"
            logger.debug("Nenhum estado extraído, usando COUNT simples")
    
    # ========== DETECTAR PADRÃO: "Quantas total/geral" → COUNT simples ==========
    elif any(word in q for word in ["quantas", "quantos", "quanto", "total", "geral", "contar", "casos"]):
        logger.debug("Padrão detectado: 'Quantas total' → COUNT(*)")
        sql = f"SELECT COUNT(*) AS total_registros FROM {table_name}"
    
    # ========== DETECTAR PADRÃO: "Por estado/região" → GROUP BY ==========
    elif any(word in q for word in ["por estado", "por uf", "cada estado", "por região", "região"]):
        logger.debug("Padrão detectado: 'Por estado' → GROUP BY")
        sql = f"SELECT {groupby_col}, COUNT(*) as total FROM {table_name} GROUP BY {groupby_col} {order_by_clause} LIMIT 100"
    
    # ========== DEFAULT: COUNT simples ==========
    else:
        logger.debug("Nenhum padrão detectado, usando COUNT simples")
        sql = f"SELECT COUNT(*) AS total_registros FROM {table_name}"
    
    logger.info(f"Fallback SQL para {dataset}: {sql}")
    return sql
