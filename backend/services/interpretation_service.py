import json
import logging
from metadata.loader import load_metadata
from llm.router import get_llm

logger = logging.getLogger(__name__)


def interpret_result(question, result, model_name):
    """Interpreta resultado da query usando LLM"""
    
    logger.info(f"Interpretando resultado para: {question}")
    
    # Bloqueio crítico: checar se é erro
    if isinstance(result, dict) and "error" in result:
        error_msg = result.get("message", result["error"])
        logger.error(f"❌ Resultado é erro: {error_msg}")
        return f"Desculpe, ocorreu um erro ao executar a consulta: {error_msg}"
    
    # Checar se está vazio
    if not result or (isinstance(result, list) and len(result) == 0):
        logger.warning("Resultado da query vazio")
        return "Não encontrei registros que correspondam à sua pergunta."
    
    try:
        llm = get_llm(model_name)
        metadata = load_metadata()
        
        # Formatar resultado
        if isinstance(result, list):
            if len(result) > 0:
                # Se for COUNT, pegar só o valor
                if len(result) == 1 and len(result[0]) == 1:
                    formatted_result = str(result[0][0])
                else:
                    formatted_result = json.dumps(result[:10], ensure_ascii=False, indent=2)
            else:
                formatted_result = "Nenhum resultado"
        else:
            formatted_result = json.dumps(result, ensure_ascii=False, indent=2)
        
        prompt = f"""INSTRUÇÃO: Você DEVE responder exatamente com o número fornecido.

PERGUNTA DO USUÁRIO: {question}

DADOS (número exato a ser usado): {formatted_result}

REGRAS RIGOROSAS:
1. Use EXATAMENTE o número {formatted_result} na resposta
2. NÃO invente outros números
3. Responda em UMA frase simples em português
4. Exemplo de resposta correta: "Em São Paulo foram aplicadas 824 doses de vacina."

RESPOSTA (UMA frase usando o número {formatted_result}):"""

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
            logger.warning(f"⚠️ LLM retornou inútil, usando fallback")
            if isinstance(result, list) and len(result) > 0:
                if len(result) == 1 and len(result[0]) == 1:
                    num = result[0][0]
                    insight = f"O resultado é: {num}"
                else:
                    insight = f"Encontrei {len(result)} registros"
            else:
                insight = "Resultado processado com sucesso."
        
        logger.info(f"✅ Interpretação completa: {insight[:100]}")
        return insight
    
    except Exception as e:
        logger.error(f"❌ Erro ao interpretar resultado: {e}")
        # Retornar resultado cru se LLM falhar
        if isinstance(result, list) and len(result) > 0:
            if len(result) == 1 and len(result[0]) == 1:
                return f"Resultado: {result[0][0]}"
            else:
                return f"Encontrei {len(result)} registros"
        return "Não foi possível processar o resultado"