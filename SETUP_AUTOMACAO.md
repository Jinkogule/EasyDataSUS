# 🚀 Automação EasyDataSUS - Guia Rápido

Este diretório contém scripts de automação para iniciar todos os serviços necessários para testar o EasyDataSUS.

## 📋 O que cada script faz?

Cada script inicia:
1. **ClickHouse** - Banco de dados com 140k registros (SRAG + UBS)
2. **Ollama** - LLM local (deepseek-coder)
3. **FastAPI** - API REST do EasyDataSUS
4. **(Opcional) Testes** - Executa as 68 questões SEIDIG

---

## 🎯 Como Usar

### Opção 1: PowerShell (Recomendado para Windows 10+)

```bash
# Inicia todos os serviços
.\run_all_services.ps1

# Inicia + executa os testes
.\run_all_services.ps1 -Test

# Inicia + testes com saída detalhada
.\run_all_services.ps1 -TestVerbose

# Para todos os serviços
.\run_all_services.ps1 -Stop
```

**Nota**: Se receber erro de permissão, execute no PowerShell como Administrador:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Opção 2: Prompt de Comando (cmd.exe)

```bash
# Inicia todos os serviços
run_all_services.bat

# Inicia + executa os testes
run_all_services.bat test

# Inicia + testes com saída detalhada
run_all_services.bat test-verbose

# Para todos os serviços
run_all_services.bat stop
```

### Opção 3: Python

```bash
# Inicia todos os serviços
python run_all_services.py

# Inicia + executa os testes
python run_all_services.py --test

# Inicia + testes com saída detalhada
python run_all_services.py --test-verbose
```

---

## ✅ O que Deve Aparecer

Após executar, você verá:

```
================================================================================
     🚀 AUTOMACAO EASYDATASUS - INICIANDO SERVICOS
================================================================================

ℹ️  Verificando Docker...
✅ Docker está rodando

ℹ️  Verificando ClickHouse...
✅ ClickHouse está rodando

ℹ️  Verificando Ollama...
✅ Ollama está acessível em http://localhost:11434

ℹ️  Iniciando FastAPI Backend...
✅ FastAPI iniciado em http://localhost:8000

================================================================================
     ✅ TODOS OS SERVIÇOS INICIADOS
================================================================================

Serviços Disponíveis:
  🗄️  ClickHouse:  http://localhost:9000 (admin:admin)
  🧠 Ollama:      http://localhost:11434
  🔌 FastAPI:     http://localhost:8000
  📚 Documentação: http://localhost:8000/docs
```

---

## 📱 URLs Úteis

| Serviço | URL | Credenciais |
|---------|-----|------------|
| **ClickHouse** | http://localhost:9000 | admin:admin |
| **Ollama** | http://localhost:11434 | — |
| **FastAPI** | http://localhost:8000 | — |
| **Documentação (Swagger)** | http://localhost:8000/docs | — |

---

## 🧪 Testando Manualmente

### Via Swagger UI (FastAPI Docs)

1. Abra http://localhost:8000/docs
2. Expanda a seção `/api/query/ask`
3. Clique em "Try it out"
4. Preencha o JSON:
```json
{
  "question": "Quantos casos de SRAG foram notificados?",
  "model": "deepseek-local",
  "dataset": "surtos-srag"
}
```
5. Clique em "Execute"

### Via cURL

```bash
curl -X POST "http://localhost:8000/api/query/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quantas Unidades Básicas de Saúde existem no Brasil?",
    "model": "deepseek-local",
    "dataset": "atencao-basica"
  }'
```

### Via Python Requests

```python
import requests

response = requests.post(
    "http://localhost:8000/api/query/ask",
    json={
        "question": "Qual estado teve mais casos de SRAG?",
        "model": "deepseek-local",
        "dataset": "surtos-srag"
    }
)

print(response.json())
```

---

## 🔧 Solução de Problemas

### "Docker não está rodando"
```bash
# Inicie Docker Desktop (Windows) ou execute:
docker-compose up -d
```

### "Ollama não encontrado"
```bash
# Instale Ollama com Chocolatey:
choco install ollama

# Ou baixe em: https://ollama.ai/download
```

### "Porta 8000 já está em uso"
```bash
# Encontre o processo usando a porta:
netstat -ano | findstr :8000

# Mate o processo (ex: PID 1234):
taskkill /PID 1234 /F

# Ou use outra porta no script
```

### "FastAPI iniciando mas API não responde"
Espere alguns segundos. FastAPI pode levar um tempo para estar pronto. Tente:
```bash
curl http://localhost:8000/docs
```

---

## 📊 Executar Testes Individuais

Depois que todos os serviços estão rodando, você também pode executar testes específicos:

```bash
# Teste TODAS as 68 questões
python test_68_questoes_seidig.py

# Teste apenas COVID-19 (Q1-Q15)
python test_68_questoes_seidig.py --dataset covid-19-vacinacao

# Teste apenas SRAG (Q31-Q45)
python test_68_questoes_seidig.py --start 31 --end 45

# Teste com saída detalhada
python test_68_questoes_seidig.py --verbose

# Teste apenas UBS
python test_68_questoes_seidig.py --dataset atencao-basica
```

Resultados são salvos em `test_results_68_questoes.json`

---

## 📈 Monitorando os Serviços

### ClickHouse - Conectar via CLI

```bash
# Dentro do container Docker
docker exec -it easydatasus-clickhouse-1 clickhouse-client

# Exemplos de queries
SELECT COUNT(*) FROM srag;
SELECT COUNT(*) FROM atencao_basica;
SELECT COUNT(*) FROM covid_vacinacao;
```

### FastAPI - Ver Logs

O FastAPI rodará em primeiro plano (ou em nova janela), então você verá os logs direto:
```
INFO:     Started server process [XXXX]
INFO:     Waiting for application startup.
INFO:     Application startup complete
INFO:     Uvicorn running on http://0.0.0.0:8000
```

### Ollama - Verificar Modelos

```bash
# Ver modelos disponíveis
curl http://localhost:11434/api/tags

# Exemplo de resposta
{
  "models": [
    {"name": "deepseek-coder:6.7b-base", "modified_at": "..."},
    {"name": "llama2:7b", "modified_at": "..."}
  ]
}
```

---

## 🛑 Parando os Serviços

### PowerShell
```powershell
.\run_all_services.ps1 -Stop
```

### Cmd
```cmd
run_all_services.bat stop
```

### Manualmente
- Feche as janelas dos serviços (FastAPI, Ollama)
- Execute: `docker-compose down`

---

## 📚 Próximos Passos

1. **Testar via Interface**: http://localhost:8000/docs
2. **Executar 68 Questões**: `python test_68_questoes_seidig.py`
3. **Analisar Resultados**: `test_results_68_questoes.json`
4. **Ver Documentação**: [docs/README.md](../docs/README.md)

---

## 💡 Dicas

- **Primeira execução** é mais lenta pois baixa dados
- **FastAPI recarrega** em tempo real (não precisa reiniciar)
- **Ollama cache** modelos, segunda execução é mais rápida
- **Resultados de teste** são salvos em JSON para análise posterior

---

## 📞 Suporte

Se tiver problemas:

1. Verifique se Docker/Ollama estão instalados
2. Procure por erros nas janelas dos serviços
3. Tente executar manualmente os serviços
4. Consulte os logs em `backend/logs/` (se existir)

---

**Bem-vindo ao EasyDataSUS! 🚀**
