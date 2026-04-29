import json
import logging
import re
from datetime import datetime, date
from metadata.loader import load_metadata
from llm.router import get_llm
from config.datasets import get_dataset_config

logger = logging.getLogger(__name__)


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


def interpret_result(question: str, result, model_name: str = "deepseek-local", dataset: str = "covid-19-vacinacao") -> str:
    """
    Interpreta resultado usando LLM com abordagem simplista e flexível.
    
    Não tenta detectar tipo de resultado - apenas passa pergunta + dados + contexto
    para o LLM interpretar naturalmente.
    
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
        
        # Obter contexto do dataset
        dataset_context = _get_dataset_context(dataset)
        
        # Formatar resultado para apresentar ao LLM
        formatted_result = _format_result_for_llm(result, max_rows=100)
        
        # Gerar prompt simples que deixa LLM interpretar
        prompt = _build_interpretation_prompt(
            question=question,
            result_data=formatted_result,
            result_count=len(result),
            dataset_context=dataset_context
        )
        
        logger.debug(f"Enviando para LLM {model_name} com {len(result)} linhas de resultado")
        
        # Obter resposta do LLM
        response = llm.generate(prompt)
        
        if not response or not response.strip():
            logger.warning("Resposta vazia do LLM, usando fallback")
            return _fallback_interpretation(result, question)
        
        interpretation = response.strip()
        logger.info(f"Interpretação gerada com sucesso: {len(interpretation)} caracteres")
        
        return interpretation
    
    except Exception as e:
        error_str = str(e)
        logger.error(f"Erro ao interpretar resultado: {e}")
        
        # Retornar fallback quando LLM falha
        return _fallback_interpretation(result, question)


def _build_interpretation_prompt(question: str, result_data: str, result_count: int, dataset_context: str) -> str:
    """
    Constrói prompt simples e flexível para o LLM interpretar resultado.
    Zero hardcoding - deixa o LLM decidir como interpretar.
    
    Args:
        question: Pergunta do usuário
        result_data: Dados formatados para exibição
        result_count: Total de linhas no resultado
        dataset_context: Contexto sobre o dataset
    
    Returns:
        Prompt estruturado para o LLM
    """
    
    return f"""Você é um assistente de análise de dados de saúde pública no Brasil.
Sua tarefa é interpretar e explicar resultados de consultas de forma clara e prática para gestor.

{dataset_context}

PERGUNTA DO GESTOR:
{question}

RESULTADO DA CONSULTA ({result_count} linha(s)):
{result_data}

INSTRUÇÕES OBRIGATÓRIAS:
1. Responda em português claro e acessível
2. Use os números EXATOS do resultado (não arredonde arbitrariamente)
3. Traduza códigos (F→Feminino, M→Masculino, etc) quando apropriado
4. Se há múltiplas linhas, interprete a distribuição/ranking/tendência
5. Se há um número único, use como resposta principal
6. PROIBIDO: inventar dados, datas, contextos não fornecidos, efeitos adversos
7. PROIBIDO: fazer comparações com períodos que não estão nos dados
8. Se a pergunta pede maior/menor/ranking, identifique claramente quem está em primeiro
9. Máximo 3-4 frases, seja conciso

CONTEXTO ADICIONAL:
- Se há muitas linhas (>10), destaque os principais padrões
- Se há proporções (razões, percentuais), calcule e mencione
- Se há séries temporais, descreva a tendência (crescimento, queda, estável)
- Se há categorizações (sexo, tipo, estado), mencione a distribuição

Responda apenas com a interpretação, sem formatação especial, sem JSON, sem explicações:"""


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