import json
import logging
import os
import re
from datetime import datetime, date
from metadata.loader import load_metadata
from llm.router import get_llm
from config.datasets import get_dataset_config

logger = logging.getLogger(__name__)


# ============================================================================
# DETECÇÃO DE TIPO DE RESULTADO BASEADA NA PERGUNTA (NÃO NO RESULTADO)
# ============================================================================

def _detect_result_type_from_question(question: str) -> str:
    """
    Detecta o tipo de resultado esperado baseado em keywords na PERGUNTA.
    Isso é muito mais confiável que tentar detectar pelo resultado em si.
    
    Tipos retornados:
    - "simple": Pergunta por um número único (COUNT, SUM, AVG)
    - "distribution": Pergunta por distribuição/proporção entre categorias
    - "ranking": Pergunta por qual X é maior/menor, ranking de
    - "temporal": Pergunta por evolução/tendência ao longo do tempo
    - "ratio": Pergunta por proporção/razão entre duas métricas
    - "multi_dimension": Pergunta cruzada (múltiplas dimensões)
    - "unknown": Não conseguiu detectar padrão claro
    
    Args:
        question: Pergunta original do usuário em português
    
    Returns:
        String com tipo detectado
    """
    q_lower = question.lower()
    
    # Padrão 1: PROPORÇÃO / RAZÃO
    if any(pattern in q_lower for pattern in [
        'proporção', 'razao', 'razão', 'por cento', 'percentual', 'percentagem',
        '/', 'em relacao', 'relação', 'comparado com', 'versus', 'vs'
    ]):
        return "ratio"
    
    # Padrão 2: DISTRIBUIÇÃO
    if any(pattern in q_lower for pattern in [
        'distribuição', 'distribuicao', 'como foi', 'qual é a distribuição',
        'de cada', 'entre', 'por sexo', 'por estado', 'por tipo', 'por faixa',
        'entre diferentes'
    ]):
        return "distribution"
    
    # Padrão 3: RANKING / COMPARAÇÃO
    if any(pattern in q_lower for pattern in [
        'qual estado', 'qual município', 'qual tipo', 'qual fabricante',
        'qual estabelecimento', 'ranking', 'maior número', 'menor número',
        'maior capacidade', 'qual teve mais', 'qual teve menos',
        'qual possui', 'que mais', 'que menos', 'líder', 'top'
    ]):
        return "ranking"
    
    # Padrão 4: TEMPORAL / SÉRIE DE TEMPO
    if any(pattern in q_lower for pattern in [
        'evolução', 'ao longo', 'ao longo do', 'tendência', 'ao decorrer',
        'mensal', 'anual', 'por mês', 'por ano', 'por período',
        'qual mês', 'qual ano', 'qual trimestre', 'qual semana',
        'ao longo', 'série', 'história', 'histórico'
    ]):
        return "temporal"
    
    # Padrão 5: MULTI-DIMENSÃO (análise cruzada)
    if any(pattern in q_lower for pattern in [
        'em cada estado', 'de cada estado', 'por estado e', 'em cada',
        'de cada', 'cruzada', 'entre diferentes dimensões',
        'em hospitais gerais públicos'
    ]):
        return "multi_dimension"
    
    # Padrão 6: SIMPLES (quantidade total, SUM, AVG)
    if any(pattern in q_lower for pattern in [
        'quantas', 'quantos', 'qual é o total', 'qual é a quantidade',
        'qual é a capacidade', 'qual é a média', 'total de', 'soma de',
        'no total', 'em total'
    ]):
        # Se não matchou distribuição ou ranking, é simples
        return "simple"
    
    return "unknown"


def _get_type_specific_context(result_type: str, question: str, result: list) -> str:
    """
    Retorna instrução específica por tipo de resultado.
    
    Args:
        result_type: Tipo detectado
        question: Pergunta original
        result: Resultado do SQL
    
    Returns:
        String com instruções para o LLM
    """
    
    result_count = len(result) if isinstance(result, list) else 0
    
    # Detectar se há número único
    is_single_number = (
        result_count == 1 and 
        isinstance(result[0], (list, tuple)) and 
        len(result[0]) == 1
    )
    
    if result_type == "simple":
        if is_single_number:
            number = result[0][0]
            return f"""TIPO DE RESULTADO: Número Único
O resultado é um valor ÚNICO que responde diretamente à pergunta.
Você recebeu: {number}

INSTRUÇÕES:
1. Responda de forma direta e simples, usando EXATAMENTE o número {number}
2. Formule em linguagem natural uma frase que responda à pergunta
3. PROIBIDO gerar SQL, código ou contextos fictícios
4. Exemplos corretos:
   - Pergunta: "Quantas doses foram aplicadas?"
   - Resposta: "Foram aplicadas 390.911 doses de vacina COVID-19 no Brasil."
5. Uma frase. Ponto final. Fim."""
        else:
            return """TIPO DE RESULTADO: Valor Agregado
O resultado é um cálculo único (soma, média, contagem) que responde à pergunta.
Use o valor recebido como resposta principal, sem adicionar contextos fictícios."""
    
    elif result_type == "distribution":
        return f"""TIPO DE RESULTADO: Distribuição
O resultado mostra como algo se distribui entre {result_count} categorias.

INSTRUÇÕES:
1. Mencione TODAS as categorias e seus valores
2. Se há proporções, calcule/mencione os percentuais
3. Identifique qual é a maior e qual é a menor
4. Descrição clara e objetiva
5. Exemplo: "A distribuição foi Feminino 210.133 (53,8%) e Masculino 180.115 (46,2%)"
6. Máximo 2-3 frases."""
    
    elif result_type == "ranking":
        first_place = result[0][0] if result and len(result[0]) > 0 else "???"
        return f"""TIPO DE RESULTADO: Ranking
O resultado é um ranking ordenado de entidades.
Primeiro lugar: {first_place}

INSTRUÇÕES:
1. Identifique e destaque quem está em PRIMEIRO lugar
2. Mencione o valor/número associado
3. Opcionalmente mencione o segundo lugar para contexto
4. Use frases como "lidera com", "em primeiro lugar", "maior de"
5. Exemplo: "São Paulo lidera com 156.000 doses, seguido por Minas Gerais com 89.000"
6. Máximo 2 frases."""
    
    elif result_type == "temporal":
        return f"""TIPO DE RESULTADO: Série Temporal
O resultado mostra evolução ao longo do tempo com {result_count} períodos.

INSTRUÇÕES:
1. Identifique o PICO (maior valor) e quando ocorreu
2. Descreva a TENDÊNCIA (crescimento, queda, estável)
3. Mencione o período com menor atividade se relevante
4. Exemplo: "Vacinações aumentaram de janeiro a junho de 2021, com pico em junho com 52.400 doses"
5. Máximo 2-3 frases."""
    
    elif result_type == "ratio":
        return f"""TIPO DE RESULTADO: Proporção/Razão
O resultado é uma razão ou proporção entre duas métricas.

INSTRUÇÕES:
1. Apresente a proporção de forma clara (X% ou Y:Z ou "X de cada Z")
2. Se há valores absolutos, mencione-os também
3. Contextualizar o que significado (maior/menor cobertura, maior/menor acesso)
4. Exemplo: "65% dos leitos (156.000 de 240.000) estão sob gestão SUS"
5. Máximo 2 frases."""
    
    elif result_type == "multi_dimension":
        return f"""TIPO DE RESULTADO: Análise Multi-dimensão
O resultado cruza múltiplas dimensões ({result_count} linhas com múltiplas colunas).

INSTRUÇÕES:
1. Identifique qual combinação tem o maior valor
2. Descreva o padrão geral (qual estado lidera, qual tipo é mais comum, etc)
3. Mencione disparidades importantes se existirem
4. Exemplo: "SP lidera com 156.000 doses em Hospitais Gerais, seguido por MG com 89.000 em Postos"
5. Máximo 3 frases."""
    
    else:  # "unknown"
        return """TIPO DE RESULTADO: Desconhecido
Não consegui identificar o padrão, então use sua melhor interpretação do resultado."""


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder customizado para lidar com objetos de data e hora"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def _get_dataset_context(dataset: str) -> str:
    """
    Retorna contexto semântico sobre o dataset.
    
    Args:
        dataset: Nome do dataset (ex: "covid-19-vacinacao", "leitos")
    
    Returns:
        String descrevendo o dataset e seus campos principais
    """
    try:
        if "," in dataset:
            datasets = [item.strip() for item in dataset.split(",") if item.strip()]
            contexts = []
            for dataset_id in datasets:
                contexts.append(_get_dataset_context(dataset_id))
            return "\n\n".join(contexts)

        config = get_dataset_config(dataset)
        description = config.get("description", "")
        
        # Carregar metadata para mais contexto
        try:
            metadata = load_metadata(dataset)
            if metadata and "descricao" in metadata:
                description = metadata["descricao"]
        except:
            pass
        
        # Contexto específico por dataset
        if "covid" in dataset.lower() or "vacinacao" in dataset.lower():
            return f"""CONTEXTO DO DATASET: {description}

IMPORTANTE:
- Os resultados se referem a DOSES DE VACINA aplicadas (não pessoas)
- Colunas importantes: paciente_endereco_uf (estado), paciente_enumSexoBiologico (F/M), 
  vacina_dataAplicacao (data), vacina_nome (marca), vacina_descricao_dose (1ª, 2ª, reforço)
- Use "Feminino" e "Masculino" ao invés de F/M
- Datas podem estar em formato YYYY-MM-DD"""
        
        elif "leito" in dataset.lower():
            return f"""CONTEXTO DO DATASET: {description}

IMPORTANTE:
- Os resultados se referem a LEITOS HOSPITALARES (camas)
- Colunas importantes: LEITOS_EXISTENTES (total de leitos), LEITOS_SUS (leitos públicos),
  UTI_TOTAL_EXIST, UTI_ADULTO_EXIST, UTI_PEDIATRICO_EXIST, UTI_NEONATAL_EXIST, etc
- Diferencie entre TOTAL e SUS (público)
- Dados de capacidade hospitalar/infraestrutura, não de pacientes"""
        
        else:
            return f"CONTEXTO: {description}"
    
    except Exception as e:
        logger.warning(f"Erro ao obter contexto do dataset {dataset}: {e}")
        return "Contexto não disponível"


def _format_result_for_llm(result: list, max_rows: int = 50) -> str:
    """
    Formata resultado para apresentação ao LLM.
    
    Args:
        result: Lista de tuplas/listas do banco de dados
        max_rows: Máximo de linhas a mostrar
    
    Returns:
        String formatada do resultado
    """
    if not result:
        return "[]"
    
    # Se há muitos resultados, mostrar amostra
    if len(result) > max_rows:
        display_result = result[:max_rows]
        more_msg = f"\n... ({len(result) - max_rows} mais linhas)"
    else:
        display_result = result
        more_msg = ""
    
    try:
        formatted = json.dumps(
            display_result, 
            ensure_ascii=False, 
            default=str,
            indent=2
        )
    except Exception as e:
        logger.warning(f"Erro ao serializar resultado: {e}. Usando versão simplificada")
        formatted = str(display_result[:max_rows])
    
    return formatted + more_msg


def interpret_result(
    question: str,
    result,
    model_name: str = "deepseek-local",
    dataset: str = "covid-19-vacinacao",
    factual_summary: str = "",
) -> str:
    """
    Interpreta resultado usando LLM com abordagem TIPO-ESPECÍFICA.
    
    Detecta o tipo de pergunta (simples, distribuição, ranking, temporal, etc)
    e passa instruções específicas ao LLM para evitar alucinação.
    
    Args:
        question: Pergunta original do usuário
        result: Lista de resultados do SQL (pode ser vazia, um número, ranking, múltiplas colunas, etc)
        model_name: Qual LLM usar
        dataset: Qual dataset (para contexto)
    
    Returns:
        String com interpretação em linguagem natural
    """
    
    logger.info(f"Interpretando resultado para: {question[:80]}...")
    
    # Bloqueio crítico: checar se é erro
    if isinstance(result, dict) and "error" in result:
        error_msg = result.get("message", result["error"])
        logger.error(f"Resultado é erro: {error_msg}")
        return f"Desculpe, ocorreu um erro ao executar a consulta: {error_msg}"
    
    # Checar se está vazio
    if not result or (isinstance(result, list) and len(result) == 0):
        logger.warning("Resultado da query vazio")
        return "Não encontrei registros que correspondam à sua pergunta. Tente reformular a pergunta ou verifique os filtros."
    
    try:
        llm = get_llm(model_name)
        
        # NOVO: Detectar tipo baseado na pergunta (não no resultado!)
        result_type = _detect_result_type_from_question(question)
        logger.debug(f"Tipo de resultado detectado: {result_type}")
        
        # Obter contexto do dataset
        dataset_context = _get_dataset_context(dataset)
        
        # Formatar resultado para apresentar ao LLM
        formatted_result = _format_result_for_llm(result, max_rows=100)
        
        # NOVO: Passar tipo e resultado para _build_interpretation_prompt
        prompt = _build_interpretation_prompt(
            question=question,
            result_data=formatted_result,
            result_count=len(result),
            dataset_context=dataset_context,
            result_type=result_type,
            result=result
        )
        if factual_summary:
            prompt += (
                "\n\nRESUMO FATUAL CALCULADO DIRETAMENTE DOS DADOS:\n"
                f"{factual_summary}\n"
                "A resposta não pode contradizer esse resumo nem atribuir a uma categoria o máximo de outra métrica."
            )
        
        logger.debug(f"Enviando para LLM {model_name} com {len(result)} linhas de resultado (tipo: {result_type})")
        
        # Obter resposta do LLM
        response = llm.generate(
            prompt,
            num_predict=int(os.getenv("OLLAMA_INTERPRETATION_NUM_PREDICT", "256")),
            temperature=0.0,
            timeout_s=int(os.getenv("OLLAMA_INTERPRETATION_TIMEOUT", "60")),
            max_retries=1,
        )
        
        if not response or not response.strip():
            logger.warning("Resposta vazia do LLM, usando fallback")
            return _fallback_interpretation(result, question)
        
        interpretation = response.strip()
        logger.info(f"Interpretação gerada com sucesso: {len(interpretation)} caracteres (tipo: {result_type})")
        
        return interpretation
    
    except Exception as e:
        error_str = str(e)
        logger.error(f"Erro ao interpretar resultado: {e}")
        
        # Retornar fallback quando LLM falha
        return _fallback_interpretation(result, question)


def _build_interpretation_prompt(question: str, result_data: str, result_count: int, dataset_context: str, result_type: str = "unknown", result: list = None) -> str:
    """
    Constrói prompt MUITO SIMPLES e direto para o LLM interpretar resultado.
    
    DeepSeek Coder funciona melhor com prompts curtos e diretos, sem muita formatação.
    
    Args:
        question: Pergunta do usuário
        result_data: Dados formatados para exibição
        result_count: Total de linhas no resultado
        dataset_context: Contexto sobre o dataset
        result_type: Tipo detectado pela pergunta
        result: Resultado bruto (para casos especiais)
    
    Returns:
        Prompt estruturado mas simples
    """
    
    # Detectar se é um número único
    is_single_number = (
        result_count == 1 and 
        result and isinstance(result[0], (list, tuple)) and 
        len(result[0]) == 1
    )
    
    # ESTRATÉGIA: Prompts separados e MUITO simples por tipo
    
    if is_single_number and result_type == "simple":
        # Para números únicos: prompt EXTREMAMENTE simples
        number = result[0][0]
        return f"""Pergunta: {question}

Resultado do banco de dados: {number}

Interprete esse resultado em UMA frase em português natural, respondendo diretamente à pergunta.
Regras:
- Use exatamente o número {number}
- Não invente contextos
- Sem SQL ou código
- Simples e direto

Resposta:"""
    
    elif result_type == "ranking" and result_count > 0:
        # Para rankings: destaque o primeiro lugar
        first_item = result[0]
        first_name = str(first_item[0]) if isinstance(first_item, (list, tuple)) and len(first_item) > 0 else "???"
        first_value = str(first_item[1]) if isinstance(first_item, (list, tuple)) and len(first_item) > 1 else "???"
        
        return f"""Pergunta: {question}

Resultado (ranking de {result_count} itens):
{result_data}

Interprete em UMA FRASE em português natural.
Regras:
- Destaque quem está em PRIMEIRO lugar: {first_name} com valor {first_value}
- Use frases como "lidera com" ou "em primeiro lugar"
- Máximo 2 frases

Resposta:"""
    
    elif result_type == "distribution" and result_count > 0:
        # Para distribuições: todas as categorias
        return f"""Pergunta: {question}

Resultado (distribuição de {result_count} categorias):
{result_data}

Interprete em PORTUGUÊS NATURAL respondendo como estão distribuídos os dados.
Regras:
- Mencione todas as categorias
- Se há percentuais, calcule e mencione
- Máximo 3 frases
- Claro e simples

Resposta:"""
    
    elif result_type == "temporal" and result_count > 0:
        # Para séries temporais: tendência
        return f"""Pergunta: {question}

Resultado (série temporal de {result_count} períodos):
{result_data}

Descreva a TENDÊNCIA e o PICO em UMA FRASE.
Regras:
- Identifique o pico (maior valor)
- Descreva a tendência (crescimento/queda/estável)
- Máximo 2 frases

Resposta:"""
    
    elif result_type == "ratio" and result_count > 0:
        # Para proporções
        return f"""Pergunta: {question}

Resultado (proporção/razão):
{result_data}

Interprete essa proporção em linguagem natural.
Máximo 2 frases. Claro e direto.

Resposta:"""
    
    elif result_type == "multi_dimension" and result_count > 0:
        # Para análises cruzadas
        return f"""Pergunta: {question}

Resultado (análise multi-dimensão, {result_count} linhas):
{result_data}

Resuma o padrão principal observado.
Máximo 3 frases. Destaque o que é mais importante.

Resposta:"""
    
    else:
        # Fallback genérico para "unknown" ou outros
        return f"""Pergunta: {question}

Resultado do banco de dados ({result_count} registros):
{result_data}

Interprete esse resultado em linguagem natural clara e simples.
Responda como um especialista em saúde pública explicando para um gestor.
Máximo 3 frases.

Resposta:"""


def _fallback_interpretation(result, question: str) -> str:
    """
    Gera interpretação simples quando LLM falha.
    
    Args:
        result: Resultado do SQL
        question: Pergunta original
    
    Returns:
        Interpretação em texto simples
    """
    
    try:
        # Se é um número único
        if isinstance(result, list) and len(result) == 1 and len(result[0]) == 1:
            num = result[0][0]
            return f"O resultado da consulta é: {num:,}" if isinstance(num, (int, float)) else f"O resultado é: {num}"
        
        # Se é ranking/distribuição
        if isinstance(result, list) and len(result) > 0 and len(result[0]) == 2:
            first_item = result[0]
            label = str(first_item[0])
            value = first_item[1]
            
            if len(result) == 1:
                return f"Resultado encontrado: {label} com {value:,}."
            else:
                return f"Resultado: {label} lidera com {value:,}, seguido por {len(result)-1} outras categorias."
        
        # Fallback genérico
        return f"Consulta retornou {len(result)} registros. Primeiros dados: {result[0] if result else 'vazio'}"
    
    except Exception as e:
        logger.error(f"Erro no fallback: {e}")
        return f"Consulta executada com sucesso ({len(result)} registros). Verifique os dados no detalhe."
