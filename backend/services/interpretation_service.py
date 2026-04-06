import json
import logging
from metadata.loader import load_metadata
from llm.router import get_llm

logger = logging.getLogger(__name__)


def _detect_result_type(result):
    """
    Detecta o tipo de resultado da query.
    
    Returns:
        "simple": Um valor numérico simples (COUNT)
        "ranking": Múltiplas linhas com nome+valor (GROUP BY)
        "multiple": Múltiplas colunas de dados
    """
    if not isinstance(result, list) or len(result) == 0:
        return "empty"
    
    first_row = result[0]
    
    # Um valor: COUNT(*)
    if len(result) == 1 and len(first_row) == 1:
        return "simple"
    
    # Múltiplas linhas de duas colunas: [["AC", 376290], ["RO", 4272], ...]
    if len(first_row) == 2 and isinstance(first_row[0], str):
        return "ranking"
    
    # Múltiplos anos/datas com valores
    if len(result) > 1 and len(first_row) == 2:
        return "ranking"
    
    # Múltiplas colunas
    return "multiple"


def _format_prompt_for_type(question, result, result_type):
    """
    Gera prompt específico para cada tipo de resultado.
    """
    
    if result_type == "simple":
        # Um número simples
        value = result[0][0]
        return f"""Você é um assistente de dados em saúde pública.

PERGUNTA: {question}

RESULTADO EXATO: {value}

REGRA OBRIGATÓRIA:
- Responda com UMA frase simples em português
- Use EXATAMENTE o número {value} na resposta
- Não invente números ou contextos
- Seja factual e breve

EXEMPLOS DE RESPOSTAS CORRETAS:
- Se pergunta: "Quantas doses?" e resultado: 1000
  Resposta: "Foram aplicadas 1000 doses de vacina."

- Se pergunta: "Quantos casos?" e resultado: 500  
  Resposta: "Foram registrados 500 casos de dengue."

RESPOSTA (uma frase com o número {value}):"""
    
    elif result_type == "ranking":
        # Ranking: [["AC", 376290], ["RO", 4272], ...]
        # Extrair top 3
        top_3 = result[:3]
        formatted = "\n".join([f"{rank+1}º - {row[0]}: {row[1]}" for rank, row in enumerate(top_3)])
        
        total_rows = len(result)
        first_place = result[0][0]
        first_value = result[0][1]
        
        return f"""Você é um assistente de dados em saúde pública.

PERGUNTA: {question}

RESULTADO (ranking de {total_rows} registros):
{formatted}

REGRA OBRIGATÓRIA:
- Responda com UMA frase simples em português
- Mencione o PRIMEIRO LUGAR e seu número: "{first_place}" com "{first_value}"
- Não invente contextos ou datas
- Seja factual e breve

EXEMPLOS DE RESPOSTAS CORRETAS:
- Se resultado: ["AC": 100, "RJ": 50]
  Resposta: "O estado com mais registros foi AC, com 100 casos."

- Se resultado: ["SP": 500, "MG": 400]
  Resposta: "São Paulo teve o maior número com 500 do total."

RESPOSTA (uma frase mencionando {first_place} e {first_value}):"""
    
    elif result_type == "multiple":
        # Múltiplos dados
        formatted_result = json.dumps(result[:5], ensure_ascii=False, indent=2)
        return f"""Você é um assistente de dados em saúde pública.

PERGUNTA: {question}

RESULTADO (primeiros 5 registros):
{formatted_result}

REGRA OBRIGATÓRIA:
- Responda com UMA frase simples em português
- Use apenas os dados fornecidos
- Não invente contextos ou datas
- Seja factual e breve

RESPOSTA (uma frase interpretando o resultado):"""
    
    else:
        # Fallback
        return f"""Responda em UMA frase simples em português.

PERGUNTA: {question}

RESPOSTA (uma frase interpretando o resultado):"""


def interpret_result(question, result, model_name):
    """Interpreta resultado da query usando LLM"""
    
    logger.info(f"Interpretando resultado para: {question}")
    
    # Bloqueio crítico: checar se é erro
    if isinstance(result, dict) and "error" in result:
        error_msg = result.get("message", result["error"])
        logger.error(f"Resultado é erro: {error_msg}")
        return f"Desculpe, ocorreu um erro ao executar a consulta: {error_msg}"
    
    # Checar se está vazio
    if not result or (isinstance(result, list) and len(result) == 0):
        logger.warning("Resultado da query vazio")
        return "Não encontrei registros que correspondam à sua pergunta."
    
    try:
        llm = get_llm(model_name)
        metadata = load_metadata()
        
        # Detectar tipo de resultado
        result_type = _detect_result_type(result)
        logger.debug(f"Tipo de resultado detectado: {result_type}")
        
        # Gerar prompt apropriado
        prompt = _format_prompt_for_type(question, result, result_type)

        logger.debug(f"Enviando prompt para LLM...")
        logger.debug(f"Prompt: {prompt[:200]}...")
        insight = llm.generate(prompt)
        logger.debug(f"Resposta bruta do LLM: repr={repr(insight)} len={len(insight) if insight else 0}")
        
        # Sanitizar resposta - remover artefatos do modelo
        insight = insight.strip() if insight else ""
        
        # Remover blocos jupyter
        if '<jupyter' in insight:
            insight = insight.split('<jupyter')[0]
        if '<gpt' in insight.lower():
            insight = insight.lower().split('<gpt')[0] if '<gpt' in insight.lower() else insight
        
        # Remover code blocks
        insight = insight.replace('```python', '').replace("```", '')
        insight = insight.replace('"""', '').replace("'''", '')
        insight = insight.replace('`', '').strip()
        
        # Remover padrões indesejados (USER INPUT, GPT Response, etc)
        lines = insight.split('\n')
        cleaned_lines = []
        for line in lines:
            upper_line = line.upper()
            # Skip linhas com padrões indesejados
            if any(pattern in upper_line for pattern in [
                'USER INPUT', 'GPT', 'RESPONSE IN', 'JUPYTER',
                'QUESTION:', 'ANSWER:', 'ASSISTANT:', 'PLEASE PROVIDE',
                'I AM A VIRTUAL', 'I AM SORRY'
            ]):
                continue
            if line.strip():
                cleaned_lines.append(line.strip())
        
        insight = '\n'.join(cleaned_lines)
        insight = insight.strip('"').strip("'").strip()
        
        # Validar resultado
        if not insight or insight in ["", "None", "null", "...", "Resultado:", "Resposta:"]:
            logger.warning(f"LLM retornou inútil, usando fallback para tipo: {result_type}")
            if result_type == "simple":
                value = result[0][0]
                insight = f"O resultado é: {value}"
            elif result_type == "ranking":
                top_1 = result[0]
                insight = f"O primeiro lugar é '{top_1[0]}' com {top_1[1]} registros. Ao todo, encontrei {len(result)} entradas."
            else:
                insight = f"Encontrei {len(result)} registros"
        
        logger.info(f"Interpretação completa: {insight[:100]}")
        return insight
    
    except Exception as e:
        error_str = str(e)
        
        # Tratamento específico para Ollama 500
        if "500" in error_str and "11434" in error_str:
            logger.warning(f"Ollama retornou erro 500. Usando fallback...")
            logger.warning("Dica: Verifique se Ollama está rodando com: docker ps | grep ollama")
        else:
            logger.error(f"Erro ao interpretar resultado: {e}")
        
        # Retornar resultado cru se LLM falhar
        if isinstance(result, list) and len(result) > 0:
            result_type = _detect_result_type(result)
            if result_type == "simple":
                return f"Resultado: {result[0][0]}"
            elif result_type == "ranking":
                top_1 = result[0]
                return f"O primeiro lugar é '{top_1[0]}' com {top_1[1]} registros."
            else:
                return f"Encontrei {len(result)} registros"
        return "Não foi possível processar o resultado"