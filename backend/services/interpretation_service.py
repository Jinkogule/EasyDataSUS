import json
import logging
import re
from datetime import datetime, date
from metadata.loader import load_metadata
from llm.router import get_llm

logger = logging.getLogger(__name__)


class DateTimeEncoder(json.JSONEncoder):
    """JSON encoder customizado para lidar com objetos de data e hora"""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def _detect_distribution_keywords(question):
    """
    Detecta palavras-chave que indicam um tipo específico de distribuição.
    Retorna dicionário com contexto sobre a pergunta.
    """
    question_lower = question.lower()
    
    keywords = {
        "sexo": ["sexo", "gênero", "feminino", "masculino", "biológico"],
        "faixa_etaria": ["faixa etária", "idade", "faixa de idade", "grupo etário"],
        "estado": ["estado", "estados", "por estado", "cada estado", "SP", "RJ", "MG", "BA"],
        "municipio": ["município", "cidade", "municipios"],
        "fabricante": ["fabricante", "vacina", "marca"],
        "mes": ["mês", "meses", "mensal", "temporal", "evolução"],
        "dose": ["dose", "doses", "tipo de dose", "esquema"],
    }
    
    detected = {}
    for category, keywords_list in keywords.items():
        for kw in keywords_list:
            if kw in question_lower:
                detected[category] = True
                break
    
    return detected


def _detect_result_type(result, question=""):
    """
    Detecta o tipo de resultado da query de forma mais inteligente.
    
    Returns:
        "simple": Um valor numérico simples (COUNT)
        "distribution": Distribuição com poucas categorias (sexo, faixas etárias, etc)
        "ranking": Ranking de múltiplas entidades (estados, cidades, etc)
        "multiple": Múltiplas colunas de dados
        "temporal": Série temporal com datas/meses
    """
    if not isinstance(result, list) or len(result) == 0:
        return "empty"
    
    first_row = result[0]
    
    # Um valor: COUNT(*)
    if len(result) == 1 and len(first_row) == 1:
        return "simple"
    
    # Duas colunas com valores
    if len(first_row) == 2 and isinstance(first_row[0], str):
        num_rows = len(result)
        
        # Se temos 2-4 categorias, é provavelmente uma distribuição
        if 2 <= num_rows <= 4:
            # Check se parecem ser categorias pequenas (F/M, Sim/Não, etc)
            categories = [row[0] for row in result]
            avg_len = sum(len(str(c)) for c in categories) / len(categories)
            if avg_len < 30:  # Nomes curtos indicam categorias, não cidades
                logger.debug(f"Detectado como distribuição: {num_rows} categorias com avg len={avg_len:.1f}")
                return "distribution"
        
        # Se contém padrões de data/mês, é série temporal
        # NOTA: Não usar [A-Z][a-z]{2} pois match com siglas de estado (AC, SP, etc)
        if any(re.match(r'\d{4}-\d{2}-\d{2}|\d{4}/\d{2}|\d{2}/\d{2}/\d{4}', str(row[0])) for row in result):
            logger.debug("Detectado como série temporal pelos padrões de data")
            return "temporal"
        
        # Se contém "2022", "2023", "2024", "2025" → série temporal
        if any(re.search(r'\d{4}', str(row[0])) for row in result[:5]):
            # Mas se todas as linhas têm 2 caracteres, é código de estado (UF), não data
            if all(len(str(row[0])) <= 3 for row in result[:5]):
                logger.debug(f"Detectado como ranking (códigos curtos tipo UF/estado)")
                return "ranking"
            logger.debug("Detectado como série temporal (contém anos)")
            return "temporal"
        
        # Caso contrário, é ranking
        logger.debug(f"Detectado como ranking: {num_rows} entidades")
        return "ranking"
    
    # Múltiplas colunas: provavelmente temporal ou múltiplo
    if len(first_row) > 2:
        # Se terceira coluna tem datas/períodos, é temporal
        if len(result) > 5:
            return "temporal"
        return "multiple"
    
    # Múltiplas colunas padrão
    return "multiple"


def _calculate_percentages(result):
    """Calcula percentuais para cada linha no resultado"""
    total = sum(row[1] for row in result if isinstance(row[1], (int, float)))
    if total == 0:
        return result
    
    return [(row[0], row[1], round(100 * row[1] / total, 1)) for row in result]


def _format_prompt_for_type(question, result, result_type):
    """
    Gera prompt específico para cada tipo de resultado com contexto apropriado.
    """
    
    if result_type == "simple":
        # Um número simples
        value = result[0][0]
        return f"""Você é um assistente de dados em saúde pública.
Responda em português claro e acessível.

PERGUNTA: {question}
RESULTADO: {value}

INSTRUÇÕES:
- Responda com UMA frase simples
- Use EXATAMENTE o número {value}
- Não invente contexto ou interpretações
- Seja direto e factual

RESPOSTA:"""
    
    elif result_type == "distribution":
        # Distribuição de categorias: [["F", 206600], ["M", 180115], ...]
        result_pct = _calculate_percentages(result)
        formatted_lines = []
        for item in result_pct:
            label, count, pct = item[0], item[1], item[2] if len(item) > 2 else 0
            formatted_lines.append(f"- {label}: {count:,} ({pct}%)")
        
        formatted = "\n".join(formatted_lines)
        total = sum(row[1] for row in result)
        
        return f"""Você é um assistente de dados em saúde pública.

PERGUNTA: {question}

RESULTADO (DISTRIBUIÇÃO entre {len(result)} categorias):
{formatted}
TOTAL: {total:,}

INSTRUÇÕES CRÍTICAS PARA DISTRIBUIÇÃO:
1. Mencione TODAS as categorias encontradas, não apenas uma
2. Inclua os números E os percentuais
3. Escolha prontamente entre feminino/masculino se for "sexo"
4. Use "Feminino" e "Masculino" para valores de sexo, não "F" e "M"
5. Dê uma interpretação clara da proporção

EXEMPLOS CORRETOS para distribuição:
- Se resultado: Sexo F: 210133, Sexo M: 180115
  Resposta: "A distribuição de vacinações foi: Feminino 210.133 (53,8%) e Masculino 180.115 (46,2%), indicando participação equilibrada de ambos os gêneros."

- Se resultado: Faixa etária 18-30: 5000, 30-60: 8000, 60+: 2000
  Resposta: "A maior parte foi adultos de 30-60 anos (57%), seguida de 18-30 anos (36%) e 60+ anos (14%)."

RESPOSTA (incluindo TODAS as categorias com números e %):"""
    
    elif result_type == "temporal":
        # Série temporal: [["2022-01", 1000], ["2022-02", 1500], ...]
        formatted_lines = []
        for row in result:
            formatted_lines.append(f"- {row[0]}: {row[1]:,} registros")
        
        formatted = "\n".join(formatted_lines[:10])  # Top 10
        max_value = max(row[1] for row in result)
        min_value = min(row[1] for row in result)
        max_entry = [row for row in result if row[1] == max_value][0]
        min_entry = [row for row in result if row[1] == min_value][0]
        
        # Detectar se a pregunta busca mínimo ou máximo
        is_asking_for_min = any(word in question.lower() for word in ["menor", "mínimo", "minima", "smallest", "least"])
        
        if is_asking_for_min:
            return f"""Você é um assistente de dados em saúde pública.

PERGUNTA: {question}

RESULTADO (SÉRIE TEMPORAL - {len(result)} períodos):
{formatted}

VALOR MÍNIMO: {min_entry[0]} com {min_value:,} registros
VALOR MÁXIMO: {max_entry[0]} com {max_value:,} registros

INSTRUÇÕES:
1. A pergunta pede o MENOR/MÍNIMO
2. Responda focando em {min_entry[0]}: {min_value:,} registros
3. Você pode mencionar também o máximo para contraste
4. Comente sobre a disparidade

RESPOSTA (mencionando o MÍNIMO {min_entry[0]}):"""  
        else:
            return f"""Você é um assistente de dados em saúde pública.

PERGUNTA: {question}

RESULTADO (SÉRIE TEMPORAL - {len(result)} períodos):
{formatted}

PICO: {max_entry[0]} com {max_value:,} registros

INSTRUÇÕES PARA SÉRIE TEMPORAL:
1. Identifique o período de pico/máximo
2. Comente sobre a tendência geral (subida, queda, estável)
3. Use nomes de meses quando aplicável (janeiro, fevereiro, etc)
4. Destaque padrões importantes

EXEMPLO CORRETO:
- Resposta: "A vacinação atingiu pico em março de 2022 com 52.400 doses, iniciando com aumento progressivo de novembro e desacelerando após."

RESPOSTA (incluindo pico e tendência):""" 
    
    elif result_type == "ranking":
        # Ranking: [["SP", 156000], ["BA", 89500], ...]
        # Detectar se a pergunta pede MÍNIMO ou MÁXIMO
        is_asking_for_min = any(word in question.lower() for word in ["menor", "mínimo", "minima", "lowest", "least", "menos"])
        is_asking_for_max = any(word in question.lower() for word in ["maior", "máximo", "maxima", "highest", "most", "mais"])
        
        if is_asking_for_min:
            # Mostrar do menor para maior
            bottom_5 = result[:5]
            formatted = "\n".join([f"{rank+1}º - {row[0]}: {row[1]:,}" for rank, row in enumerate(bottom_5)])
            first_place = result[0][0]
            first_value = result[0][1]
            last_place = result[-1][0]
            last_value = result[-1][1]
            
            return f"""Você é um assistente de dados em saúde pública.

PERGUNTA: {question}

RESULTADO (RANKING ASCENDENTE - {len(result)} entidades, do MENOR para MAIOR):
{formatted}

MENOR: {first_place} com {first_value:,}
MAIOR: {last_place} com {last_value:,}
DISPARIDADE: {last_value:,} / {first_value:,} = {last_value/first_value:.0f}x

INSTRUÇÕES (pergunta pede MENOR):
1. Mencione claramente o MENOR: {first_place} com {first_value:,}
2. Contraste com o maior para mostrar disparidade: {last_place} com {last_value:,}
3. Use contexto geográfico apropriado
4. Comente sobre a disparidade de cobertura

EXEMPLO: "O estado com MENOR cobertura é AC com apenas 548 vacinações, enquanto SP lidera com 156.000 (285x mais)."

RESPOSTA (mencionando o MENOR {first_place}):""" 
        else:
            # Mostrar do maior para menor (padrão)
            top_5 = result[-5:] if is_asking_for_max else result[:5]  # Inversão se DESC
            formatted = "\n".join([f"{rank+1}º - {row[0]}: {row[1]:,}" for rank, row in enumerate(top_5)])
            
            first_place = result[0][0]
            first_value = result[0][1]
            last_place = result[-1][0]  
            last_value = result[-1][1]
            
            return f"""Você é um assistente de dados em saúde pública.

PERGUNTA: {question}

RESULTADO (TOP {min(5, len(result))} de {len(result)} entidades):
{formatted}

INSTRUÇÕES PARA RANKING:
1. Mencione o 1º lugar e seu valor
2. Comente sobre disparidades (se houver grandes diferenças)
3. Se relevante, mencione o último lugar
4. Use contexto geográfico/institucional apropriado

EXEMPLOS CORRETOS:
- Para ranking de estados: "São Paulo lidera com 156.000 vacinações, representando 40% do total, enquanto Acre tem apenas 548."
- Para ranking de cidades: "A capital concentra 63% das vacinações."

RESPOSTA (incluindo 1º lugar e contexto da disparidade):""" 
    
    elif result_type == "multiple":
        # Múltiplos dados - lidar com datas
        try:
            formatted_result = json.dumps(result[:5], ensure_ascii=False, indent=2, cls=DateTimeEncoder)
        except Exception as e:
            logger.warning(f"Erro ao serializar resultado múltiplo: {e}. Usando versão simplificada")
            # Fallback: converter tudo para string
            formatted_result = str(result[:5])
        
        return f"""Você é um assistente de dados em saúde pública.

PERGUNTA: {question}

RESULTADO (primeiros 5 registros):
{formatted_result}

INSTRUÇÕES:
- Responda com UMA frase simples em português
- Use apenas os dados fornecidos
- Não invente contextos
- Seja factual e breve

RESPOSTA:"""
    
    else:
        # Fallback
        try:
            formatted = json.dumps(result[:3], ensure_ascii=False, cls=DateTimeEncoder)
        except:
            formatted = str(result[:3])
        
        return f"""Responda em UMA frase simples em português sobre:
{question}

Dados: {formatted}

RESPOSTA:"""


def interpret_result(question, result, model_name):
    """Interpreta resultado da query usando LLM com contexto inteligente"""
    
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
        
        # Detectar tipo de resultado PASSANDO A PERGUNTA para contexto melhor
        result_type = _detect_result_type(result, question)
        logger.info(f"Tipo de resultado detectado: {result_type}")
        
        # Gerar prompt apropriado
        prompt = _format_prompt_for_type(question, result, result_type)

        logger.debug(f"Enviando para LLM modelo={model_name} com tipo={result_type}")
        insight = llm.generate(prompt)
        logger.debug(f"Resposta bruta do LLM: len={len(insight) if insight else 0}")
        
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
                'I AM A VIRTUAL', 'I AM SORRY', 'INSTRUÇÕES', 'REGRA'
            ]):
                continue
            if line.strip():
                cleaned_lines.append(line.strip())
        
        insight = '\n'.join(cleaned_lines)
        insight = insight.strip('"').strip("'").strip()
        
        # Validar resultado
        if not insight or insight in ["", "None", "null", "...", "Resultado:", "Resposta:"]:
            logger.warning(f"LLM retornou inútil, usando fallback para tipo: {result_type}")
            insight = _generate_fallback_response(result, result_type, question)
        
        logger.info(f"Interpretação gerada com sucesso (tipo={result_type}, len={len(insight)})")
        return insight
    
    except Exception as e:
        error_str = str(e)
        logger.error(f"Erro ao interpretar resultado: {e}")
        
        # Retornar resultado cru se LLM falhar
        return _generate_fallback_response(result, _detect_result_type(result, question), question)


def _generate_fallback_response(result, result_type, question=""):
    """Gera resposta fallback quando LLM falha ou retorna nada útil"""
    
    # Detectar se pergunta busca menor ou máximo
    is_asking_for_min = any(word in question.lower() for word in ["menor", "mínimo", "minima", "lowest", "least"])
    
    if result_type == "simple":
        return f"Resultado: {result[0][0]}"
    
    elif result_type == "distribution":
        total = sum(row[1] for row in result)
        lines = []
        for row in result:
            pct = round(100 * row[1] / total, 1) if total > 0 else 0
            lines.append(f"{row[0]}: {row[1]:,} ({pct}%)")
        return "Distribuição encontrada: " + "; ".join(lines)
    
    elif result_type == "temporal":
        max_entry = max(result, key=lambda x: x[1])
        min_entry = min(result, key=lambda x: x[1])
        if is_asking_for_min:
            return f"Mínimo em {min_entry[0]} com {min_entry[1]:,} registros. Máximo em {max_entry[0]} com {max_entry[1]:,}. Total de {len(result)} períodos."
        else:
            return f"Pico em {max_entry[0]} com {max_entry[1]:,} registros. Total de {len(result)} períodos."
    
    elif result_type == "ranking":
        first = result[0]
        last = result[-1]
        
        if is_asking_for_min:
            # Se pergunta pede menor e resultado está ascendente, primeiro é o menor
            return f"Menor cobertura: {first[0]} com {first[1]:,} registros. Maior: {last[0]} com {last[1]:,}. Disparidade: {last[1]/first[1]:.0f}x. Total de {len(result)} entidades."
        else:
            # Se pergunta pede maior e resultado está descendente, primeiro é o maior
            return f"Maior cobertura: {first[0]} com {first[1]:,} registros. Menor: {last[0]} com {last[1]:,}. Total de {len(result)} entidades."
    
    else:
        return f"Encontrei {len(result)} registros"