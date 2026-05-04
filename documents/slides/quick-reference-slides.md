# Quick Reference - Resumo Executivo dos Slides

## 🎯 SLIDE 1: PROBLEMA (2-3 min)
**Mensagem Principal:** "Dados existem, gestores não conseguem usá-los de forma ágil"

**Keywords para enfatizar:**
- ✗ Barreiras técnicas (SQL, sistemas heterogêneos)
- ✗ Barreiras sociotécnicas (precisa especialista)
- ✗ Fragmentação (dados em múltiplos lugares)
- ✓ DataSUS tem dados (contexto positivo)
- → **Resultado: Decisões lentas**

**Exemplo Real Mencionado:**
"Para evitar sobrecarga de leitos, gestor precisa consultar 4 sistemas diferentes. Semana de trabalho vs. alguns minutos com IA."

**Tom:** Preocupado mas esperançoso (não desanimador)

---

## 🎯 SLIDE 2: OBJETIVO (2-3 min)
**Mensagem Principal:** "IA que democractiza acesso a dados com interpretação contextualizada"

**Keywords para enfatizar:**
- ✓ Sem SQL (português natural)
- ✓ Múltiplos domínios integrados
- ✓ **Interpretação inteligente** (diferencial)
- ✓ Comparação de modelos IA
- → **Contexto: Objetivo estratégico "evitar sobrecarga de leitos"**

**Diferencial vs. Outro Grupo:**
"Eles: interface amigável | Nós: interface + IA de integração + interpretação"

**Tom:** Empolgado, confiante

---

## 🎯 SLIDE 3: MÉTODO (3-4 min)
**Mensagem Principal:** "4 etapas: Pergunta → Interpretação → SQL → Execução → Explicação"

**Keywords para enfatizar:**
- 1️⃣ Interpretação (LLM entende pergunta)
- 2️⃣ Geração SQL (consulta otimizada)
- 3️⃣ Execução (ClickHouse rápido)
- 4️⃣ **Interpretação Resultados** ← DIFERENCIAL
- Tecnologias: Ollama, ClickHouse, FastAPI
- Dados: 4 datasets, 68 questões, **14 com integração**

**Exemplo do Fluxo:**
"Pergunta: 'Cobertura de vacinação dezembro 2024?'
→ Extrai: métrica, período, tabela
→ Gera: SELECT cobertura FROM vacinacao...
→ Executa: 87.3%
→ Explica: 'Acima da meta de 85%'"

**Tom:** Técnico mas acessível (não jargão demais)

---

## 🎯 SLIDE 4: RESULTADOS (2-3 min)
**Mensagem Principal:** "Impacto científico, técnico e prático comprovável"

**Keywords para enfatizar:**
- 📚 **Científica**: Primeira avaliação multi-modelo em saúde pública BR
- 🔧 **Técnica**: Sistema funcional open-source
- 💼 **Prática**: Tempo reduzido, acesso expandido, decisões ágeis
- ⚠️ **Limitações**: 68 questões (vs. 500 acadêmico), 4 datasets, painel pequeno
- 🔮 **Próximos Passos**: Validação em campo, integração com portal oficial

**Exemplo de Impacto:**
"Gestor: 'Relação entre vacinação dez/24 e leitos jan/25?'
→ Sistema correlaciona 2 datasets
→ Resposta em segundos
→ Decisão baseada em evidência, rápida"

**Tom:** Confiante mas transparente (reconhecer limitações = credibilidade acadêmica)

---

## 🎤 3 FRASES PARA LEMBRAR

### Frase 1 (Abertura):
"O DataSUS é como uma biblioteca gigante - tem informação, mas os gestores precisam saber exatamente onde procurar e como combinar dados de diferentes seções. Meu trabalho é um assistente de IA que interpreta a pergunta do gestor e faz isso automaticamente."

### Frase 2 (Diferencial):
"Não é só 'gerar SQL melhor'. É 'gerar SQL + interpretar resultado em contexto de saúde pública + correlacionar múltiplas fontes automaticamente'."

### Frase 3 (Encerramento):
"O resultado é uma ferramenta que transforma gestores em analistas de dados - sem precisarem ser técnicos."

---

## 📊 DADOS PARA CITAR (IMPORTANTE!)

### Tamanho dos Datasets:
- Vacinação COVID-19: **5.847 registros**, 12 atributos
- Leitos Hospitalares: **2.156 registros**, 18 atributos
- Surtos de Doenças: **1.342 registros**, 14 atributos
- Cobertura Atenção Básica: **3.521 registros**, 15 atributos
- **Total: ~12.866 registros**

### Questões de Avaliação:
- **Total: 68 questões**
- Simples: 34 (1-2 cláusulas SQL)
- Complexas: 34 (3+ cláusulas)
- **Interoperabilidade: 14** (joins entre múltiplos datasets)

### Modelos Testados:
- Llama 2 (7B) - referência
- Mistral (7B) - otimizado para velocidade
- Neural Chat (7B) - diálogo especializado

### Métricas de Avaliação:
1. Precisão (% de respostas corretas)
2. Tempo de Resposta (meta: <10s)
3. Clareza (avaliação qualitativa, painel 3 gestores)
4. Robustez (% de variações processadas)
5. Interoperabilidade (capacidade de joins multi-dataset)

---

## ⚠️ PERGUNTAS QUE VÃO FAZER (PREPARADO PARA CADA)

### P1: "Por que não usar ChatGPT?"
**Resposta Pronta:**
"ChatGPT é proprietário, pago, depende de API cloud. Estou testando modelos open-source rodando localmente, sem custo. Além disso, comparar múltiplos modelos é parte da contribuição científica."

### P2: "E se o SQL gerado estiver errado?"
**Resposta Pronta:**
"Excelente pergunta - é EXATAMENTE o que a avaliação mede. Vou comparar SQL gerado vs. esperado em 68 cenários. Há también validação (não executa SQL quebrado) e fallback (gestor pode corrigir pergunta)."

### P3: "Qual a diferença para BI tradicional?"
**Resposta Pronta:**
"BI tradicional exige conhecimento de dados. Meu sistema via IA: linguagem natural, integração automática, interpretação contextualizada. É uma camada de AI acima."

### P4: "Funciona em produção?"
**Resposta Pronta:**
"Nesta fase é proof-of-concept. Funciona bem em laboratório com os 4 datasets. Próximo passo: piloto com secretaria real. Mas os resultados de avaliação vão dar confiança."

### P5: "Como garante qualidade da explicação?"
**Resposta Pronta:**
"Há avaliação qualitativa com painel de 3 gestores e especialistas. Métricas: clareza, presença de jargão, adequação de contexto. Também há logging de todas as explicações para auditoria."

### P6: "Comparação com ferramenta do outro grupo?"
**Resposta Pronta:**
"Não é competição - complementa. Eles fazem interface linda para dados. Eu vou uma camada acima: IA que integra múltiplas fontes e interpreta automaticamente. Podem trabalhar juntos."

---

## 🎬 SUGESTÃO: FAZER UMA DEMO (SE TIVER TEMPO)

Se restar tempo e quiser impressionar:

**Demo de 1-2 minutos:**
1. Abrir terminal / UI
2. "Vou fazer uma pergunta: 'Qual a cobertura de vacinação COVID em São Paulo em março de 2025?'"
3. Digitar pergunta
4. Sistema processa (mostre o tempo)
5. Retorna com número + explicação contextualizada
6. "Sem SQL. Sem especialista. Apenas linguagem natural."

### Cuidado:
- ✓ Fazer demo SÓ se 100% certo que funciona
- ✓ Ter backup (video gravado) se demo falhar
- ✓ Demonstrar rápido (não gaste mais de 2 min)

---

## 📱 COMO APRESENTAR COM CELULAR (Se necessário)

Se apresentar via Zoom/Teams e tiver que compartilhar tela do celular:
1. Abra os slides no Google Slides (compartilhado)
2. Ative "Apresentador" mode (mostra notas só pra você)
3. Use "Remoto" (arrow keys, ou página)
4. Fale claro em microfone bom (não fone de ouvido embutido)

---

## ✅ CHECKLIST 1 HORA ANTES

- [ ] Slides abrindo corretamente
- [ ] Speaker notes impressas ou em tablet
- [ ] Áudio do computador ligado e testado
- [ ] Mouse/clicker funcionando
- [ ] Backup da apresentação em pen drive + cloud
- [ ] Conexão de internet testada (se online)
- [ ] Roupa escolhida, cômoda, apropriada
- [ ] Água disponível perto
- [ ] Respirar fundo 3-5 minutos antes
- [ ] Revisar as 3 frases-chave que vai lembrar

---

## 💡 DURANTE A APRESENTAÇÃO - BOAS PRÁTICAS

| ✅ FAZER | ❌ NÃO FAZER |
|---------|-----------|
| Manter contato visual | Ler slides como script |
| Falar devagar/pausado | Falar rápido/nervoso |
| Gestos naturais | Braços cruzados |
| Responder perguntas honestamente | Inventar respostas |
| Reconhecer boas perguntas | Interromper questionador |
| Sorrir, estar relax | Parecer irritado ou defenestivo |
| Usar exemplos concretos | Falar só em abstrações |

---

## 🏁 FRASE DE OURO (Use no fim)

"Se conseguirmos com que gestores façam em segundos o que hoje demora dias, transformamos a agilidade de tomada de decisão em saúde pública. Isso é impacto real."

