#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json

# Read the 68 questions from the SEIDIG file
with open('docs/PERGUNTAS_SEIDIG_68.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Create new content with 204 questions (68 × 3 replicas)
new_content = """# Perguntas-Teste para Avaliação Integral de EasyDataSUS
## 204 Questões para Teste Experimental (FASE 7)

**Documento estruturado para FASE 7: Execução de experimentos com replicação de testes**

Essa suite contém **68 questões principais** alinhadas com Objetivos Estratégicos SEIDIG, cada uma replicada **3 vezes** para validar consistência e robustez do sistema LLM.

**Estrutura de Teste:**
- **68 Questões Únicas**: Cobrindo 4 datasets e interoperabilidade
- **3 Replicações por Questão**: Q1-Rep1, Q1-Rep2, Q1-Rep3... Q68-Rep1, Q68-Rep2, Q68-Rep3
- **Total de Execuções**: 68 × 3 = **204 testes**
- **Métricas Coletadas**: Acurácia, tempo de resposta, tipo de erro

**Distribuição:**
- **OE 3.6.1 (Imunização)**: COVID-19 (15×3=45 testes) + UBS (15×3=45 testes) = 90 testes
- **OE 9.1 (Vigilância/Gestão)**: SRAG (15×3=45 testes) + Leitos (15×3=45 testes) = 90 testes  
- **Interoperabilidade**: 8×3 = 24 testes
- **TOTAL**: 204 testes

---

## 📊 Resumo de Distribuição

| Categoria | Questões | Replicas | Total | Complexidade |
|-----------|----------|----------|-------|--------------|
| COVID-19 (OE 3.6.1) | 15 | 3 | 45 | Simples/Média/Complexa |
| UBS (OE 3.6.1) | 15 | 3 | 45 | Simples/Média/Complexa |
| SRAG (OE 9.1) | 15 | 3 | 45 | Simples/Média/Complexa |
| Leitos (OE 9.1) | 15 | 3 | 45 | Simples/Média/Complexa |
| Interoperabilidade | 8 | 3 | 24 | Complexa |
| **TOTAL** | **68** | **3** | **204** | **100%** |

---

## 🎯 Estrutura de Teste

Cada uma das 68 questões é replicada **3 vezes** com a mesma formulação:

**Exemplo: Questão 1 (Taxa de Cobertura Vacinal)**
- **Teste 1.1**: Replicação 1 da questão
- **Teste 1.2**: Replicação 2 da questão  
- **Teste 1.3**: Replicação 3 da questão

Isso permite:
- ✅ Validar **consistência** do LLM (mesma pergunta = mesma resposta?)
- ✅ Medir **variabilidade** em tempo de resposta
- ✅ Identificar **falhas intermitentes**
- ✅ Calcular **média e desvio padrão** de performance

---

## 🔵 COVID-19 Vacinação - 45 Testes

### Q1-Q5: Monitoramento de Cobertura
1. Taxa de cobertura vacinal (% da população) - 3 replicas
2. Estado com maior cobertura de 1ª dose - 3 replicas
3. Esquema vacinal completo (2ª dose) - 3 replicas
4. Taxa de abandono por estado - 3 replicas
5. Reforços em relação ao total - 3 replicas

### Q6-Q10: Equidade e Vulnerabilidade
6. Distribuição por sexo - 3 replicas
7. Faixa etária com menor vacinação - 3 replicas
8. Município com menor cobertura - 3 replicas
9. Distribuição por faixa etária e estado - 3 replicas
10. Rede pública vs privada - 3 replicas

### Q11-Q15: Eficiência Logística
11. Vacina mais utilizada - 3 replicas
12. Fabricante com maior volume - 3 replicas
13. Evolução temporal de doses - 3 replicas
14. Pico de vacinação por estado - 3 replicas
15. Doses de reforço por tipo - 3 replicas

---

## 🟢 Atenção Primária (UBS) - 45 Testes

### Q16-Q20: Mapeamento de Capacidade
16. Total de UBS ativas - 3 replicas
17. Distribuição de UBS por estado - 3 replicas
18. UBS por 100 mil habitantes - 3 replicas
19. Cobertura municipal - 3 replicas
20. Municípios sem UBS - 3 replicas

### Q21-Q25: Análise Geográfica e Acesso
21. Maior densidade de UBS - 3 replicas
22. Padrão de distribuição no Nordeste - 3 replicas
23. Informações de localização completas - 3 replicas
24. Raio médio de cobertura - 3 replicas
25. UBS urbanas vs rurais - 3 replicas

### Q26-Q30: Estrutura e Capacidade
26. Tipo de gestão predominante - 3 replicas
27. UBS públicas por estado - 3 replicas
28. Dados de contato registrados - 3 replicas
29. Distribuição por bairro (ex: SP) - 3 replicas
30. Déficit de UBS por habitante - 3 replicas

---

## 🔴 SRAG - 45 Testes

### Q31-Q35: Monitoramento de Casos
31. Total de casos SRAG notificados - 3 replicas
32. Evolução semanal de casos - 3 replicas
33. Estado com maior número de SRAG - 3 replicas
34. Incidência por estado (por 100k hab) - 3 replicas
35. Dispersão geográfica (municípios) - 3 replicas

### Q36-Q40: Gravidade Clínica
36. Taxa de hospitalização - 3 replicas
37. Mortalidade total - 3 replicas
38. Taxa de mortalidade em hospitalizados - 3 replicas
39. Taxa de internação em UTI - 3 replicas
40. Estado com maior taxa de mortalidade - 3 replicas

### Q41-Q45: Etiologia
41. Distribuição de sintomas - 3 replicas
42. Faixa etária mais acometida - 3 replicas
43. Proporção com comorbidades - 3 replicas
44. Confirmação laboratorial - 3 replicas
45. Agente etiológico mais frequente - 3 replicas

---

## 🟠 Leitos - 45 Testes

### Q46-Q50: Mapeamento de Capacidade
46. Total de leitos - 3 replicas
47. Leitos SUS - 3 replicas
48. Proporção de leitos SUS - 3 replicas
49. Estado com maior capacidade - 3 replicas
50. Densidade de leitos por 1000 hab - 3 replicas

### Q51-Q55: Especialidades
51. Total de leitos UTI - 3 replicas
52. Proporção de leitos UTI - 3 replicas
53. Tipo de unidade predominante - 3 replicas
54. Distribuição de especialidades de UTI - 3 replicas
55. UTI neonatal por nascimentos - 3 replicas

### Q56-Q60: Gestão e Resiliência
56. Tipo de gestão - 3 replicas
57. Leitos SUS em rede privada - 3 replicas
58. Estado com maior percentual SUS - 3 replicas
59. Distribuição regional - 3 replicas
60. Município com melhor infraestrutura - 3 replicas

---

## 🔗 Interoperabilidade - 24 Testes

### Q61-Q68: Análises Cruzadas

61. Municípios com SRAG e cobertura de UBS - 3 replicas
62. Cobertura de UBS em municípios com maior SRAG - 3 replicas
63. SRAG hospitalizados com baixa capacidade de leitos - 3 replicas
64. Cobertura vacinal nos municípios com maior SRAG - 3 replicas
65. UTI SUS em estados com maior mortalidade por SRAG - 3 replicas
66. Resposta de internação hospitalar em 7 dias - 3 replicas
67. Correlação entre densidade de UBS e cobertura vacinal - 3 replicas
68. Déficit de resposta (SRAG grave mas leitos insuficientes) - 3 replicas

---

## 📋 Resumo Final

**Total de Testes**: 204

**Distribuição por Objetivo Estratégico:**
- OE 3.6.1 (Imunização + Atenção Primária): 90 testes (44%)
- OE 9.1 (Vigilância + Gestão): 90 testes (44%)
- Multi-OE (Interoperabilidade): 24 testes (12%)

**Distribuição por Complexidade:**
- Simples: 45 testes (22%)
- Média: 105 testes (51%)
- Complexa: 54 testes (27%)

---

## ✅ Próximas Etapas (FASE 7-9)

1. **FASE 7**: Executar 204 testes com 3 replicas cada
   - Coletar: acurácia, tempo de resposta, tipos de erro
   - Output: `test_results_68_questoes.json`

2. **FASE 8**: Analisar resultados
   - Estatísticas por categoria, complexidade, dataset
   - Identificar padrões de erro
   - Output: `docs/experimentos/analise_resumida.json`

3. **FASE 9**: Documentar na dissertação
   - Capítulo de avaliação da ferramenta
   - Discussão de resultados
   - Recomendações

---

**Versão**: 2.0 - Atualizado 21/05/2026
**Status**: ✅ 68 questões + 3 replicações = 204 testes preparados para execução

Para documentação detalhada das 68 questões, ver: [docs/PERGUNTAS_SEIDIG_68.md](PERGUNTAS_SEIDIG_68.md)
"""

# Write the new content
with open('docs/PERGUNTAS_TESTE_GESTOR.md', 'w', encoding='utf-8') as f:
    f.write(new_content)

print("✅ Arquivo atualizado com 204 perguntas!")
print("   - 68 questões principais")
print("   - 3 replicas cada")
print("   - Total: 204 testes")
