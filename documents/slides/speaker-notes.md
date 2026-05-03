# Anotações do Apresentador (Speaker Notes)

## ABERTURA (30 segundos)
"Olá pessoal, meu nome é Lucas e estou desenvolvendo uma ferramenta de IA para democratizar o acesso a dados de saúde pública. Hoje vou apresentar 4 slides estruturados em Problema, Objetivo, Método e Resultados Esperados."

---

## SLIDE 1: PROBLEMA (2-3 minutos)

### O que falar (de forma natural):

**Parágrafo 1 - Contexto:**
"Todos sabem que o DataSUS disponibiliza dados públicos sobre saúde. Vacinação, leitos hospitalares, surtos de doenças, dados de atenção básica... muitos dados. Mas aqui está o paradoxo: apesar de toda essa informação disponível, gestores de saúde ainda têm dificuldade em usá-los efetivamente."

**Parágrafo 2 - Barreiras Técnicas:**
"Por quê? Primeiro, barreiras técnicas. Os dados estão em formatos diferentes, em sistemas diferentes. Se você quer fazer uma pergunta que correlacione dados de múltiplas fontes - por exemplo, 'qual é a relação entre cobertura de vacinação e hospitalização?' - você precisa saber SQL, precisar entender a estrutura de diferentes bancos de dados. Isso não é trivial."

**Parágrafo 3 - Barreiras Sociotécnicas:**
"Segundo, barreiras sociotécnicas. Mesmo que existam ferramentas de Business Intelligence sofisticadas - e elas são caras - os gestores precisam contratar analistas especializados para fazer essas análises. Não é ágil, não é acessível para a maioria das secretarias de saúde menores."

**Parágrafo 4 - Barreiras de Integração (seu diferencial!):**
"E terceiro, que é crítico para meu trabalho: os dados relevantes para tomar uma decisão estratégica estão fragmentados. Vou dar um exemplo concreto. Se um gestor quer 'evitar sobrecarga de ocupação de leitos' - que é um objetivo estratégico real em saúde pública - ele precisa correlacionar: quantos leitos tem disponível agora? Há surtos de doenças causando mais internações? Qual é a cobertura de vacinação (prevenção)? Qual a capacidade da atenção básica (porta de entrada)? Essas informações estão em 4 sistemas diferentes."

**Conclusão:**
"Então o problema é: **gestores têm dados, mas não conseguem usá-los de forma ágil para apoiar decisões estratégicas.** Essa é a lacuna que estou tentando resolver."

### Resposta antecipada:
**Se alguém perguntar: "Mas existe BI open-source, tipo Metabase?"**
> "Sim, existem, mas eles exigem conhecimento técnico para configurar. Meu foco é usar Inteligência Artificial para intermediar essa barreira - não pergunta em SQL, pergunta em português."

---

## SLIDE 2: OBJETIVO (2-3 minutos)

### O que falar:

**Parágrafo 1 - Objetivo Geral:**
"Meu objetivo geral é simples: usar modelos de linguagem de IA para permitir que gestores façam perguntas em português natural sobre dados complexos, e recebam respostas inteligentes."

**Parágrafo 2 - Por que é diferente:**
"Agora, quando eu digo 'respostas inteligentes', não é apenas "aqui está seu SQL gerado". É: 'aqui está sua resposta, interpretada no contexto de saúde pública, conectada ao que você realmente quis saber'."

**Parágrafo 3 - Os 4 Pilares (confira slide):**
"Especificamente, meu trabalho tem 4 objetivos específicos:"

1. "**Sem SQL**: Gestores sem conhecimento técnico podem consultar dados."
2. "**Interoperabilidade**: O sistema consegue correlacionar dados de múltiplos domínios automaticamente."
3. "**Interpretação de Resultados**: Não é só números brutos, é contexto em saúde pública."
4. "**Comparação de Modelos**: Não vou usar apenas um modelo de IA, vou testar múltiplos (Llama 2, Mistral, Neural Chat) para ver qual funciona melhor para saúde."

**Parágrafo 4 - Diferencial vs. outros grupos:**
"Agora, para deixar claro: sei que há outro grupo aqui desenvolvendo uma ferramenta também. A diferença é que eles focam em interface amigável para dados existentes - O que é super válido. Eu estou indo um passo além: usar IA para integração inteligente e interpretação dos resultados."

**Parágrafo 5 - Contexto Estratégico:**
"Tudo isso será validado em torno de um objetivo estratégico real: 'evitar sobrecarga de ocupação de leitos hospitalares'. Isso não é imaginário - é um problema real que gestores enfrentam, especialmente em contextos de emergência de saúde."

### Resposta antecipada:
**"Por que múltiplos modelos? Não é mais fácil usar ChatGPT?"**
> "ChatGPT é proprietário, custa, e depende de conexão com servidor da OpenAI. Estou testando modelos open-source que rodam localmente, sem custo de API. E precisamente porque são diferentes, quero medir qual é melhor para dados de saúde pública."

---

## SLIDE 3: MÉTODO (3-4 minutos)

### O que falar:

**Parágrafo 1 - Visão Geral do Fluxo:**
"Vou andar pelo fluxo do sistema. Imagine um gestor que faz a pergunta: 'Qual a cobertura de vacinação em dezembro de 2024?'"

**Parágrafo 2 - Etapa 1 (Interpretação):**
"**Etapa 1: Interpretação**. Meu modelo de IA lê a pergunta em português e entende: 'Ok, ele quer a métrica cobertura, período dezembro de 2024, tabela vacinação'. Extrai essas informações estruturadas."

**Parágrafo 3 - Etapa 2 (Geração SQL):**
"**Etapa 2: Geração SQL**. Com essas informações, o sistema gera uma consulta SQL otimizada para ClickHouse. Não é aleatória - usa templates quando possível, modelos de IA quando é mais complexo."

**Parágrafo 4 - Etapa 3 (Execução):**
"**Etapa 3: Execução**. A query é validada, e depois executada no banco de dados ClickHouse, que é otimizado para operações analíticas. No nosso exemplo, retorna 87.3%."

**Parágrafo 5 - Etapa 4 (Interpretação de Resultados) - SEU DIFERENCIAL!:**
"**Etapa 4: Interpretação de Resultados** - e aqui é o diferencial. Em vez de apenas retornar '87.3%', meu sistema usa IA novamente para gerar: 'Cobertura foi de 87.3%, acima da meta de 85% recomendada pela Organização Mundial de Saúde'. Ou seja, contextualiza no domínio de saúde pública."

**Parágrafo 6 - Componentes Técnicos:**
"Teknicamente: modelo Llama 2 rodando via Ollama (execução local), ClickHouse para o banco (performático), FastAPI para a API (rápida e com documentação automática)."

**Parágrafo 7 - Dados:**
"Estou usando 4 datasets de domínios diferentes: vacinação COVID, leitos hospitalares, surtos de doenças, e cobertura de atenção básica. Múltiplos domínios permitem testar integração."

**Parágrafo 8 - Avaliação:**
"A avaliação consiste de 68 questões. 30 simples, 38 complexas. E o importante: 14 dessas questões complexas exigem integração entre datasets - por exemplo, 'qual a correlação entre picos de surtos e ocupação de leitos?'. Essas 14 vão testar meu objetivo de interoperabilidade."

### Resposta antecipada:
**"Como garantem que o SQL gerado está correto?"**
> "Ótima pergunta. Por isso a avaliação: vou comparar o SQL gerado vs. SQL esperado para cada uma das 68 questões. Mensuramos precisão, tempo de resposta, robustez. Se tiver erro, você vê onde foi."

**"Rodando localmente - qual a velocidade esperada?"**
> "Meta é menos de 10 segundos para 95% das queries. Estaremos medindo cada etapa (interpretação, execução, geração de explicação) para identificar gargalos."

---

## SLIDE 4: RESULTADOS ESPERADOS (2-3 minutos)

### O que falar:

**Parágrafo 1 - Dimensão Científica:**
"Resultados esperados em 4 dimensões. Primeiro, científica. Esta é, até onde sei, a primeira avaliação sistemática de múltiplos modelos de IA em contexto de dados de saúde pública brasileira. E a primeira que realmente testa integração de múltiplos datasets via linguagem natural. Isso é publicável em periódicos de Informática em Saúde."

**Parágrafo 2 - Dimensão Técnica:**
"Segundo, técnica. Vou entregar um sistema funcional, open-source, que demonstra viabilidade. Código disponível para comunidade, para outros pesquisadores, para outras secretarias de saúde que queiram usar."

**Parágrafo 3 - Dimensão Prática:**
"Terceiro, prática. O impacto no mundo real seria enorme. Tempo de análise: em vez de dias com analistas, minutos com o sistema. Acesso: em vez de técnicos especializados, gestores conseguem explorar dados. Decisões são mais ágeis."

**Parágrafo 4 - Exemplo Concreto (importante!):**
"Deixa eu concretizar: Um gestor na secretaria de saúde do Rio de Janeiro quer verificar: 'Qual a relação entre cobertura de vacinação em dezembro de 2024 e a ocupação de leitos em janeiro de 2025?' Ele digita isso em português no sistema. Meu sistema correlaciona automaticamente os dados de 2 tabelas diferentes. Retorna: 'Existe correlação positiva - regiões com maior cobertura vacinal tenderam a ter menor ocupação de leitos'. E isso tudo em alguns segundos. Sem SQL. Sem analista. O gestor toma a decisão."

**Parágrafo 5 - Dimensão de Viabilidade:**
"Quarto, viabilidade técnica. Comprova que LLMs são viáveis para consulta a dados de saúde, que modelos open-source podem rodar localmente, que interoperabilidade é alcançável."

**Parágrafo 6 - Limitações (IMPORTANTE - mostra maturidade acadêmica):**
"Agora, honestidade acadêmica: há limitações. 68 questões é bom, mas benchmarks tradicionais têm 500+. 4 datasets é um bom começo, mas expansível. Validação com apenas 3 gestores é limitada - próximas fases teriam mais. Comparação com modelos proprietários (GPT-4) seria ideal, mas custo probibetivo."

**Parágrafo 7 - Próximos Passos:**
"Próximos passos: divulgação científica (artigos), validação em campo com secretarias de saúde reais, integração com plataformas oficiais como Portal de Dados Abertos."

### Resposta antecipada:
**"Como podem ter certeza que a ferramenta vai funcionar em produção?"**
> "Nesta fase é proof-of-concept. Funciona bem em laboratório. Próxima fase seria piloto com uma secretaria real. Mas os resultados de 68 questões vão dar confiança de que está no caminho certo."

**"E se o gestor fizer uma pergunta que o modelo não consegue responder?"**
> "Ótima observação. Estamos testando justamente isso - robustez do modelo. E há fallback: sistema pode pedir para gesttor reformular ou deixar feedback. Isso faz parte da avaliação."

---

## ENCERRAMENTO (30 segundos)

"Então, resumindo: temos um problema real (dados fragmentados, acesso difícil), um objetivo claro (IA para integração e interpretação), um método estruturado (4 etapas, múltiplos modelos, avaliação rigorosa), e resultados esperados que impactam ciência, tecnologia e prática em saúde pública. Fico aberto a perguntas."

---

## DICAS DE ENTREGA

### Gestos e Movimentação
- **Não fique parado**: Varie entre estar perto da tela (detalhe técnico) e afastado (visão geral)
- **Use gestos para contar**: "Primeiro..." (dedo), "Segundo..." (outro dedo), etc.
- **Mantenha contato visual**: Alterne entre slides, notas, e audiência

### Entonação
- **Problema**: Tom mais sério, preocupado
- **Objetivo**: Tom mais esperançoso, empolgado
- **Método**: Tom técnico, mas não robótico
- **Resultados**: Tom de confiança, mas honesto sobre limitações

### Pacing
- **Não fale rápido**: 1 segundo por linha é ok
- **Pause antes de transições de slide**: "Então isso leva à próxima questão..."
- **Pause depois de perguntas principais**: Deixe audiência processar

### Se Ficar Nervoso
- Beba água antes de começar
- Respire fundo entre slides
- Lembre-se: você é especialista no assunto, a audiência quer aprender com você
- Se não souber resposta: "Ótima pergunta, não tenho resposta agora, mas posso pesquisar e voltar com você"

---

## CHECKLIST FINAL

- [ ] Slides abertos no full-screen
- [ ] Notas do apresentador (este documento) aberto no seu laptop
- [ ] Clicker/remote da apresentação carregado
- [ ] Áudio do computador testado (se tem video)
- [ ] Backup em pen drive ou cloud (GoogleDrive, Dropbox)
- [ ] Roupa adequada para ambiente acadêmico
- [ ] Chegar 5 minutos antes
- [ ] Fazer "teste de som" com áudio
- [ ] Postura ereta, não cruzar braços
- [ ] Sorrir no início - primeira impressão conta!

---

## DISTRIBUIÇÃO DE TEMPO (assumindo 15 minutos)

- Abertura: 0:00-0:30 (30s)
- Slide 1 (Problema): 0:30-3:00 (2:30)
- Slide 2 (Objetivo): 3:00-5:30 (2:30)
- Slide 3 (Método): 5:30-9:30 (4:00) ← slide mais longo
- Slide 4 (Resultados): 9:30-12:00 (2:30)
- Encerramento: 12:00-12:30 (0:30)
- **Perguntas e Discussão: 12:30-15:00 (2:30)**

Se faltar tempo: comrime Slide 3 (técnico) para 3 minutos. Priorize Problema e Objetivos.

