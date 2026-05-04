# Guia de Design Visual para os 4 Slides

## SLIDE 1: PROBLEMA

### Design Sugerido
- **Fundo**: Branco ou cinza claro
- **Cor Destaque**: Vermelho/Laranja (para indicar "problema")
- **Fonte**: Sans-serif (Arial, Helvetica, Segoe UI)

### Layout
```
┌─────────────────────────────────────────────┐
│  A Lacuna no Acesso a Dados de Saúde      │
│  (Título em grande, vermelho)              │
├─────────────────────────────────────────────┤
│                                             │
│  [SEÇÃO ESQUERDA]         [SEÇÃO DIREITA] │
│  • DataSUS tem dados      • Gestores       │
│  • Mas não conseguem        querem usar    │
│    usar effectively        • Precisam de:  │
│                              - SQL?        │
│  Por que?                    - Especialistas│
│  ❌ Técnico demais         - Integração    │
│  ❌ Fragmentado            de múltiplas    │
│  ❌ Caro                      fontes        │
│                                             │
├─────────────────────────────────────────────┤
│  Impacto: Decisões estratégicas lentas     │
│  (pequeno em baixo, em vermelho)           │
└─────────────────────────────────────────────┘
```

### Elementos Visuais
- **Ícones**: 📊 (dados), 🚫 (barreira), 👤 (gestor), ⚡ (velocidade)
- **Gráfico**: Simples mostrando "Dados Disponíveis vs. Dados Utilizados" (proporção)

---

## SLIDE 2: OBJETIVO

### Design Sugerido
- **Fundo**: Branco ou azul claro
- **Cor Destaque**: Azul/Verde (para indicar "solução/objetivo")
- **Fonte**: Mesma que Slide 1

### Layout
```
┌─────────────────────────────────────────────┐
│  Democratizar Acesso a Dados de Saúde     │
│  com Inteligência Artificial               │
│  (Título em grande, azul)                  │
├─────────────────────────────────────────────┤
│                                             │
│  OBJETIVO GERAL:                           │
│  "LLM que permite perguntas em             │
│   português → respostas inteligentes"      │
│                                             │
│  4 PILARES (4 colunas ou cards):           │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐     │
│  │ Sem  │ │Inter-│ │Inter-│ │Compa-│     │
│  │ SQL  │ │opera-│ │preta-│ │ração │     │
│  │      │ │bili-│ │ção   │ │      │     │
│  │🔓    │ │dade  │ │de    │ │de    │     │
│  │      │ │🔗    │ │resu- │ │Models│     │
│  │      │ │      │ │ltados│ │🤖    │     │
│  └──────┘ └──────┘ └──────┘ └──────┘     │
│                                             │
│  CONTEXTO: Objetivo estratégico             │
│  "Evitar sobrecarga de leitos"            │
│                                             │
└─────────────────────────────────────────────┘
```

### Elementos Visuais
- **Cards coloridos** para cada objetivo (cada um cor diferente)
- **Ícones**: 🔓 (democratização), 🔗 (integração), 💡 (interpretação), 🤖 (IA)
- **Destaque**: Underline verde no "Diferencial vs. ferramentas tradicionais"

---

## SLIDE 3: MÉTODO

### Design Sugerido
- **Fundo**: Branco (muito conteúdo técnico, precisa clareza)
- **Cor Destaque**: Roxo/Violeta (para indicar "processo")
- **Fonte**: Mesma

### Layout A: FLUXO (OPÇÃO 1 - Mais Dinâmico)
```
┌─────────────────────────────────────────────┐
│  Abordagem Técnica: 4 Etapas               │
├─────────────────────────────────────────────┤
│                                             │
│  "Qual a cobertura de vacinação"          │
│   em dezembro de 2024?"                    │
│  (Pergunta do gestor em PT-BR)             │
│           ▼                                 │
│   ┌──────────────────┐                     │
│   │1️⃣ INTERPRETAÇÃO │                      │
│   │ LLM extrai:      │                     │
│   │ • Métrica: cobertura                  │
│   │ • Período: dez/24                     │
│   │ • Tabela: vacinacao                   │
│   └────────┬─────────┘                     │
│            ▼                                │
│   ┌──────────────────┐                     │
│   │2️⃣ GERAÇÃO SQL   │                      │
│   │SELECT cobertura  │                     │
│   │FROM vacinacao    │                     │
│   │WHERE data LIKE   │                     │
│   │'2024-12%'        │                     │
│   └────────┬─────────┘                     │
│            ▼                                │
│   ┌──────────────────┐                     │
│   │3️⃣ EXECUÇÃO      │                      │
│   │ClickHouse        │                     │
│   │ ✓ Resultado:     │                     │
│   │   87.3%          │                     │
│   └────────┬─────────┘                     │
│            ▼                                │
│   ┌──────────────────┐                     │
│   │4️⃣ INTERPRETAÇÃO │                      │
│   │RESULTADO ⭐     │                      │
│   │ "Cobertura foi   │                     │
│   │ de 87.3%, acima  │                     │
│   │ da meta de 85%"  │                     │
│   └──────────────────┘                     │
│                                             │
│  Diferencial: Não é só SQL gerado,        │
│  mas também resultado EXPLICADO            │
│                                             │
└─────────────────────────────────────────────┘
```

### Layout B: TABELA TÉCNICA (OPÇÃO 2 - Mais Formal)
```
┌─────────────────────────────────────────────┐
│  Componentes Técnicos                      │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │ Componente  │ Tecnologia │ Por quê?  │  │
│  ├──────────────────────────────────────┤  │
│  │ Linguagem   │ Ollama +   │ Local,    │  │
│  │             │ Llama 2    │ sem      │  │
│  │             │ (7B)       │ cloud    │  │
│  ├──────────────────────────────────────┤  │
│  │ Comparação  │ Mistral +  │ Testar   │  │
│  │ de Models   │ Neural     │ veloci-  │  │
│  │             │ Chat (7B)  │ dade vs. │  │
│  │             │            │ qualidade│  │
│  ├──────────────────────────────────────┤  │
│  │ BD Analítica│ ClickHouse │ Otimi-   │  │
│  │             │            │ zado para│  │
│  │             │            │ queries  │  │
│  ├──────────────────────────────────────┤  │
│  │ API         │ FastAPI    │ Perfor-  │  │
│  │             │            │ mance +  │  │
│  │             │            │ docs     │  │
│  └──────────────────────────────────────┘  │
│                                             │
│  DADOS: 4 Datasets de Domínios Diferentes  │
│  💉 Vacinação | 🏥 Leitos | 🦠 Surtos    │
│  👨‍⚕️ Atenção Básica                       │
│                                             │
│  AVALIAÇÃO: 68 Questões (14 com           │
│  integração entre datasets)                │
│                                             │
└─────────────────────────────────────────────┘
```

### Recomendação
**Use Layout A** (Fluxo) - visualmente mais claro e memorável. O Layout B pode ser um slide adicional se tiver espaço.

---

## SLIDE 4: RESULTADOS ESPERADOS

### Design Sugerido
- **Fundo**: Branco
- **Cor Destaque**: Verde (para indicar "resultado/sucesso")
- **Fonte**: Mesma

### Layout
```
┌─────────────────────────────────────────────┐
│  Contribuições & Impacto                   │
├─────────────────────────────────────────────┤
│                                             │
│  4 DIMENSÕES:                              │
│                                             │
│  1️⃣ CIENTÍFICA (Verde claro)              │
│    ✓ Primeira avaliação de múltiplos       │
│      LLMs em saúde pública BR              │
│    ✓ Interoperabilidade demonstrada        │
│    ✓ Publicações em periódicos de          │
│      Informática em Saúde                  │
│                                             │
│  2️⃣ TÉCNICA (Verde)                       │
│    ✓ Sistema funcional e open-source       │
│    ✓ Integração automática de fontes       │
│    ✓ Explicações contextualizadas          │
│                                             │
│  3️⃣ PRÁTICA (Verde escuro)                │
│    ✓ Tempo: Dias → Minutos                │
│    ✓ Acesso: Técnicos → Gestores          │
│    ✓ Decisões mais ágeis                   │
│                                             │
│  📊 EXEMPLO REAL:                          │
│  "Qual relação entre vacinação             │
│   e ocupação de leitos?"                   │
│  → Correlação automática de 2 datasets     │
│  → Resposta em português contextualizado   │
│  → Decisão em minutos                      │
│                                             │
│  4️⃣ TRANSPARÊNCIA (Laranja - limitações) │
│    • 68 questões (expandível)              │
│    • 4 datasets (expansível)               │
│    • Painel pequeno de validação           │
│    • Próximos passos: validação com       │
│      gestores reais                        │
│                                             │
└─────────────────────────────────────────────┘
```

### Elementos Visuais
- **Ícones**: 📚 (científica), 🔧 (técnica), 💼 (prática), ⚠️ (transparência)
- **Cores diferentes** para cada dimensão (verde em tons diferentes)
- **Caixa destacada** para o exemplo real
- **Caixa de "limitações"** em laranja (mostra honestidade acadêmica)

---

## DICAS GERAIS

### Para PowerPoint/Google Slides
1. **Paleta de cores**: Azul, Verde, Vermelho, Roxo + Branco/Cinza
2. **Fontes**: 
   - Títulos: 44-48pt, Bold
   - Conteúdo: 24-28pt, Regular
   - Notas: 16-20pt
3. **Espaçamento**: Generoso (não preencha tudo, deixe respirar)
4. **Imagens**: 
   - Ícones (Flaticon, Font Awesome)
   - Gráficos simples (Slide 1: pizza ou barras comparando disponibilidade vs. uso)
   - Diagrama de fluxo (Slide 3)

### Transições
- **Simples**: Fade ou Push
- **Não use**: Spinning, zooming excessivo (distrai)

### Animações
- **Bullets**: Aparecem um a um (left click)
- **Diagrama Slide 3**: Cada seta pode revelar passo a passo
- **Não exagere**: 1-2 animações por slide no máximo

### Última Dica
**Pratique a apresentação!** Com animações/transições suave, o timing fica 12-15 minutos, perfeito para apresentação + perguntas em 30 minutos.

---

## ADAPTAÇÃO PARA DIFERENTES PÚBLICOS

### Se apresentar para Grupo Técnico:
- Aumentar detalhes do Slide 3
- Mencionar benchmarks acadêmicos
- Adicionar gráficos de performance

### Se apresentar para Gestores/Administrativo:
- Reduzir Slide 3 (detalhes técnicos)
- Aumentar foco em Slide 1 (problema real) e Slide 4 (impacto prático)
- Usar mais exemplos do mundo real

### Público Misto (como será provavelmente):
- **Use os 4 slides como está** (bom equilíbrio)
- Prepare notas extras para perguntas técnicas
- Esteja pronto para "simplificar" explanações técnicas se necessário

