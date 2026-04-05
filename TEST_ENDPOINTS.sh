#!/usr/bin/env bash
# Cheat Sheet - Testar novos endpoints

echo "=========================================="
echo "🧪 TESTANDO NOVOS ENDPOINTS"
echo "=========================================="

# 1. Listar TODAS as perguntas pré-prontas
echo -e "\n[1] GET /api/questions - Todas as perguntas"
curl http://localhost:8000/api/questions | jq . | head -30

# 2. Listar perguntas de um dataset específico
echo -e "\n\n[2] GET /api/questions/vacinacao-covid - Apenas vacinação"
curl http://localhost:8000/api/questions/vacinacao-covid | jq . | head -30

# 3. Listar datasets disponíveis
echo -e "\n\n[3] GET /api/datasets/available - Datasets no sistema"
curl http://localhost:8000/api/datasets/available | jq .

# 4. Executar pergunta pré-pronta COM dataset
echo -e "\n\n[4] POST /api/ask - Pergunta pré-pronta com dataset"
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quantas vacinas foram aplicadas em SP?",
    "model": "deepseek-local",
    "dataset": "vacinacao-covid"
  }' | jq .

# 5. Executar pergunta customizada (detecta dataset)
echo -e "\n\n[5] POST /api/ask - Pergunta customizada (detecção automática)"
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Qual estado teve mais casos de dengue?",
    "model": "deepseek-local"
  }' | jq .

# 6. Testar detecção de dataset
echo -e "\n\n[6] POST /api/questions/detect-dataset - Detectar dataset"
curl -X POST "http://localhost:8000/api/questions/detect-dataset?question=Quantas%20vacinas%20em%20SP?" | jq .

echo -e "\n=========================================="
echo "✅ TESTES COMPLETOS"
echo "=========================================="
