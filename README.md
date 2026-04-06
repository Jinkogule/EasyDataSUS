# 🚀 EasyDataSUS - Sistema NLP para Consultas de Dados de Saúde

> Consulte dados públicos de saúde (DataSUS) fazendo perguntas em português. O sistema gera SQL automaticamente e retorna respostas interpretadas por IA local.

**Status:** ✅ MVP Completo | 🚀 Pronto para Deploy | 📊 Multi-Dataset Support

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
┌─────────────────────────────┐         Frontend
│   Pergunta em Português     │         (React)
└──────────────┬──────────────┘
               │
       ┌───────▼────────┐
       │  FastAPI       │  Port 8000
       │  Backend       │
       └───────┬────────┘
               │
        ┌──────┴──────────┐
        │                 │
    ┌───▼────┐         ┌──▼─────┐
    │ClickHouse       │ Ollama
    │ Port 8123       │ Port 11434
    │                 │
    │ 390K+ Vacinas   │ DeepSeek
    │ Dengue          │ Orca-Mini
    │ Influenza       │ Mistral
    └─────────┘       │ Neural-Chat
              │       └─────────────┘
```

**Stack Técnico:**
- **Backend:** FastAPI + Python 3.10+
- **Database:** ClickHouse (SQL OLAP)
- **LLM:** Ollama (local, sem APIs externas)
- **Deployment:** Docker Compose
- **Multi-Dataset:** Arquitetura escalável

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

FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
FASTAPI_LOG_LEVEL=INFO
```

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

**1. Criar estrutura:**
```
backend/metadata/datasets/seu-dataset/
  └── schema.json

backend/data/datasets/seu-dataset/
  └── seu-arquivo.csv
```

**2. Definir schema** (`schema.json`):
```json
{
  "name": "Seu Dataset",
  "description": "Descrição",
  "table_name": "seu_dataset",
  "columns": [
    {"name": "id", "type": "Int32"},
    {"name": "data", "type": "Date"},
    {"name": "valor", "type": "Float32"}
  ]
}
```

**3. Carregar dados:**
```powershell
python etl/load_csv.py
```

ou via API:
```powershell
curl -X POST "http://localhost:8000/api/admin/datasets/upload?dataset=seu-dataset" `
  -F "file=@seu-arquivo.csv"
```

---

## 🏗️ Estrutura do Projeto

```
backend/
├── main.py                              # FastAPI app
├── requirements.txt                     # Dependências
├── .env                                 # Configuração
├── routes/
│   ├── query.py                         # POST /ask
│   ├── questions.py                     # GET /questions
│   └── admin.py                         # Upload + gerenciamento
├── services/
│   ├── sql_service.py                   # Geração SQL
│   └── interpretation_service.py        # Interpretação
├── llm/
│   ├── base.py                          # Interface
│   ├── router.py                        # Seletor de modelo
│   ├── ollama_provider.py               # Com retry automático
│   └── openai_provider.py               # Alternativa
├── db/
│   └── clickhouse.py                    # Cliente BD
├── etl/
│   └── load_csv.py                      # Carregar dados (multi-CSV)
├── metadata/
│   ├── loader.py                        # load_metadata()
│   └── datasets/
│       ├── vacinacao-covid/
│       │   ├── schema.json              # 32 colunas
│       │   └── README.md
│       ├── dengue-2024/
│       │   └── schema.json
│       └── influenza-2025/
│           └── schema.json
└── data/
    ├── datasets/
    │   ├── vacinacao-covid/
    │   │   └── vacinacao-ac-es.csv      # 390K registros
    │   ├── dengue-2024/
    │   │   └── dados.csv
    │   └── influenza-2025/
    │       └── dados.csv
    └── README_DATASETS.md

docker-compose.yml                      # Infrastructure
.gitignore                              # Git exclusões
README.md                               # Este arquivo (centralizado)
ARCHITECTURE.md                         # Detalhes técnicos
FRONTEND_INTEGRATION.md                 # React integration
```

---

## 🔄 Recursos Principais

### ✅ Suportado
- Multi-dataset (vacinação, dengue, influenza)
- Upload de CSV com validação
- Roteamento automático de perguntas
- Retry logic (3x) para Ollama
- Fallback inteligente se LLM falhar
- Modelos intercambiáveis (DeepSeek, Orca, Mistral)
- Múltiplas perguntas pré-prontas

### 🔄 Em Desenvolvimento
- Frontend Web (React)
- Dashboard com gráficos
- Cache de queries
- Histórico de perguntas
- Autenticação/autorização
- GPU acceleration
- Clustering de dados

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
