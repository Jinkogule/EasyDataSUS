# 🚀 EasyDataSUS - Sistema NLP para Consultas de Dados de Saúde

> Consulte dados públicos de saúde (DataSUS) fazendo perguntas em português. O sistema gera SQL automaticamente e retorna respostas interpretadas por IA local.

**Status:** ✅ MVP Completo | 🚀 Pronto para Deploy | 🏗️ Arquitetura Multi-Dataset Genérica | 🔧 Escalável

---

## 🆕 Arquitetura Multi-Dataset Genérica

Este projeto implementa una **arquitetura escalável** que suporta múltiplos temas de dados (datasets) sem necessidade de recodificar lógica central:

- **GenericSQL Generation:** `sql_service.py` gera queries para qualquer dataset dinamicamente
- **Theme-Agnostic ETL:** `load_csv.py` carrega dados para qualquer tema
- **Centralized Config:** `backend/config/datasets.py` registra todos os datasets de forma declarativa
- **Smart Routing:** Sistema detecta automaticamente qual dataset usar pela pergunta

**Suportados atualmente:**
- 🩺 **Vacinação COVID-19** (`vacinacao-covid`) - 390K+ registros
- 🦟 **Dengue 2024** (`dengue-2024`) - estrutura pronta
- 🤒 **Influenza 2025** (`influenza-2025`) - estrutura pronta

**Adicionar novo dataset?** Veja [Adicionar Novo Dataset](#-adicionar-novo-dataset)

---

## ✨ Como Funciona

**Você pergunta:**
```
"Quantas vacinas foram aplicadas em SP?"
```

**Sistema gera SQL automaticamente:**
```sql
SELECT COUNT(*) FROM vacinacao 
WHERE paciente_endereco_uf = 'SP' 
LIMIT 10000
```

**E responde em português:**
```
Em São Paulo foram aplicadas 824 doses de vacina.
```

---

## 🏗️ Arquitetura

```
┌──────────────────────────────────┐
│  Pergunta em Português           │  Frontend
│  "Qual relação vacina + casos?\" │  (React)
└────────────────┬─────────────────┘
                 │
         ┌───────▼──────────┐
         │  FastAPI         │  Port 8000
         │  + Orchestrator  │  Multi-Dataset
         └────────┬─────────┘
                  │
      ┌───────────┼──────────────┐
      │           │              │
   ┌──▼──┐  ┌────▼────┐  ┌──────▼───┐
   │Vacinação  │Dengue    │Influenza │  Config Registry
   │(SQL)      │(SQL)     │(SQL)     │  (config/datasets.py)
   └──┬──┘  └────┬────┘  └──────┬───┘
      │           │              │
   ┌──▼──────────▼──────────────▼──┐
   │     ClickHouse (TimeSeries)   │  Port 8123
   │     Multi-Table Support        │  390K+ rows
   └───────────────────────────────┘
        │
   ┌────▼────────────────┐
   │    Ollama (Local)    │  Port 11434
   │  DeepSeek/Mistral    │  GPU Optional
   │  Retry: 3x Auto      │
   └─────────────────────┘
```

**Stack Técnico:**
- **Backend:** FastAPI + Python 3.10+ (thread-safe)
- **Database:** ClickHouse 23+ (OLAP TimeSeries)
- **LLM:** Ollama (local, sem APIs externas, retry automático)
- **Deployment:** Docker Compose
- **Multi-Dataset:** Config centralizado (backend/config/datasets.py)
- **Architecture:** GenericSQL generation + Theme-agnostic patterns

---

## 📋 Pré-requisitos

- ✅ **Docker Desktop** ([Download](https://www.docker.com/products/docker-desktop))
- ✅ **Python 3.10+** ([Download](https://www.python.org))
- ✅ **Git** (opcional - [Download](https://git-scm.com))
- ✅ **15 GB de espaço livre** (modelos LLM + dados)

**Verificar instalação:**
```powershell
docker --version
docker-compose --version
python --version
```

---

## 🚀 Setup em 6 Passos

### 1️⃣ Clonar Repositório

```powershell
git clone https://github.com/Jinkogule/EasyDataSUS.git
cd EasyDataSUS
```

---

### 2️⃣ Iniciar Docker Containers

**ClickHouse (Banco de Dados):**
```powershell
docker-compose up -d clickhouse
docker-compose logs clickhouse
```
✅ Pronto quando ver: `Server started`

**Ollama (LLM):**
```powershell
docker-compose up -d ollama
docker-compose logs ollama
```
✅ Pronto quando ver: `Loaded run context`

**Verificar:**
```powershell
docker-compose ps
```

---

### 3️⃣ Ambiente Python

```powershell
cd backend

# Virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell

# Se der erro: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Instalar dependências
pip install -r requirements.txt
```

**Criar `.env`:**
```env
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=admin
CLICKHOUSE_PASSWORD=admin
CLICKHOUSE_DATABASE=default

OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=deepseek-coder:6.7b-base-q4_K_M
OLLAMA_TIMEOUT=180

FASTAPI_HOST=localhost
FASTAPI_PORT=8000
FASTAPI_LOG_LEVEL=INFO
```

💡 **Diferença do host:** Mudado de `0.0.0.0` para `localhost` (mais seguro para envs locais)

---

### 4️⃣ Baixar Modelos LLM

⏳ **IMPORTANTE:** Pode levar **5-15 minutos**. Aguarde!

```powershell
# Opção A: DeepSeek (qualidade alta, 4.1GB)
docker exec easydatasus-ollama ollama pull deepseek-coder:6.7b-base-q4_K_M

# Opção B: Orca Mini (rápido, 2GB - recomendado se RAM < 8GB)
docker exec easydatasus-ollama ollama pull orca-mini

# Opção C: Múltiplos modelos
docker exec easydatasus-ollama ollama pull neural-chat
docker exec easydatasus-ollama ollama pull mistral
```

**Verificar:**
```powershell
docker exec easydatasus-ollama ollama list
```

**🔥 Warmup do Ollama (OBRIGATÓRIO):**
```powershell
docker exec easydatasus-ollama ollama run deepseek-coder:6.7b-base-q4_K_M "Hello"
```

⚠️ Primeiro request é lento (30-60s), depois melhora.

---

### 5️⃣ Carregar Dados

**Opção A: CLI (Recomendado)**
```powershell
python etl/load_csv.py
```

**Opção B: Upload via API**
```powershell
curl -X POST "http://localhost:8000/api/admin/datasets/upload?dataset=vacinacao-covid" `
  -F "file=@seu-arquivo.csv"
```

**Opção C: Manual**
Coloque arquivo em: `backend/data/datasets/vacinacao-covid/seu-arquivo.csv`
Depois: `python etl/load_csv.py`

---

### 6️⃣ Iniciar Backend

```powershell
python main.py
```

✅ Pronto em: `Uvicorn running on http://0.0.0.0:8000`

---

## 🧪 Testes Rápidos

**Health Check:**
```powershell
curl http://localhost:8000/health
```

**Fazer Pergunta:**
```powershell
$body = @{
    question = "Quantas vacinas em SP?"
    model = "deepseek-coder:6.7b-base-q4_K_M"
} | ConvertTo-Json

curl -X POST "http://localhost:8000/api/ask" `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body
```

**Resposta Esperada:**
```json
{
  "success": true,
  "sql": "SELECT COUNT(*) FROM vacinacao WHERE paciente_endereco_uf = 'SP'",
  "data": [[824]],
  "insight": "Em São Paulo foram aplicadas 824 doses de vacina."
}
```

---

## 🔀 Usar Multi-Dataset

### Testar com Dataset Específico

```powershell
$body = @{
    question = "Quantos casos de dengue?"
    dataset = "dengue-2024"
    model = "deepseek-coder:6.7b-base-q4_K_M"
} | ConvertTo-Json

curl -X POST "http://localhost:8000/api/ask" `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body
```

### Detecção Automática

Se omitir `dataset`, o sistema tenta detectar pela pergunta:

```powershell
$body = @{
    question = "Quantas internações por COVID?"  # ← Sistema detecta automaticamente
    model = "deepseek-coder:6.7b-base-q4_K_M"
} | ConvertTo-Json

curl -X POST "http://localhost:8000/api/ask" `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body
```

### Listar Datasets Disponíveis

```powershell
curl http://localhost:8000/api/admin/datasets/available
```

Resposta:
```json
{
  "datasets": [
    {"id": "vacinacao-covid", "table": "vacinacao", "rows": 390911},
    {"id": "dengue-2024", "table": "dengue", "rows": 0},
    {"id": "influenza-2025", "table": "influenza", "rows": 0}
  ]
}
```

---

## 📤 Upload de Dados (API)

### URL Base
```
POST /api/admin/datasets/upload
```

### Com cURL
```bash
curl -X POST "http://localhost:8000/api/admin/datasets/upload?dataset=vacinacao-covid" \
  -F "file=@vacina-sp.csv"
```

### Com Python
```python
import requests

response = requests.post(
    'http://localhost:8000/api/admin/datasets/upload',
    params={'dataset': 'vacinacao-covid'},
    files={'file': open('data.csv', 'rb')}
)
print(response.json())
```

### Com JavaScript/React
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);

fetch('http://localhost:8000/api/admin/datasets/upload?dataset=vacinacao-covid', {
  method: 'POST',
  body: formData
})
.then(r => r.json())
.then(data => console.log(data))
```

### Resposta
```json
{
  "success": true,
  "dataset": "vacinacao-covid",
  "filename": "data.csv",
  "rows_loaded": 390911,
  "message": "Dataset carregado com sucesso!"
}
```

### Validações Automáticas
- ✅ Schema matching (colunas esperadas)
- ✅ Tipo de dados
- ✅ Campos obrigatórios
- ✅ Delimitador semicolon

### Outros Endpoints Admin

```powershell
# Validar sem upload
curl -X POST "http://localhost:8000/api/admin/datasets/validate?dataset=vacinacao-covid" `
  -F "file=@seu-arquivo.csv"

# Listar datasets
curl http://localhost:8000/api/admin/datasets/available

# Info de dataset
curl http://localhost:8000/api/admin/datasets/vacinacao-covid/info

# Deletar arquivo
curl -X DELETE "http://localhost:8000/api/admin/datasets/vacinacao-covid/files/vacina-sp.csv"

# Recarregar dataset
curl -X POST "http://localhost:8000/api/admin/datasets/vacinacao-covid/reload"
```

---

## 🐛 Troubleshooting

### ❌ Ollama retorna erro 500

**Diagnóstico (execute em ordem):**

1️⃣ **Está rodando?**
```powershell
docker ps | findstr ollama
```
Se não → `docker-compose up -d ollama`

2️⃣ **Modelo carregado?**
```powershell
docker exec easydatasus-ollama ollama list
```
Se vazio → Baixe modelo novamente

3️⃣ **Logs completos:**
```powershell
docker logs easydatasus-ollama -f
```

**Soluções (tente em ordem):**

**Solução 1: Reiniciar**
```powershell
docker-compose down ollama
Start-Sleep -Seconds 10
docker-compose up -d ollama
Start-Sleep -Seconds 30
```

**Solução 2: Verificar memória**
```powershell
docker stats easydatasus-ollama --no-stream
```
Se "Out of Memory" → use `orca-mini` em `.env`

**Solução 3: Aumentar timeout**
```env
OLLAMA_TIMEOUT=300
```
Reinicie: `python main.py`

**Solução 4: Limpar cache**
```powershell
docker-compose down ollama
docker volume prune -f
docker-compose up -d ollama
docker exec easydatasus-ollama ollama pull orca-mini
```

**System has automatic retry:** Tenta 3x automaticamente. Veja logs do backend.

---

### ❌ ClickHouse connection refused

```powershell
docker-compose logs clickhouse
```
Se "Server started" → Conexão OK
Se não → Reinicie: `docker-compose down clickhouse && docker-compose up -d clickhouse`

---

### ❌ CSV validation failed

```powershell
# Verifique schema esperado
cat backend/metadata/datasets/vacinacao-covid/schema.json

# Seu CSV tem todas as colunas?
# Delimitador é semicolon (;)?
# Sem linhas vazias no meio?
```

---

### ❌ PowerShell: "Cannot execute script"

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

### ❌ Python module not found

```powershell
pip install -r requirements.txt
```

---

## 🎛️ Gerenciar Modelos LLM

**Ver disponíveis:**
```powershell
docker exec easydatasus-ollama ollama list
```

**Baixar novo:**
```powershell
docker exec easydatasus-ollama ollama pull mistral
```

**Testar modelo:**
```powershell
$body = @{
    question = "Quantas vacinas?"
    model = "mistral"
} | ConvertTo-Json

curl -X POST "http://localhost:8000/api/ask" `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body
```

**Remover (libera 4GB+):**
```powershell
docker exec easydatasus-ollama ollama rm mistral
```

**Comparação de Modelos:**

| Modelo | Tamanho | Velocidade | Qualidade | RAM Mín |
|--------|---------|-----------|-----------|---------|
| orca-mini | 2GB | ⚡⚡⚡ | ⭐⭐ | 4GB |
| neural-chat | 4.7GB | ⚡⚡ | ⭐⭐⭐ | 6GB |
| deepseek-coder | 6.7GB | ⚡ | ⭐⭐⭐⭐ | 8GB |
| mistral | 4GB | ⚡⚡ | ⭐⭐⭐⭐ | 6GB |

---

## 📊 Adicionar Novo Dataset

### Passo 1: Registrar em `backend/config/datasets.py`

```python
# backend/config/datasets.py - DATASETS_CONFIG dict

DATASETS_CONFIG = {
    "seu-dataset-2024": {
        "table_name": "seu_dataset_2024",
        "description": "Descrição do seu dataset",
        "metadata_file": "backend/metadata/datasets/seu-dataset-2024/schema.json",
    },
    # ... outros datasets
}
```

### Passo 2: Criar estrutura de metadados

**1. Criar pasta:**
```powershell
mkdir backend/metadata/datasets/seu-dataset-2024
mkdir backend/data/datasets/seu-dataset-2024
```

**2. Definir schema** (`backend/metadata/datasets/seu-dataset-2024/schema.json`):
```json
{
  "name": "Seu Dataset 2024",
  "description": "Descrição detalhada",
  "fonte": "DataSUS / Seu órgão",
  "table_name": "seu_dataset_2024",
  "colunas_principais": {
    "id": {"tipo": "Int32", "descricao": "ID único", "exemplos": [1, 2, 3]},
    "data": {"tipo": "Date", "descricao": "Data do evento", "exemplos": ["2024-01-15"]},
    "estado_uf": {"tipo": "String", "descricao": "UF do evento", "exemplos": ["SP", "RJ"]},
    "valor": {"tipo": "Float32", "descricao": "Valor medido", "exemplos": [100.5]}
  }
}
```

### Passo 3: Carregar dados

**Opção A: CLI (Recomendado)**
```powershell
python etl/load_csv.py
```
O sistema detecta automaticamente novos datasets em `backend/config/datasets.py`

**Opção B: API**
```powershell
curl -X POST "http://localhost:8000/api/admin/datasets/upload?dataset=seu-dataset-2024" `
  -F "file=@seu-arquivo.csv"
```

**Opção C: Upload Manual**
1. Coloque arquivo CSV em: `backend/data/datasets/seu-dataset-2024/`
2. Execute: `python etl/load_csv.py`

### Passo 4: Testar

```powershell
$body = @{
    question = "Pergunta sobre seu novo dataset"
    dataset = "seu-dataset-2024"
    model = "deepseek-coder:6.7b-base-q4_K_M"
} | ConvertTo-Json

curl -X POST "http://localhost:8000/api/ask" `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body
```

---

## 🏗️ Estrutura do Projeto

```
backend/
├── main.py                              # FastAPI app
├── requirements.txt                     # Dependências
├── .env                                 # Configuração
├── config/                              # 🆕 Configuração Centralizada
│   ├── __init__.py
│   └── datasets.py                      # 🆕 Registry de datasets + helpers
├── routes/
│   ├── query.py                         # POST /ask (multi-dataset)
│   ├── questions.py                     # GET /questions
│   └── admin.py                         # Upload + gerenciamento
├── services/
│   ├── sql_service.py                   # 🔄 GENÉRICO: cria SQL para qualquer dataset
│   └── interpretation_service.py        # Interpretação
├── llm/
│   ├── base.py                          # Interface
│   ├── router.py                        # Seletor de modelo
│   ├── ollama_provider.py               # ✅ Com retry automático (3x)
│   └── openai_provider.py               # Alternativa
├── db/
│   └── clickhouse.py                    # Cliente BD
├── etl/
│   └── load_csv.py                      # 🔄 GENÉRICO: carrega qualquer dataset
├── metadata/
│   ├── loader.py                        # load_metadata(dataset)
│   └── datasets/
│       ├── vacinacao-covid/
│       │   ├── schema.json              # 32 colunas, tabela: vacinacao
│       │   └── README.md
│       ├── dengue-2024/
│       │   └── schema.json              # Estrutura dengue, tabela: dengue
│       └── influenza-2025/
│           └── schema.json              # Estrutura influenza, tabela: influenza
├── data/
│   ├── datasets/
│   │   ├── vacinacao-covid/
│   │   │   └── vacinacao-ac-es.csv      # 390K+ registros
│   │   ├── dengue-2024/
│   │   │   └── (dados carregados aqui)
│   │   └── influenza-2025/
│   │       └── (dados carregados aqui)
│   └── README_DATASETS.md
└── (outros arquivos)

docker-compose.yml                      # Infrastructure (ClickHouse + Ollama)
.env.example                            # Template de configuração
.gitignore                              # Git exclusões
README.md                               # Este arquivo (público, centralizado)
/docs/                                  # 🆕 Documentação interna (gitignored)
│   ├── ESCALABILIDADE_MULTI_TEMAS.md
│   ├── IMPLEMENTACAO_ESCALABILIDADE.md
│   └── ...(outros guides)
ARCHITECTURE.md                         # Detalhes técnicos (quando criado)
```

---

## 🔄 Recursos Principais

### ✅ Suportado (MVP)
- **Multi-dataset:** Vacinação COVID-19, Dengue 2024, Influenza 2025 (extensível)
- **Arquitetura genérica:** SQL service + ETL agnósticos a temas
- **Upload de CSV:** Validação automática de schema
- **Roteamento smart:** Detecta dataset automaticamente pela pergunta
- **Retry automático:** 3x retry para Ollama com backoff
- **Fallback robusto:** Query genérica se LLM falhar
- **Modelos intercambiáveis:** DeepSeek, Orca, Mistral, Neural-Chat
- **Config centralizado:** `backend/config/datasets.py` para registrar novos temas

### 🔄 Roadmap (Próximos)
- Frontend Web (React)
- Dashboard com gráficos + exportação
- Cache de queries + histórico
- Análises multi-dataset (correlação temporal)
- Autenticação/autorização básica
- GPU acceleration opcional
- GraphQL API alternativa

---

## 🧑‍💻 Stack Técnico Detalhado

**Backend:**
- FastAPI 0.104+
- Pydantic (validação)
- Python-multipart (uploads)
- Requests (HTTP)

**Database:**
- ClickHouse 23+
- clickhouse-driver

**LLM:**
- Ollama (local inference)
- Suporte a OpenAI API (fallback)

**DevOps:**
- Docker & Docker Compose
- Git + GitHub
- Python venv

---

## 🚀 Deployment

Para deploy em produção:

1. **AWS EC2:**
   - Inicie instância Ubuntu 22.04
   - Clone repositório
   - Execute `docker-compose up -d`

2. **Azure:**
   - Use App Service + Container
   - Configure environment variables

3. **DigitalOcean:**
   - Droplet + Docker
   - Port forwarding necessário

📖 Veja `ARCHITECTURE.md` para detalhes completos

---

## 🆘 Suporte & Debug

**Logs em tempo real:**
```powershell
docker-compose logs -f backend
docker-compose logs -f ollama
docker-compose logs -f clickhouse
```

**Testar componentes individualmente:**
```powershell
# Testar ClickHouse
curl -X POST "http://localhost:8123/" -u admin:admin -d "SELECT 1"

# Testar Ollama
curl http://localhost:11434/api/tags

# Testar Backend
curl http://localhost:8000/health
```

**Issues do GitHub:**
https://github.com/Jinkogule/EasyDataSUS/issues

---

## 📝 Seções Técnicas

- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Design técnico, diagramas, fluxos
- **[FRONTEND_INTEGRATION.md](./FRONTEND_INTEGRATION.md)** - React/Vue integration

---

## 📄 Licença

MIT License - Use livremente em projetos comerciais

---

## 🎉 Pronto para começar?

```powershell
# Tudo em um comando
git clone https://github.com/Jinkogule/EasyDataSUS.git
cd EasyDataSUS
docker-compose up -d
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python etl/load_csv.py
python main.py
```

Acesse: http://localhost:8000

**Feito com ❤️ para tornar dados públicos acessíveis a todos!**
