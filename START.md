# 🚀 INICIAR EASYDATASUS - GUIA RÁPIDO

## Opção 1️⃣ PowerShell (Recomendado)
```powershell
cd C:\dev\easydatasus
.\run_all_services.ps1 -Test
```

## Opção 2️⃣ Prompt de Comando
```cmd
cd C:\dev\easydatasus
run_all_services.bat test
```

## Opção 3️⃣ Python
```bash
cd C:\dev\easydatasus
python run_all_services.py --test
```

---

## ✅ O que acontece automaticamente

1. ✅ Inicia **ClickHouse** (banco com 140k registros)
2. ✅ Inicia **Ollama** (LLM local)
3. ✅ Inicia **FastAPI** (API em http://localhost:8000)
4. ✅ Executa as **68 questões SEIDIG** (3 replicações = 204 testes)

---

## 📊 URLs após iniciar

| Serviço | URL |
|---------|-----|
| **API** | http://localhost:8000 |
| **Documentação** | http://localhost:8000/docs |
| **ClickHouse** | http://localhost:9000 |

---

## 🧪 Testar uma pergunta manualmente

```bash
# Via cURL
curl -X POST "http://localhost:8000/api/query/ask" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quantos casos de SRAG foram notificados?",
    "model": "deepseek-local",
    "dataset": "surtos-srag"
  }'

# Ou abra: http://localhost:8000/docs (Swagger UI)
```

---

## 📋 Testes Específicos

```bash
# Todas as 68 questões
python test_68_questoes_seidig.py

# Apenas COVID-19
python test_68_questoes_seidig.py --dataset covid-19-vacinacao

# Apenas SRAG
python test_68_questoes_seidig.py --start 31 --end 45

# Detalhado
python test_68_questoes_seidig.py --verbose
```

---

**Mais detalhes**: Leia [SETUP_AUTOMACAO.md](./SETUP_AUTOMACAO.md)
