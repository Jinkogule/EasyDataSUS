# Apresentação: EasyDataSUS - Ferramenta de Acesso Inteligente a Dados de Saúde Pública

## SLIDE 1: PROBLEMA

### Título
**A Lacuna no Acesso a Dados Públicos de Saúde**

### Conteúdo Principal (Bullets)
- **Paradoxo dos Dados Abertos**: DataSUS disponibiliza enormes volumes de dados, mas sua utilização por gestores é limitada
  
- **Barreiras Técnicas**:
  - Heterogeneidade de formatos e sistemas (vacinação, leitos, vigilância epidemiológica)
  - Necessidade de conhecimento em SQL e análise de dados
  - Ferramentas de BI sofisticadas e caras

- **Barreiras Sociotécnicas**:
  - Curva de aprendizado elevada para gestores
  - Dependência de analistas especializados
  - Documentação inadequada das bases

- **Barreira de Integração**:
  - Dados relevantes para um objetivo estratégico estão espalhados em múltiplos sistemas
  - Ex: Para "evitar sobrecarga de leitos" é preciso correlacionar: leitos, surtos de doenças, vacinação, atenção básica

### Impacto
*Gestores não conseguem acessar dados de forma ágil para apoiar decisões estratégicas em saúde pública*

---

## SLIDE 2: OBJETIVO

### Título
**Democratizar o Acesso a Dados de Saúde com Inteligência Artificial**

### Objetivo Geral
Desenvolver e avaliar uma **ferramenta baseada em modelos de linguagem** que permita gestores formularem perguntas em linguagem natural sobre dados públicos de saúde, **integrando múltiplos domínios** e retornando respostas contextualizadas.

### Objetivos Específicos

1. **Reduzir Barreiras Técnicas**
   - Permitir consultas sem conhecimento de SQL
   - Interface amigável em linguagem natural

2. **Integração de Múltiplos Domínios** ⭐ (Diferencial)
   - Correlacionar dados de vacinação, leitos, surtos, atenção básica
   - Suportar análises que conectam múltiplas fontes

3. **Interpretação Inteligente** ⭐ (Diferencial vs. ferramentas tradicionais)
   - LLM não apenas traduz pergunta para SQL
   - Interpreta resultados em linguagem natural, contextualizada em saúde pública

4. **Comparar Modelos de IA**
   - Avaliar diferentes LLMs (Llama 2, Mistral, Neural Chat)
   - Identificar qual é mais apropriado para dados de saúde

### Contexto Estratégico
*Usar objetivo estratégico "evitar sobrecarga de ocupação de leitos" como caso de uso concreto*

---

## SLIDE 3: MÉTODO

### Título
**Abordagem Técnica: Arquitetura e Componentes**

### Arquitetura em 4 Etapas

```
┌─────────────────────┐
│   Pergunta do       │
│   Gestor (PT-BR)    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────────────────┐
│ 1. INTERPRETAÇÃO                │
│ LLM: "O que o gestor quer?"     │
│ → Intenção, entidades, filtros  │
└──────────┬──────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ 2. GERAÇÃO SQL                  │
│ "Quais tabelas? Qual JOIN?"     │
│ → Consulta SQL otimizada        │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ 3. EXECUÇÃO                     │
│ Banco: ClickHouse               │
│ → Dados brutos obtidos          │
└──────────┬───────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│ 4. INTERPRETAÇÃO DE RESULTADOS ⭐  │
│ LLM: "O que esses números       │
│ significam em saúde pública?"    │
│ → Resposta contextualizada      │
└─────────────────────────────────────┘
```

### Componentes Técnicos

| Componente | Tecnologia | Justificativa |
|-----------|-----------|--------------|
| **Modelo de Linguagem** | Ollama + Llama 2/Mistral/Neural Chat (7B) | Execução local, sem dependência cloud, múltiplos modelos para comparação |
| **Banco de Dados** | ClickHouse | Otimizado para queries analíticas, performance em múltiplas agregações |
| **API** | FastAPI | Performance, documentação automática (Swagger) |
| **Metadados** | JSON | Semântica comum entre datasets, facilita compreensão do LLM |

### Dados Utilizados (4 Datasets)

1. **Vacinação COVID-19** (5.847 registros) - Domínio: Imunização
2. **Leitos Hospitalares** (2.156 registros) - Domínio: Gestão Assistencial
3. **Surtos de Doenças** (1.342 registros) - Domínio: Vigilância Epidemiológica
4. **Cobertura Atenção Básica** (3.521 registros) - Domínio: Atenção Primária

**Estratégia**: Múltiplos domínios permitem testar integração (ex: picos de surtos vs. ocupação de leitos)

### Avaliação (68 Questões)

- **30 questões simples** (1-2 cláusulas SQL)
- **38 questões moderadas/complexas** (3+ cláusulas)
  - **14 com foco em interoperabilidade** (joins entre múltiplos datasets)
- Cada questão avaliada em: Precisão, Tempo de Resposta, Clareza, Robustez, Integração

---

## SLIDE 4: RESULTADOS ESPERADOS

### Título
**Contribuições Esperadas e Impacto**

### 1. Científicas

**Primeira Avaliação Sistemática de:**
- ✅ Comparação de múltiplos modelos LLM em contexto de saúde pública brasileira
- ✅ Capacidade de integração de múltiplos datasets heterogêneos via linguagem natural
- ✅ Interpretação contextualizada de resultados (não apenas geração de SQL)

**Publicáveis em:**
- Periódicos de Informática em Saúde
- Conferências de IA + Saúde Pública

### 2. Técnicas

**Sistema Funcional Demonstrando:**
- Interface amigável para acesso a dados complexos
- Integração automática de múltiplas fontes
- Explicações contextualizadas para não-técnicos

**Código Open-Source** disponível para comunidade

### 3. Práticas

**Impacto Esperado:**
- Redução de tempo de análise (de dias → minutos)
- Democratização: Gestores sem conhecimento técnico podem explorar dados
- Decisões estratégicas mais ágeis em saúde pública

**Exemplo Concreto:**
*Gestor pergunta: "Qual a relação entre cobertura de vacinação em dezembro de 2024 e a ocupação de leitos em janeiro de 2025?"*
- Sistema correlaciona 2 datasets
- Retorna dados + interpretação contextualizada em saúde pública
- Gestor toma decisão em minutos, não dias

### 4. Viabilidade Técnica

**Comprovará:**
- LLMs são viáveis para consulta a dados de saúde pública
- Múltiplos modelos podem funcionar localmente (sem dependência cloud/API paga)
- Interoperabilidade é alcançável via metadados estruturados

### 5. Limitações Reconhecidas (Transparência)

- Avaliação com 68 questões (mais representativa que antes, mas menor que benchmarks acadêmicos com 500+)
- Foco em 4 datasets (expansão futura para outros domínios)
- Comparação com outros modelos proprietários seria desejável (mas custos impedem)
- Validação com painel pequeno de gestores (3 pessoas)

### Próximos Passos

1. **Curto prazo**: Finalizar avaliação, preparar publicação
2. **Médio prazo**: Validação com gestores reais de secretarias de saúde
3. **Longo prazo**: Integração em plataformas oficiais de dados de saúde (Portal de Dados Abertos)

---

## NOTAS PARA APRESENTAÇÃO

### Tom
- **Científico mas acessível**: Não assumir que a audiência conhece LLM/Text-to-SQL em detalhe
- **Conectar com prática**: Sempre mencionar "como isso ajuda um gestor?"
- **Diferencial claro**: Destacar que não é apenas BI + SQL gerado, mas com interpretação inteligente

### Timing (estimado)
- **Slide 1 (Problema)**: 2-3 minutos
- **Slide 2 (Objetivo)**: 2-3 minutos
- **Slide 3 (Método)**: 3-4 minutos (mais técnico, pode ter perguntas)
- **Slide 4 (Resultados)**: 2-3 minutos

**Total**: ~12 minutos (deixando tempo para perguntas)

### Perguntas Antecipadas

**P1: "Como isso diferencia da outra ferramenta do grupo?"**
> R: Eles fazem interface amigável para dados. Nós vamos além: LLM interpreta resultados e correlaciona múltiplos datasets automaticamente. É uma camada de AI acima da interface.

**P2: "Por que LLM e não machine learning tradicional?"**
> R: LLM entende linguagem natural sem treinamento específico. Alternativas exigiriam dataset enorme de perguntas-exemplos de saúde pública (não temos). LLM generaliza melhor.

**P3: "Isso funciona em produção?"**
> R: Nesta fase é proof-of-concept. Funciona localmente. Próximo passo seria integração com APIs oficiais e validação com secretarias reais.

**P4: "E se o LLM gera SQL errado?"**
> R: Essa é a avaliação principal. Estamos medindo precisão em 68 cenários. Há fallbacks (validação de SQL) e possibilidade de iteração (usuário corrige pergunta).

