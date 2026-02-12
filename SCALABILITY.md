# 🔧 Análise de Escalabilidade e Roadmap de Implementação

## Pergunta Central
> "O projeto pode suportar múltiplos tipos de dados do DataSUS de forma genérica?"

**Resposta:** Parcialmente. Atual é **específico para vacinação**, mas **existe um caminho** para generalizar.

---

## 📊 Estado Atual: Específico para Vacinação

### ❌ Hardcoded para 32 colunas de vacinação

**`backend/etl/load_csv_v2.py` (linhas 80-135):**
```python
row = []
row.append(r.get("document_id") or "UNKNOWN")  # ← Coluna vacinação
row.append(r.get("paciente_id") or "UNKNOWN")  # ← Coluna vacinação
row.append(int(r["paciente_idade"]) if r.get("paciente_idade") else 0)  # ← Tipo Integer hardcoded
row.append(parse_date(r.get("paciente_dataNascimento"), allow_null=False)) # ← Data específica
# ... 28 mais colunas hardcoded
row.append(r.get("vacina_nome") or "")  # ← Coluna específica de vacinação
row.append(r.get("vacina_lote") or "")  # ← Coluna específica de vacinação
```

**Problema:** Se mudar dataset de vacinação para internações, cada coluna muda completamente.

### ❌ Schema em JSON é específico

**`backend/metadata/vacinacao.json`:**
```json
{
  "tabela": "vacinacao",
  "colunas": [
    {
      "nome": "paciente_endereco_uf",
      "tipo": "String",
      "exemplo": "SP",
      "descricao": "Estado do paciente"
    },
    {
      "nome": "vacina_dataAplicacao",
      "tipo": "Date",
      "exemplo": "2022-03-17",
      "descricao": "Data da aplicação da vacina"
    }
  ]
}
```

Para internações, seria completamente diferente (data admissão, motivo internação, diagnóstico, etc).

### ❌ Prompt LLM é específico para vacinação

**`backend/services/sql_service.py` (few-shot examples):**
```python
# Exemplos no prompt
"Pergunta: Quantas pessoas vacinadas em SP?",
"SQL: SELECT COUNT(DISTINCT paciente_id) FROM vacinacao WHERE paciente_endereco_uf='SP'",
"Pergunta: Qual é a vacina mais aplicada?",
"SQL: SELECT vacina_nome, COUNT(*) FROM vacinacao GROUP BY vacina_nome ORDER BY COUNT(*) DESC LIMIT 3"
```

Para internações, seria:
```python
"Pergunta: Quantas internações em 2024?",
"SQL: SELECT COUNT(*) FROM internacoes WHERE YEAR(data_internacao) = 2024",
```

---

## ⚠️ Limitações Conhecidas

| Aspecto | Limitação | Impacto | Esforço para Fix |
|--------|-----------|--------|-----------------|
| **CSV Parser** | Hardcoded 32 colunas de vacinação | Não funciona para internações/óbitos | Alto |
| **Metadata** | Schema único para vacinacao.json | Precisa de internacoes.json, obitos.json | Médio |
| **LLM Prompt** | Few-shot examples só de vacinação | Modelo não entende novo dataset | Médio |
| **ClickHouse** | Uma tabela por dataset | Precisa de ALTER TABLE ou nova tabela | Baixo |
| **Roteamento** | Sem sistema para escolher qual dataset | Sempre usa "vacinacao" | Médio |

---

## 🎯 O que Precisa Mudar para Generalizar

### Nível 1: Suporte Básico (1-2 dias)

**Meta:** Aceitar qualquer CSV com colunas em ordem diferente

**Mudanças:**
1. **ETL genérico baseado em schema**
   - Ler schema JSON
   - Usar schema para ordenar colunas
   - Tipo conversão automática (String, Integer, Date, Float)

2. **Metadata loader multi-dataset**
   - Carregar vacinacao.json, internacoes.json, obitos.json
   - Sistema de "dataset ativo" ou seleção por query

**Código necessário:**
```python
# backend/etl/generic_loader.py (NOVO)
def load_csv_generic(csv_path: str, schema_path: str):
    """Carrega CSV usando schema declarativo"""
    schema = load_json(schema_path)  # Lê internacoes.json
    
    with open(csv_path) as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            # Ordenar por schema, converter tipos
            values = [convert_type(row.get(col['nome']), col['tipo']) 
                     for col in schema['colunas']]
            insert_row(values)
```

**Resultado:** 
- ✅ Qualquer CSV com colunas em qualquer ordem
- ✅ Suporte a múltiplas tabelas
- ❌ Ainda precisa de schema JSON para cada dataset (manual)

### Nível 2: Multi-dataset Query (2-3 dias)

**Meta:** API saber qual dataset usar

**Mudanças:**
1. **Roteador de dataset**
   - Detectar dataset a partir da pergunta: "internações" → internacoes
   - Ou usuário especifica: `{"question": "...", "dataset": "internacoes"}`

2. **Prompt dinamicamente gerado**
   - Ler colunas do schema JSON
   - Gerar few-shot examples automaticamente

**Código necessário:**
```python
# backend/llm/dynamic_prompt.py (NOVO)
def generate_prompt(question: str, schema: dict):
    """Gera prompt customizado por dataset"""
    
    # Ler colunas disponíveis do schema
    columns_desc = "\n".join([
        f"- {col['nome']}: {col['descricao']}"
        for col in schema['colunas']
    ])
    
    # Gerar exemplos baseado em tipo de coluna
    examples = [
        generate_example_for_question(q, schema) 
        for q in ["Quantos registros?", "Qual é o X mais comum?"]
    ]
    
    return f"""Você trabalha com dados de {schema['nome_amigavel']}.
    
Colunas disponíveis:
{columns_desc}

Exemplos de SQL válido:
{examples}

PERGUNTA: {question}"""
```

**Resultado:**
- ✅ Suporte a múltiplos datasets
- ✅ LLM adapta-se automaticamente ao dataset
- ❌ Ainda precisa de schema JSON manual para cada dataset

### Nível 3: Auto-Schema Detection (1 semana+) 

**Meta:** Inferir schema do CSV automaticamente

**Mudanças:**
1. **Tipo detection automático**
   - Amostragem de colunas
   - Heurística: "se tudo é YYYY-MM-DD, é Date"
   - "se tem '-' ou '.', pode ser Float/Money"

2. **Descrição auto-gerada**
   - Usar LLM para gerar descrições: "paciente_endereco_uf" → "Estado de residência do paciente"

**Resultado:**
- ✅ Carregar novo CSV sem escrever schema
- ❌ Qualidade pode ser ruim
- ❌ LLM precisa entender contexto do domínio (saúde)

---

## 📋 Passo-a-Passo: Implementar Internações

Assumindo que você tem `internacoes-2024.csv`:

### Passo 1: Criar Schema JSON
**`backend/metadata/internacoes.json`** (15 minutos)
```json
{
  "nome_amigavel": "Internações Hospitalares",
  "tabela": "internacoes",
  "descricao": "Registros de internações hospitalares no SUS",
  "colunas": [
    {
      "nome": "id_admissao",
      "tipo": "String",
      "exemplo": "12345",
      "descricao": "ID único da admissão"
    },
    {
      "nome": "paciente_id",
      "tipo": "String",
      "exemplo": "74bc...",
      "descricao": "ID do paciente (hash)"
    },
    {
      "nome": "data_internacao",
      "tipo": "Date",
      "exemplo": "2024-01-15",
      "descricao": "Data e hora de admissão"
    },
    {
      "nome": "data_alta",
      "tipo": "Date",
      "exemplo": "2024-01-20",
      "descricao": "Data de alta ou transferência"
    },
    {
      "nome": "diagnóstico_principal",
      "tipo": "String",
      "exemplo": "COVID-19",
      "descricao": "Diagnóstico principal (CID-10)"
    },
    {
      "nome": "estabelecimento_uf",
      "tipo": "String",
      "exemplo": "SP",
      "descricao": "Estado do hospital"
    },
    {
      "nome": "tipo_internacao",
      "tipo": "String",
      "exemplo": "Clínica Médica",
      "descricao": "Tipo/especialidade de internação"
    },
    {
      "nome": "dias_internacao",
      "tipo": "Integer",
      "exemplo": "5",
      "descricao": "Número de dias internado"
    }
  ],
  "tabela_sql": "CREATE TABLE IF NOT EXISTS internacoes ..."
}
```

### Passo 2: Criar Tabela no ClickHouse
**Adicionar a `backend/db/init.sql`** (10 minutos)
```sql
CREATE TABLE IF NOT EXISTS internacoes (
    id_admissao String,
    paciente_id String,
    data_internacao Date,
    data_alta Date,
    diagnóstico_principal String,
    estabelecimento_uf String,
    tipo_internacao String,
    dias_internacao Integer
) ENGINE = MergeTree()
ORDER BY (estabelecimento_uf, data_internacao);
```

### Passo 3: Adaptar ETL
**Opção A: Manter separado** (1 hora)
```python
# backend/etl/load_internacoes.py
def load_internacoes_csv(csv_path: str):
    schema = load_json("metadata/internacoes.json")
    # Mesmo padrão que load_csv_v2.py, mas para internações
    ...
```

**Opção B: ETL genérico** (2 horas - melhor long-term)
```python
# backend/etl/generic_loader.py (NOVO)
def load_from_schema(csv_path: str, schema_path: str):
    """Carrega qualquer CSV baseado em schema JSON"""
    schema = load_json(schema_path)
    rows = []
    
    with open(csv_path, encoding='utf-8') as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            # Extrair valores conforme schema
            values = []
            for col in schema['colunas']:
                raw = row.get(col['nome'], '')
                # Converter tipo
                value = convert_type(raw, col['tipo'])
                values.append(value)
            rows.append(values)
    
    # Inserir no ClickHouse
    client.insert(schema['tabela'], rows)
```

### Passo 4: Registrar Dataset
**`backend/llm/router.py` - adicionar `DATASETS`** (20 minutos)
```python
DATASETS = {
    "vacinacao": {
        "table": "vacinacao",
        "metadata_path": "backend/metadata/vacinacao.json",
        "csv_path": "backend/data/vacinacao-ac-es.csv",
        "keywords": ["vacina", "dose", "aplicação"]
    },
    "internacoes": {
        "table": "internacoes",
        "metadata_path": "backend/metadata/internacoes.json",
        "csv_path": "backend/data/internacoes-2024.csv",
        "keywords": ["internação", "hospital", "admissão", "alta"]
    }
}

def detect_dataset(question: str) -> str:
    """Detecta qual dataset a pergunta refere-se"""
    question_lower = question.lower()
    for dataset_name, config in DATASETS.items():
        if any(kw in question_lower for kw in config['keywords']):
            return dataset_name
    return "vacinacao"  # default
```

### Passo 5: Atualizar SQL Service
**`backend/services/sql_service.py`** (30 minutos)
```python
def generate_sql(question: str, model_name: str = "deepseek-local"):
    # Detectar dataset
    dataset = detect_dataset(question)
    
    # Carregar schema apropriado
    metadata = load_metadata(dataset)  # NEW PARAMETER
    
    # Gerar prompt com contexto do dataset
    prompt = f"""Você trabalha com dados de {metadata['nome_amigavel']}.

COLUNAS DISPONÍVEIS:
{json.dumps(metadata['colunas'], indent=2)}

EXEMPLOS:
- Pergunta: "Quantas internações em SP?"
  SQL: SELECT COUNT(*) FROM internacoes WHERE estabelecimento_uf = 'SP'
  
- Pergunta: "Qual diagnóstico mais comum?"
  SQL: SELECT diagnóstico_principal, COUNT(*) FROM internacoes GROUP BY diagnóstico_principal ORDER BY COUNT(*) DESC LIMIT 5

PERGUNTA: {question}
SQL:"""
    
    # Gerar e executar
    ...
```

### Passo 6: Testar
```powershell
# Carregar dados
python etl/load_internacoes.py

# Testar query
curl -X POST http://localhost:8000/api/ask `
  -Headers @{"Content-Type"="application/json"} `
  -Body '{"question":"Quantas internações em SP em 2024?","dataset":"internacoes"}'
```

---

## 📈 Esforço Estimado por Dataset

| Dataset | Esforço | Tarefas | Bloqueadores |
|---------|---------|--------|--------------|
| **Vacinação** (atual) | ✅ Completo | CSV + Schema + ETL + Queries | Nenhum |
| **Internações** | 1-2 dias | Novo CSV + Schema JSON + ETL + Testes | Qualidade do CSV |
| **Óbitos** | 1-2 dias | Mesmo que internações | Qualidade do CSV |
| **Atendimentos** | 1-2 dias | Mesmo que internações | Qualidade do CSV |
| **Genérico para N datasets** | 1 semana | Refactor ETL + Schema system + Roteador | Manutenibilidade |

---

## 🏗️ Arquitetura para Suporte Multi-Dataset

### Antes (Atual)
```
CSV Vacinação
    ↓
load_csv_v2.py (hardcoded 32 colunas vacinação)
    ↓
vacinacao.json (schema específico)
    ↓
ClickHouse: TABLE vacinacao
    ↓
sql_service.py (prompt vacinação)
```

### Depois (Proposto)
```
CSV Vacinação                CSV Internações              CSV Óbitos
    ↓                            ↓                            ↓
generic_loader.py <────────────────────────────────────────────
(usa schema JSON para cada)
    ↓
vacinacao.json + internacoes.json + obitos.json
    ↓
ClickHouse: TABLE vacinacao, TABLE internacoes, TABLE obitos
    ↓
detect_dataset() → sql_service.py → dynamic_prompt.py
    ↓
LLM recebe contexto específico de cada tabela
```

---

## 📋 Checklist para Implementar Novo Dataset

Para cada novo tipo de dado (internações, óbitos, atendimentos):

- [ ] **1. Obter CSV do DataSUS**
  - [ ] Verificar colunas
  - [ ] Verificar delimitador (? vs ;)
  - [ ] Verificar encoding (UTF-8 vs LATIN1)
  - Tempo: 1 hora (exploração)

- [ ] **2. Criar Schema JSON**
  - [ ] Listar todas as colunas
  - [ ] Definir tipo correto para cada
  - [ ] Adicionar exemplos
  - [ ] Adicionar descrição human-friendly
  - Tempo: 30 minutos

- [ ] **3. Criar Tabela ClickHouse**
  - [ ] Definir ORDER BY (primárias chaves de filtro)
  - [ ] Testar CREATE TABLE
  - [ ] Verificar se cabe em RAM
  - Tempo: 20 minutos

- [ ] **4. Criar/Adaptar ETL**
  - [ ] Se usar genérico: já funciona
  - [ ] Se criar específico: copy-paste de load_csv_v2.py
  - [ ] Testar parse de datas/números
  - [ ] Testar insert no ClickHouse
  - Tempo: 1 hora

- [ ] **5. Registrar Dataset**
  - [ ] Adicionar em DATASETS no router.py
  - [ ] Adicionar keywords para detect
  - [ ] Testar detect_dataset()
  - Tempo: 20 minutos

- [ ] **6. Testar Queries**
  - [ ] Teste manual: "Quantos registros?"
  - [ ] Teste manual: "Qual o mais comum?"
  - [ ] Teste manual: "Em SP?"
  - Tempo: 30 minutos

**TOTAL por novo dataset: 2-3 horas**

---

## 🎯 Resposta Direta às Suas Perguntas

### P1: "O tratamento é genérico ou específico?"
**R:** Completamente **específico para vacinação** agora. Mas código está estruturado para permitir generalização.

### P2: "É viável fazer genérico E funcional?"
**R:** SIM, mas em fases:
- **Fase 1 (atual):** Específico + funcional ✅
- **Fase 2 (1 semana):** Multi-dataset genérico ⏳
- **Fase 3 (riscos):** Auto-detection de schema (experimental)

### P3: "Isso será uma limitação?"
**R:** Não é limitação, é **design decision**:
- ✅ Funciona perfeitamente para vacinação agora
- ✅ Pode adicionar internações em 2 horas (sem impacto)
- ✅ Arquitetura permite crescimento

### P4: "Precisa de mais desenvolvimento para cada tipo?"
**R:** Sim, mas mínimo:
- Dados em CSV → Schema em JSON (documentar colunas)
- Schema → ETL automático (se usar genérico) OU copiar template
- Total: ~2-3 horas por novo dataset

### P5: "Para internações preciso de novos arquivos?"
**R:** Sim, mas rápido:
```
CRIAR:
└── backend/
    ├── metadata/internacoes.json      ← 30 min
    ├── etl/load_internacoes.py        ← 1 hora (ou usar genérico)
    ├── data/internacoes-2024.csv      ← Você fornece
    
MODIFICAR:
└── backend/
    ├── db/init.sql                    ← +20 min
    ├── llm/router.py                  ← +15 min
    ├── services/sql_service.py        ← +30 min
```

---

## 🚀 Recomendação Prática

**Curto prazo (próximas semanas):**
1. Manter como está (específico para vacinação)
2. Próximo dataset: copiar estrutura existente

**Médio prazo (próximo mês):**
1. Refatorar ETL para genérico
2. Sistema de detecção de dataset
3. Então adicionar múltiplos datasets com facilidade

**Longo prazo (roadmap):**
1. Auto-detection de schema (inferência)
2. UI para carregar CSVs dinamicamente
3. Suporte a dados de tempo real (APIs)

---

## 📄 Documento para Roadmap

Incluir no projeto:

```
SCALABILITY.md
├── Arquitetura multi-dataset
├── Checklist para novo dataset
├── Esforço estimado
├── Fases de implementação
└── Milestones
```

Quer que crie esse arquivo também?
