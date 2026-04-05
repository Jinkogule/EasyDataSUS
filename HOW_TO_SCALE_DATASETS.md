# 📈 Como Adicionar Novos Datasets - Guia Completo

## Visão Geral

**Pergunta**: Basta criar pasta + schema.json + CSV que funciona?
**Resposta**: ❌ **Não completamente.** A estrutura de pasta é automática, mas há **3 lugares no código** que precisam de atualizações.

---

## 6 Passos Para Escalar (Usando `internacao-uti` como exemplo)

### 1️⃣ Criar Pastas [AUTOMÁTICO ✅]

```bash
# Pasta de metadados (schema)
mkdir -p backend/metadata/datasets/internacao-uti

# Pasta de dados (CSV)
mkdir -p backend/data/datasets/internacao-uti
```

### 2️⃣ Criar Schema [ARQUIVO]

**Arquivo**: `backend/metadata/datasets/internacao-uti/schema.json`

```json
{
  "table_name": "internacao_uti",
  "description": "Dados de internação em UTI no Brasil",
  "columns": [
    {
      "name": "estado",
      "type": "String",
      "description": "Estado (AC, ES, RJ, SP...)"
    },
    {
      "name": "cidade",
      "type": "String",
      "description": "Cidade"
    },
    {
      "name": "data",
      "type": "Date",
      "description": "Data da internação"
    },
    {
      "name": "total_internacoes",
      "type": "Int64",
      "description": "Total de internações em UTI"
    },
    {
      "name": "leitos_disponiveis",
      "type": "Int64",
      "description": "Leitos UTI disponíveis"
    }
  ]
}
```

### 3️⃣ Colocar CSV [ARQUIVO]

**Arquivo**: `backend/data/datasets/internacao-uti/internacao-ac-es.csv`

```csv
estado,cidade,data,total_internacoes,leitos_disponiveis
AC,Rio Branco,2024-01-01,150,45
AC,Cruzeiro do Sul,2024-01-01,30,10
ES,Vitória,2024-01-01,200,60
RJ,Rio de Janeiro,2024-01-01,450,120
SP,São Paulo,2024-01-01,800,200
```

> **Nota**: O ETL detecta automaticamente! Só colocar em `data/datasets/internacao-uti/` que carrega.

### 4️⃣ Adicionar Perguntas Pré-Prontas [CÓDIGO]

**Arquivo**: `backend/routes/questions.py` (Linha ~15)

Procure por:
```python
PREBUILT_QUESTIONS = {
    "vacinacao-covid": { ... },
    "dengue-2024": { ... },
    "influenza-2025": { ... }
}
```

Adicione antes da última chave:
```python
PREBUILT_QUESTIONS = {
    "vacinacao-covid": { ... },
    "dengue-2024": { ... },
    "influenza-2025": { ... },
    
    # 🏥 NOVO DATASET
    "internacao-uti": {
        "theme_color": "🏥",
        "theme_name": "Internação UTI",
        "description": "Dados de internação em Unidades de Terapia Intensiva",
        "questions": [
            {
                "id": "uti-001",
                "theme": "Quantidade Total",
                "question": "Quantas internações em UTI foram registradas?",
                "description": "Total de pacientes internados em UTI",
                "category": "statistics"
            },
            {
                "id": "uti-002",
                "theme": "Por Estado",
                "question": "Qual estado teve mais internações em UTI?",
                "description": "Estado com maior número de internações",
                "category": "regional"
            },
            {
                "id": "uti-003",
                "theme": "Disponibilidade",
                "question": "Quantos leitos de UTI estão disponíveis?",
                "description": "Total de leitos UTI ainda disponíveis",
                "category": "availability"
            },
            {
                "id": "uti-004",
                "theme": "Por Estado",
                "question": "Quantas internações em UTI em SP?",
                "description": "Total de internações em São Paulo",
                "category": "regional"
            },
            {
                "id": "uti-005",
                "theme": "Taxa de Ocupação",
                "question": "Qual é a taxa de ocupação de leitos de UTI?",
                "description": "Percentual de leitos UTI ocupados",
                "category": "occupancy"
            }
        ]
    }
}
```

### 5️⃣ Mapear Dataset → Tabela [CÓDIGO]

**Arquivo**: `backend/routes/query.py` (Linha ~88, dentro da função `is_valid_sql`)

Procure por:
```python
dataset_table_map = {
    "vacinacao-covid": "vacinacao",
    "dengue-2024": "dengue",
    "influenza-2025": "influenza"
}
```

Adicione:
```python
dataset_table_map = {
    "vacinacao-covid": "vacinacao",
    "dengue-2024": "dengue",
    "influenza-2025": "influenza",
    "internacao-uti": "internacao_uti"  # ← NOVO
}
```

> **Por quê?** O LLM gera SQL, mas passa a validar se a tabela referenciada está correta para o dataset.

### 6️⃣ Adicionar Keywords de Detecção [CÓDIGO]

**Arquivo**: `backend/routes/query.py` (Linha ~268, função `_detect_dataset_for_question`)

Procure por:
```python
keywords_map = {
    "vacinacao-covid": [
        "vacina", "vacinação", "covid", "doses", ...
    ],
    "dengue-2024": [
        "dengue", "aedes", "mosquito", ...
    ],
    "influenza-2025": [
        "influenza", "gripe", "h1n1", ...
    ]
}
```

Adicione:
```python
keywords_map = {
    "vacinacao-covid": [
        "vacina", "vacinação", "covid", "doses", ...
    ],
    "dengue-2024": [
        "dengue", "aedes", "mosquito", ...
    ],
    "influenza-2025": [
        "influenza", "gripe", "h1n1", ...
    ],
    
    # 🏥 NOVO DATASET
    "internacao-uti": [
        "uti", "internação", "internacao", "leito", "cuidado intensivo",
        "crítico", "terapia intensiva", "paciente crítico", "hospital"
    ]
}
```

> **Por quê?** Para quando o usuário faz pergunta customizada ("Internações críticas?"), o sistema detecta automaticamente qual dataset usar.

---

## Checklist Completo

| Passo | Tipo | Arquivo | O quê | ✅ |
|-------|------|---------|-------|-----|
| 1 | Pasta | `metadata/datasets/internacao-uti/` | Criar pasta | ✅ |
| 2 | Arquivo | `schema.json` em metadata | Copiar do template e adaptar | ✅ |
| 3 | Pasta | `data/datasets/internacao-uti/` | Criar pasta | ✅ |
| 4 | Arquivo | `*.csv` em data | Colocar CSV com dados | ✅ |
| 5 | Código | `routes/questions.py` | Adicionar ao dicionário (5+ perguntas) | ✅ |
| 6 | Código | `routes/query.py` line 88 | Mapear dataset → tabela | ✅ |
| 7 | Código | `routes/query.py` line 268 | Adicionar keywords detecção | ✅ |

---

## O Sistema Automaticamente Detecta

✅ **Carregamento de CSV**: ETL procura por `data/datasets/{dataset}/` e carrega automaticamente
✅ **Schema JSON**: `metadata/loader.py` busca em `metadata/datasets/{dataset}/schema.json`
✅ **Endpoints /api/questions**: Carrega automaticamente do dicionário `PREBUILT_QUESTIONS`
✅ **Roteamento**: Detecta dataset pela pergunta usando keywords

---

## Para Fazer Rapidinho

### Template para Copiar/Colar

**schema.json:**
```json
{
  "table_name": "NOME_TABELA",
  "description": "DESCRIÇÃO",
  "columns": [
    {"name": "estado", "type": "String"},
    {"name": "total_casos", "type": "Int64"}
  ]
}
```

**routes/questions.py** - Adicione:
```python
"novo-dataset": {
    "theme_color": "🆕",
    "theme_name": "Nome Dataset",
    "description": "Descrição",
    "questions": [
        {
            "id": "new-001",
            "theme": "Categoria",
            "question": "Sua pergunta aqui?",
            "description": "...",
            "category": "category_name"
        }
    ]
}
```

**routes/query.py** - Dataset map (linha 88):
```python
"novo-dataset": "nome_tabela"
```

**routes/query.py** - Keywords (linha 268):
```python
"novo-dataset": ["keyword1", "keyword2", "keyword3"]
```

---

## Exemplo Prático Rápido

Para adicionar **"cancer-2024"**:

```bash
# 1. Criar pastas
mkdir -p backend/metadata/datasets/cancer-2024
mkdir -p backend/data/datasets/cancer-2024

# 2. Copiar schema.json (adaptar nomes)
# 3. Copiar CSV para data/datasets/cancer-2024/

# 4. Editar routes/questions.py (adicionar 5 perguntas)
# 5. Editar routes/query.py linha 88 (mapear "cancer-2024" → "cancer_cases")
# 6. Editar routes/query.py linha 268 (adicionar keywords)
```

Pronto! Sistema já funciona! 🚀

---

## Então, Resumindo Sua Pergunta

**"Basta criar pasta + schema.json + CSV?"**

❌ **Oficialmente não**, porque:
- **Arquivos**: Sim, pasta + schema + CSV é automático
- **Código**: Precisa adicionar 3 lugares (questions.py + 2x query.py)

**Mas...** Se você colocar só pasta + CSV + schema, o sistema não vai quebrar. Só a pergunta não vai aparecer em `/api/questions` e a detecção automática não funcionará. O backend carregará o CSV corretamente, mas falta a inteligência de roteamento.

**Recomendação**: Automatizar os 3 passos de código é para quando tiver muitos datasets. Para 3-5 datasets, editar manualmente os dicionários é mais rápido e mais seguro.
