# 🚀 EasyDataSUS - Sistema NLP para Consultas de Dados de Vacinação

> Consulte dados públicos de vacinação (DataSUS) fazendo perguntas simples em português. O sistema transforma suas perguntas em SQL, executa no ClickHouse e interpreta os resultados usando LLM local.

**Status:** ✅ MVP Funcional e Demonstrável

---

## ✨ Como Funciona?

**Você pergunta:**
```
"Quantas vacinas foram aplicadas em SP?"
```

**O sistema gera SQL:**
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
┌─────────────────────────────┐
│   Pergunta em Português     │
└──────────────┬──────────────┘
               │
       ┌───────▼────────┐
       │  FastAPI       │
       │  Backend       │
       │  (Port 8000)   │
       └───────┬────────┘
               │
        ┌──────┴──────────┐
        │                 │
    ┌───▼────┐         ┌──▼─────┐
    │ ClickHouse   │ LLM Ollama
    │ (Port 8123)  │ (Port 11434)
    │              │ 
    │ 390K+        │ DeepSeek-Coder
    │ Registros    │ Orca-Mini
    │ Vacinação    │ Neural-Chat
    └────────┘     │ Mistral
             │      └────────┘
└─────────────────┘
```

**Stack:**
- 🔧 **Backend:** FastAPI + Python 3.12
- 📦 **Database:** ClickHouse (SQL OLAP)
- 🧠 **LLM:** Ollama (local, sem APIs)
- 🐳 **Deployment:** Docker Compose

---

## 📋 Pré-requisitos

Antes de começar, você precisa de:

- ✅ **Docker Desktop** ([Download](https://www.docker.com/products/docker-desktop))
- ✅ **Docker Compose** (vem com Docker Desktop)
- ✅ **Python 3.10+** ([Download](https://www.python.org))
- ✅ **Git** (opcional, para clonar - [Download](https://git-scm.com))
- ✅ **~15 GB de espaço livre** (para LLM models + dados)

**Verifique se tudo está instalado:**
```powershell
docker --version
docker-compose --version
python --version
git --version
```

---

## 🚀 Guia de Setup Completo (Passo a Passo)

### 1️⃣ Clone o Repositório

```powershell
# Windows PowerShell
git clone https://github.com/seu-usuario/easydatasus.git
cd easydatasus
```

Ou se não tiver Git, faça download do ZIP e extraia.

---

### 2️⃣ Suba o Docker Compose

**Inicie o ClickHouse:**

```powershell
docker-compose up -d clickhouse
```

**Aguarde o ClickHouse iniciar (15-30 segundos):**

```powershell
docker-compose logs clickhouse
```

✅ Pronto quando ver:
```
<Information> Application: Listening for TCP connections on [::]:9000
<Information> Application: Server started
```

**Suba o Ollama:**

```powershell
docker-compose up -d ollama
```

**Aguarde Ollama iniciar (30-60 segundos):**

```powershell
docker-compose logs ollama
```

✅ Pronto quando ver:
```
Loaded run context
```

**Verifique status:**

```powershell
docker-compose ps
```

Deve mostrar:
```
STATUS  NAMES
Up      easydatasus-clickhouse
Up      easydatasus-ollama
```

---

### 3️⃣ Prepare o Ambiente Python

**Abra PowerShell na pasta `backend`:**

```powershell
cd backend
```

**Crie um virtual environment:**

```powershell
python -m venv venv
```

**Ative o virtual environment:**

```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1

# Se der erro "não permitido", execute:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Instale as dependências:**

```powershell
pip install -r requirements.txt
```

**Configure as variáveis de ambiente (.env):**

```powershell
# Copie o arquivo de exemplo (se existir)
Copy-Item .env.example .env -ErrorAction SilentlyContinue

# Ou crie manualmente
```

**Crie o arquivo `.env` com:**

```env
# ClickHouse
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=admin
CLICKHOUSE_PASSWORD=admin
CLICKHOUSE_DATABASE=default

# Ollama Local
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=deepseek-coder:6.7b-base-q4_K_M

# FastAPI
FASTAPI_HOST=0.0.0.0
FASTAPI_PORT=8000
FASTAPI_LOG_LEVEL=INFO
```

---

### 4️⃣ Baixe os Modelos LLM

**Opção A: Apenas DeepSeek (4.1 GB, ~50s latência)**

```powershell
docker exec easydatasus-ollama ollama pull deepseek-coder:6.7b-base-q4_K_M
```

**Opção B: Instalar vários modelos (recomendado)**

```powershell
# Orca Mini (rápido, ~2GB, 10s latência)
docker exec easydatasus-ollama ollama pull orca-mini

# Neural Chat (balanço, ~4.7GB, 40s latência)
docker exec easydatasus-ollama ollama pull neural-chat

# Mistral (qualidade, ~4GB, 30s latência)
docker exec easydatasus-ollama ollama pull mistral
```

**Verifique modelos instalados:**

```powershell
docker exec easydatasus-ollama ollama list
```

---

### 5️⃣ Carregue os Dados de Vacinação

**Carregue o CSV no ClickHouse:**

```powershell
# Dentro de backend/ com venv ativo
python etl/load_csv.py
```

**Você deve ver:**

```
Conectando ao ClickHouse...
✓ Conexão OK

Carregando CSV...
✓ 390.911 linhas inseridas com sucesso!

Distribuição por estado:
  AC: 376.290
  RO: 4.272
  AM: 3.504
  ... outros estados ...

✓ Tabela 'vacinacao' pronta com 390.911 registros
```

**Verifique os dados no ClickHouse:**

```powershell
curl -X POST "http://localhost:8123/" `
  -u admin:admin `
  -d "SELECT COUNT(*) as total FROM vacinacao"
```

Deve retornar: `390911`

---

### 6️⃣ Inicie o Backend

**Dentro de `backend/` com venv ativo:**

```powershell
python main.py
```

**Você deve ver:**

```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete
```

---

## 🧪 Teste o Sistema

**Em outro terminal PowerShell, dentro de `backend/`:**

### Teste 1: Health Check

```powershell
curl http://localhost:8000/health
```

**Resposta esperada:**
```json
{"status":"ok","service":"EasyDataSUS"}
```

### Teste 2: Fazer uma Pergunta

```powershell
$body = @{
    question = "Quantas vacinas em SP?"
    model = "deepseek-coder:6.7b-base-q4_K_M"
} | ConvertTo-Json

curl -X POST http://localhost:8000/api/ask `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body
```

**Resposta esperada:**
```json
{
  "success": true,
  "sql": "SELECT COUNT(*) FROM vacinacao WHERE paciente_endereco_uf = 'SP'",
  "data": [[824]],
  "insight": "Em São Paulo foram aplicadas 824 doses de vacina."
}
```

### Teste 3: Usar Outro Modelo

```powershell
$body = @{
    question = "Quantas vacinas por estado?"
    model = "orca-mini"
} | ConvertTo-Json

curl -X POST http://localhost:8000/api/ask `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body
```

---

## 📚 Exemplos de Perguntas

| Pergunta | Resultado |
|----------|-----------|
| Quantas vacinas em SP? | 824 doses |
| Quantas vacinas em AC? | 376.290 doses |
| Qual vacina mais aplicada? | [Resultado agrupado] |
| Vacinas por estado? | Tabela com distribuição |
| Quantas no mês de Março? | [Resultado filtrado] |

---

## 🎛️ Gerenciar Modelos

**Ver todos os modelos disponíveis:**

```powershell
docker exec easydatasus-ollama ollama list
```

**Baixar um novo modelo:**

```powershell
docker exec easydatasus-ollama ollama pull neural-chat
```

**Testar um modelo específico:**

```powershell
$body = @{
    question = "Quantas vacinas?"
    model = "neural-chat"
} | ConvertTo-Json

curl -X POST http://localhost:8000/api/ask `
  -Headers @{"Content-Type"="application/json"} `
  -Body $body
```

**Remover um modelo (libera espaço):**

```powershell
docker exec easydatasus-ollama ollama rm mistral
```

---

## 🐛 Troubleshooting

### ❌ Erro: "Cannot GET / (ClickHouse connection refused)"

**Solução:**

```powershell
# Verifique se ClickHouse está rodando
docker-compose ps clickhouse

# Se não estiver, reinicie
docker-compose up -d clickhouse

# Aguarde 30 segundos e tente novamente
docker-compose logs clickhouse
```

---

### ❌ Erro: "Connection refused (Ollama: 11434)"

**Solução:**

```powershell
# Inicie Ollama
docker-compose up -d ollama

# Aguarde iniciar
Start-Sleep -Seconds 30

# Verifique
docker-compose logs ollama

# Baixe o modelo novamente se necessário
docker exec easydatasus-ollama ollama pull deepseek-coder:6.7b-base-q4_K_M
```

---

### ❌ Erro: "CSV load failed"

**Solução:**

```powershell
# Verifique se arquivo existe
Test-Path ".\data\vacinacao-ac-es.csv"

# Se não existir, faça download de https://datasus.gov.br
# ou use dados de exemplo

# Verifique logs
python etl/load_csv.py

# Teste conexão ClickHouse
curl -X POST "http://localhost:8123/" -u admin:admin -d "SHOW TABLES"
```

---

### ❌ Erro: "SQL inválido / sem resultados"

**Solução:**

```powershell
# Verifique logs do backend (saída do terminal)
# Deve mostrar: "DEBUG: SQL extraído: SELECT ..."

# Teste uma query manual
curl -X POST "http://localhost:8123/" `
  -u admin:admin `
  -d "SELECT TOP 5 * FROM vacinacao"

# Verifique se tabela existe
curl -X POST "http://localhost:8123/" `
  -u admin:admin `
  -d "DESCRIBE TABLE vacinacao"
```

---

### ❌ Erro: "Timeout aguardando resposta do LLM"

**Solução:**

```powershell
# Verifique se modelo está rodando
docker exec easydatasus-ollama ollama list

# Se não aparecer, baixe
docker exec easydatasus-ollama ollama pull deepseek-coder:6.7b-base-q4_K_M

# Aguarde finalizar (pode levar 10-15 min)
docker-compose logs ollama

# Verifique se container tem RAM suficiente
# Modelos precisam de ~8GB RAM disponível
```

---

### ❌ PowerShell: "Não é possível carregar arquivo de script"

**Solução:**

```powershell
# Execute uma vez
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Depois
.\venv\Scripts\Activate.ps1
```

---

## 🛑 Parar o Sistema

**Parar todos os containers:**

```powershell
docker-compose down
```

**Parar apenas ClickHouse (manter Ollama):**

```powershell
docker-compose stop clickhouse
```

**Limpar volumes e dados (cuidado!):**

```powershell
docker-compose down -v
```

---

## 📊 Dados Disponíveis

**Tabela:** `vacinacao`

**Registros:** 390.911 doses de vacina

**Distribuição por Estado:**
- 🟢 AC (Acre): 376.290 registros (96.2%)
- RO (Rondônia): 4.272 registros
- AM (Amazonas): 3.504 registros
- *(27 estados no total)*

**Colunas:** 32 (informações de paciente, vacinação, estabelecimento, etc)

**Período:** Conforme dados do DataSUS

---

## 🎯 Próximos Passos

1. **Testar com diferentes modelos** - Compare qualidade e velocidade
2. **Explorar SCALABILITY.md** - Adicionar novos datasets (internações, óbitos)
3. **Criar Frontend Web** - Interface para não-desenvolvedores
4. **GPU Acceleration** - 10x mais rápido com CUDA
5. **Multi-dataset Support** - Unificar várias fontes DataSUS

Veja `SCALABILITY.md` para detalhes de expansão.

---

## ✅ Checklist de Setup

- [ ] Docker Desktop instalado e rodando
- [ ] `docker-compose ps` mostra ClickHouse + Ollama
- [ ] Python venv criado e ativado
- [ ] `pip install -r requirements.txt` executado
- [ ] `.env` criado com valores corretos
- [ ] Modelo LLM baixado (`ollama list` mostra modelo)
- [ ] CSV carregado (`python etl/load_csv.py` OK)
- [ ] Backend rodando (`python main.py`)
- [ ] Health check OK (`curl http://localhost:8000/health`)
- [ ] Pergunta de teste funcionando

Se tudo ✅, você está pronto! 🎉

---

## 📖 Estrutura do Projeto

```
backend/
├── main.py                          # FastAPI app
├── requirements.txt                 # Dependencies
├── .env.example                     # Template configuração
├── test_scalability.py              # Valida datasets
│
├── db/
│   └── clickhouse.py                # Cliente ClickHouse
├── routes/
│   ├── query.py                     # POST /ask
│   └── questions.py                 # GET /questions
├── services/
│   ├── sql_service.py               # Geração SQL
│   └── interpretation_service.py    # Interpretação LLM
├── llm/
│   ├── base.py                      # Interface
│   ├── router.py                    # Seletor
│   └── ollama_provider.py           # Ollama Provider
│
├── 📚 metadata/         (SCHEMAS - ESCALÁVEL)
│   ├── README_DATASETS.md           # Documentação
│   ├── loader.py                    # load_metadata(dataset)
│   └── datasets/
│       ├── vacinacao-covid/
│       │   ├── schema.json          # 32 colunas
│       │   └── README.md
│       ├── dengue-2024/             # (Futuro)
│       │   └── schema.json
│       └── influenza-2025/          # (Futuro)
│           └── schema.json
│
├── 💾 data/             (CSVS - ESCALÁVEL)
│   ├── README_DATASETS.md           # Documentação
│   └── datasets/
│       ├── vacinacao-covid/
│       │   ├── vacinacao-ac-es.csv  # 390K registros
│       │   └── README.md
│       ├── dengue-2024/             # (Futuro)
│       │   └── dengue-*.csv
│       └── influenza-2025/          # (Futuro)
│           └── influenza-*.csv
│
├── etl/
│   ├── load_csv.py                  # load_csv(dataset)
│   └── load_csv_v2.py               # Versão alternativa
│
└── venv/                            # Environment (ignored)

docker-compose.yml                  # Infrastructure
init.sql                            # Schema ClickHouse
README.md                           # Setup guide
SCALABILITY_DATASETS.md             # 📚 Guia de escalabilidade
STRUCTURE_VISUALIZATION.md          # 📊 Visualização
.env.example                        # Configuração
```

### 🆕 Estrutura Escalável (v1.1+)

A nova estrutura suporta **múltiplos datasets**:

```python
# Carrega qualquer dataset
metadata = load_metadata("vacinacao-covid")    # ✅ Atual
metadata = load_metadata("dengue-2024")        # 🆕 Futuro
metadata = load_metadata("influenza-2025")     # 🆕 Futuro

# Carrega dados automaticamente
load_csv()                          # vacinacao-covid (padrão)
load_csv(dataset="dengue-2024")     # dataset específico
```

📖 **Veja [SCALABILITY_DATASETS.md](SCALABILITY_DATASETS.md)** para guia completo de escalabilidade

---

## 🚀 Próximos Passos

1. ✅ Setup completo
2. ✅ Testar com `curl` ou Postman
3. ✅ **Roteamento por Dataset** - Sistema de perguntas pré-prontas com detecção automática
4. 🔄 **[TODO]** Frontend Web (React/Vue)
5. 🔄 **[TODO]** Dashboard com gráficos
6. 🔄 **[TODO]** Cache de queries
7. 🔄 **[TODO]** Histórico de perguntas

---

## 🎯 Novidade: Roteamento Inteligente por Dataset

O sistema agora suporta **múltiplos datasets** com roteamento automático!

### Perguntas Pré-Prontas

```bash
# Listar todas as perguntas disponíveis
curl http://localhost:8000/api/questions

# Listar perguntas de um dataset específico
curl http://localhost:8000/api/questions/vacinacao-covid

# Executar pergunta pré-pronta (frontend seleciona)
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quantas vacinas em SP?",
    "dataset": "vacinacao-covid"
  }'

# Executar pergunta customizada (detecta dataset)
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quantos casos de dengue?"
  }'
```

📖 **Veja [ROUTING_SUMMARY.md](ROUTING_SUMMARY.md)** para detalhes completos  
📖 **Veja [FRONTEND_INTEGRATION.md](FRONTEND_INTEGRATION.md)** para integração no frontend

---

## 📝 Licença

MIT - Use livremente!

---

## 💬 Suporte

Se encontrar problemas, verifique:

1. Logs: `docker-compose logs -f clickhouse`
2. Health: `curl http://localhost:8000/health`
3. Conectividade: `curl -X POST http://localhost:8123 -u admin:admin -d "SELECT 1"`

4. Arquivo .env configurado corretamente

---

**Feito com ❤️ para tornar dados públicos acessíveis a todos!**
