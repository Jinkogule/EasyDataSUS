# Template Visual para Google Slides / PowerPoint

## Como usar este template:
1. Copie e cole o conteúdo de cada slide em seu Google Slides / PowerPoint
2. Adicione cores, ícones e imagens conforme indicado
3. Ajuste tamanhos de fonte conforme sua preferência

---

# SLIDE 1: O PROBLEMA

## TÍTULO (48pt, Bold, Vermelho/Laranja)
A Lacuna no Acesso a Dados de Saúde Pública

## CONTEÚDO

### Coluna Esquerda (Tamanho 28pt)
**Por que é problema?**
- 📊 DataSUS disponibiliza muitos dados
- ❌ Mas gestores têm dificuldade em usá-los
- ⚡ Decisões são lentas (dias vs minutos)

### Coluna Direita (Tamanho 28pt)
**As 3 Barreiras:**

**1. Técnicas**
- Sistemas heterogêneos
- Precisa conhecer SQL
- Ferramentas caras

**2. Sociotécnicas**
- Curva de aprendizado alta
- Dependência de analistas
- Não é acessível

**3. Integração**
- Dados fragmentados
- Ex: Para "evitar sobrecarga de leitos" 🏥
  preciso correlacionar 4 sistemas diferentes

---

### Rodapé (Tamanho 32pt, Bold, Vermelho)
💡 Gestores têm dados, mas não conseguem usá-los de forma ágil

### Notas de Design SLIDE 1:
- Background: Branco
- Cor destaque: Vermelho #FF4444 ou Laranja #FF8800
- Use 2 colunas para organizar
- Ícones: Faticon (📊, ❌, ⚡, 🏥)
- Transição: Fade

---

# SLIDE 2: O OBJETIVO

## TÍTULO (48pt, Bold, Azul)
Democratizar Acesso a Dados de Saúde com IA

## SUBTÍTULO (32pt, Azul claro)
Uma ferramenta que entende português e integra múltiplas fontes

## CONTEÚDO - 4 CARDS (28pt cada)

### CARD 1 (Verde claro)
🔓 **SEM SQL**
Gestores fazem perguntas
em português natural

### CARD 2 (Verde médio)
🔗 **INTEROPERABILIDADE**
Sistema correlaciona
dados de múltiplas
fontes automaticamente

### CARD 3 (Verde escuro)
💡 **INTERPRETAÇÃO**
Não só números brutos,
mas explicação em
contexto de saúde

### CARD 4 (Verde muito escuro)
🤖 **MÚLTIPLOS MODELOS**
Comparar Llama 2,
Mistral, Neural Chat
para achar o melhor

## CONTEXTO ESTRATÉGICO (Rodapé, 24pt, Itálico)
📌 Validado em torno de objetivo real:
"Evitar sobrecarga de ocupação de leitos hospitalares"

### Notas de Design SLIDE 2:
- Background: Branco
- Cores: 4 tons de verde em progressão
- Layout: 4 cards lado a lado (ou 2x2 em tela menor)
- Cada card tem ícone grande (48pt)
- Transição: Fade ou Push from left
- Animação (opcional): Cards aparecem um por um

---

# SLIDE 3: O MÉTODO

## TÍTULO (48pt, Bold, Roxo)
Abordagem Técnica: 4 Etapas + Componentes

## SEÇÃO A: FLUXO (Centro, com setas)

```
PERGUNTA DO GESTOR (28pt)
"Qual a cobertura de vacinação 
em dezembro de 2024?"

          ⬇️ (seta grande, 40pt)

1️⃣ INTERPRETAÇÃO (28pt, roxo claro)
LLM extrai:
• Métrica: cobertura
• Período: dez/2024
• Tabela: vacinacao

          ⬇️

2️⃣ GERAÇÃO SQL (28pt)
SELECT cobertura FROM vacinacao
WHERE data LIKE '2024-12%'

          ⬇️

3️⃣ EXECUÇÃO (28pt)
ClickHouse
✓ Resultado: 87.3%

          ⬇️

4️⃣ INTERPRETAÇÃO DE RESULTADO ⭐ (28pt, roxo escuro)
"Cobertura foi 87.3%, acima da
meta de 85% recomendada"

DIFERENCIAL: Não é só SQL,
é SQL + CONTEXTO
```

## SEÇÃO B: TABELA TÉCNICA (Abaixo, 22pt)

| Componente | Tecnologia | Por quê |
|-----------|-----------|--------|
| **Linguagem Natural** | Ollama + Llama 2 (7B) | Local, sem cloud |
| **BD Analítica** | ClickHouse | Otimizado para queries |
| **API** | FastAPI | Rápida + docs automáticas |
| **Metadados** | JSON | Semântica comum |

## SEÇÃO C: DADOS (Rodapé)

💉 **Vacinação COVID** (5.847 registros)
🏥 **Leitos Hospitalares** (2.156 registros)
🦠 **Surtos de Doenças** (1.342 registros)
👨‍⚕️ **Atenção Básica** (3.521 registros)

**Avaliação: 68 questões (14 com integração multi-dataset)**

### Notas de Design SLIDE 3:
- Background: Branco
- Cor destaque: Roxo #8844BB
- Seção A: Grande, com setas animadas (passo a passo)
- Seção B: Tabela com linhas alternadas (branco/cinza claro)
- Seção C: Ícones grandes + números em negrito
- Transição: Fade
- Animação (opcional): Setas aparecem uma por uma no fluxo

---

# SLIDE 4: RESULTADOS ESPERADOS

## TÍTULO (48pt, Bold, Verde)
Contribuições & Impacto

## CONTEÚDO - 4 DIMENSÕES

### Dimensão 1 (Verde claro, 26pt)
📚 **CIENTÍFICA**
✓ Primeira avaliação multi-modelo
  em saúde pública BR
✓ Interoperabilidade demonstrada
✓ Publicações em periódicos
  de Informática em Saúde

### Dimensão 2 (Verde médio, 26pt)
🔧 **TÉCNICA**
✓ Sistema funcional e open-source
✓ Integração automática de fontes
✓ Explicações contextualizadas

### Dimensão 3 (Verde escuro, 26pt)
💼 **PRÁTICA**
✓ Tempo: Dias → Minutos
✓ Acesso: Técnicos → Gestores
✓ Decisões estratégicas ágeis

### Dimensão 4 (Laranja, 26pt) - LIMITAÇÕES
⚠️ **TRANSPARÊNCIA**
• 68 questões (expandível)
• 4 datasets (expansível)
• Painel pequeno (primeiros passos)
• Próximos: validação com gestores reais

## EXEMPLO PRÁTICO (Centro, 24pt, em caixa)

### 📊 Situação Real:
Gestor pergunta: "Qual a relação entre cobertura
de vacinação (dez/24) e ocupação de leitos (jan/25)?"

### ⚙️ O que o sistema faz:
1. Correlaciona 2 datasets diferentes
2. Gera queries otimizadas
3. Executa análise
4. Retorna em português contextualizado

### ⚡ Resultado:
**Segundos vs. dias**
**Sem SQL vs. com especialista**
**Decisão informada, rápida**

## PRÓXIMOS PASSOS (Rodapé, 22pt)
1️⃣ Divulgação científica (artigos)
2️⃣ Validação em campo com secretarias reais
3️⃣ Integração com Portal de Dados Abertos

### Notas de Design SLIDE 4:
- Background: Branco
- Cores: 4 tons de verde + laranja para destaque
- Layout: 4 caixas lado a lado (ou 2x2)
- Caixa do Exemplo: Com borda cinza, fundo cinza muito claro
- Ícones grandes: 40-48pt
- Transição: Fade
- Animação (opcional): Boxes aparecem um por um

---

# INSTRUÇÕES FINAIS DE IMPLEMENTAÇÃO

## 1. Google Slides
- Crie nova apresentação
- Para cada slide, use "Layouts" > "Blank"
- Adicione caixas de texto manualmente
- Adicione cores: Menu > Inserir > Forma
- Adicione ícones: Menu > Inserir > Ícone (procure por "chart", "settings", etc)

## 2. PowerPoint
- Novo > Apresentação em Branco
- Cada slide: Design > Tema (escolha um simples)
- Adicione caixas/formas: Home > Shapes
- Cores: botão direito > Fill > Solid color

## 3. Alternativa: Marp (se souber Markdown)
```markdown
---
marp: true
theme: gaia
---

# Slide 1: Problema
...
```

## Paleta de Cores Recomendada

| Uso | Cor | Código Hex |
|-----|-----|-----------|
| Problema (Vermelho) | 🔴 | #FF4444 |
| Objetivo (Azul) | 🔵 | #4488FF |
| Método (Roxo) | 🟣 | #8844BB |
| Resultados (Verde) | 🟢 | #44BB44 |
| Destaque Laranja | 🟠 | #FF8800 |
| Texto Preto | ⚫ | #222222 |
| Fundo Branco | ⚪ | #FFFFFF |
| Cinza Claro | ⚪ | #F5F5F5 |

## Fontes Recomendadas
- **Títulos**: Arial Bold, Segoe UI Bold, Helvetica Bold
- **Conteúdo**: Arial, Segoe UI, Helvetica
- **Tamanhos**:
  - Slide Title: 48pt Bold
  - Subtitles: 36-40pt
  - Main Content: 28pt
  - Small Content: 22-24pt
  - Notes: 16pt

## Ícones Sugeridos (Use Flaticon ou FontAwesome)
- 📊 Dados
- ❌ Problema/Barreira
- ✓ Solução
- 🔓 Acesso aberto
- 🔗 Integração
- 💡 Ideia
- 🤖 IA
- 🏥 Hospital/Saúde
- 💉 Vacinação
- 🦠 Doença
- ⚡ Velocidade/Energia
- 📚 Ciência
- 🔧 Técnica
- 💼 Prática
- ⚠️ Aviso/Limitação

---

## Timing com Timer

Se apresentar com cronômetro:

| Slide | Tempo | Tempo Acumulado |
|-------|-------|----------|
| Abertura | 0:30 | 0:30 |
| Slide 1 | 2:30 | 3:00 |
| Slide 2 | 2:30 | 5:30 |
| Slide 3 | 4:00 | 9:30 |
| Slide 4 | 2:30 | 12:00 |
| Encerramento | 0:30 | 12:30 |
| **Perguntas** | **2:30** | **15:00** |

**Alarme mental:**
- 3:00 → deve estar no final do Slide 1
- 5:30 → deve estar no final do Slide 2
- 9:30 → deve estar no final do Slide 3
- 12:00 → deve estar encerrando Slide 4

---

## Checklist Final Antes de Apresentar

- [ ] Todos os 4 slides prontos
- [ ] Cores testadas (veem bem em projetor?)
- [ ] Fontes legíveis em distância
- [ ] Imagens comprimidas (não deixar arquivo pesado)
- [ ] Clicker funcionando
- [ ] Backup em pen drive
- [ ] Speaker notes impressas ou em tablet
- [ ] Roupa confortável
- [ ] Água disponível
- [ ] Respirar fundo 5 minutos antes
- [ ] Chegar 10 minutos antes para testar projetor

**Boa apresentação! 🎤**

