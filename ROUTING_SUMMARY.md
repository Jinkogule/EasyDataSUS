# 📊 Resumo: Roteamento Inteligente por Dataset

## 🎯 Problema Identificado

Com a refatoração para múltiplos datasets, surgiu um **problema crítico de escalabilidade**:

> **Como o sistema sabe qual dataset usar quando uma pergunta é feita?**

Existem basicamente 3 cenários:

1. **Pergunta pré-pronta** (frontend)
   - Usuário clica em "Quantas vacinas em SP?"
   - Frontend sabe que é sobre Vacinação COVID
   - Deve informar o dataset ao backend

2. **Pergunta customizada** (frontend)
   - Usuário digita "Quantos casos de dengue?"
   - Frontend NÃO sabe o dataset
   - Backend deve **detectar automaticamente**

3. **Query programática** (API)
   - Sistema externo faz pergunta
   - Pode especificar dataset ou deixar detectar

---

## ✅ Solução Implementada

Criamos um **sistema de roteamento inteligente com 4 camadas**:

### 1️⃣ Perguntas Pré-Prontas Associadas a Datasets

**Arquivo**: [routes/questions.py](backend/routes/questions.py)

```python
PREBUILT_QUESTIONS = {
    "vacinacao-covid": {
        "theme_color": "🩹",
        "theme_name": "Vacinação COVID-19",
        "questions": [
            {
                "id": "vac-002",
                "question": "Quantas vacinas foram aplicadas em SP?",
                "dataset": "vacinacao-covid"
                # ↑ Dataset associado!
            }
        ]
    },
    "dengue-2024": { ... },
    "influenza-2025": { ... }
}
```

Cada pergunta tem:
- `id`: Identificador único
- `question`: Texto da pergunta
- `dataset`: Dataset associado
- `category`: Categoria ("statistics", "regional", etc)
- `theme`: Tema ("Por Estado", "Quantidade Total", etc)

### 2️⃣ Endpoints de Descoberta

**Novos Endpoints**:

| Método | Endpoint | Proposito |
|--------|----------|-----------|
| `GET` | `/api/questions` | Lista todas perguntas pré-prontas |
| `GET` | `/api/questions/{dataset}` | Perguntas de um dataset específico |
| `GET` | `/api/questions/categories/{dataset}` | Agrupa perguntas por tema |
| `POST` | `/api/questions/detect-dataset` | Detecta dataset para pergunta |
| `GET` | `/api/datasets/available` | Lista datasets no sistema |

### 3️⃣ Detecção Automática de Dataset

**Arquivo**: [routes/query.py](backend/routes/query.py)

```python
def _detect_dataset_for_question(question: str) -> Optional[str]:
    """
    Usa palavras-chave para detectar dataset.
    
    Exemplo:
        "Quantas vacinas em SP?" → "vacinacao-covid"
        "Casos de dengue?" → "dengue-2024"
    """
    keywords_map = {
        "vacinacao-covid": ["vacina", "doses", "imunização"],
        "dengue-2024": ["dengue", "mosquito", "vetor"],
        "influenza-2025": ["gripe", "influenza", "h1n1"]
    }
    # ... busca por keywords ...
```

### 4️⃣ Endpoint `/ask` com Roteamento

**Arquivo**: [routes/query.py](backend/routes/query.py) - Endpoint atualizado

```python
@router.post("/ask")
def ask(req: AskRequest):
    """
    ANTES:
    {
      "question": "...",
      "model": "deepseek-local"
    }
    
    AGORA (com roteamento):
    {
      "question": "...",
      "model": "deepseek-local",
      "dataset": "vacinacao-covid"  ← NOVO!
      // Se não especificar, detecta automaticamente
    }
    """
    
    # Lógica:
    # 1. Se dataset fornecido → usar direto
    # 2. Se não → detectar do conteúdo
    # 3. Se não detectado → padrão (vacinacao-covid)
    
    dataset_to_use = req.dataset or \
                      _detect_dataset_for_question(req.question) or \
                      "vacinacao-covid"
    
    metadata = load_metadata(dataset_to_use)  # ← Carrega schema correto!
    # ... resto da lógica ...
```

---

## 📱 Fluxo Frontend

### Fluxo 1: Pergunta Pré-Pronta

```javascript
// [1] Frontend lista perguntas
GET /api/questions
// Response: lista de datasets com perguntas associadas

// [2] Usuário clica em pergunta
"Quantas vacinas em SP?" (de "vacinacao-covid")

// [3] Frontend envia para /ask COM dataset
POST /api/ask
{
  "question": "Quantas vacinas em SP?",
  "model": "deepseek-local",
  "dataset": "vacinacao-covid"  ← Frontend sabe qual dataset!
}

// [4] Backend processa com schema correto
✅ Sucesso
```

### Fluxo 2: Pergunta Customizada

```javascript
// [1] Usuário digita pergunta manual
"Quantos óbitos por dengue?"

// [2] Frontend envia SEM dataset
POST /api/ask
{
  "question": "Quantos óbitos por dengue?",
  "model": "deepseek-local"
  // sem dataset!
}

// [3] Backend detecta
"dengue-2024" ← Encontrado por keywords!

// [4] Backend processa com schema correto
✅ Sucesso
```

---

## 🎯 Benefícios da Solução

| Aspecto | Benefício |
|---------|-----------|
| **Escalabilidade** | Novos datasets = apenas perguntas + pasta |
| **Descoberta** | Frontend descobre datasets via API |
| **Roteamento** | Pergunta sempre vai para dataset correto |
| **Backward Compat** | Código antigo ainda funciona (detecção fallback) |
| **Experiência UX** | Perguntas agrupadas por tema/dataset |
| **Manutenção** | Fácil adicionar/remover datasets |

---

## 📋 Estrutura de Dados

### AskRequest (atualizado)

```python
class AskRequest(BaseModel):
    question: str                    # Pergunta em português
    model: str = "deepseek-local"   # LLM a usar
    dataset: Optional[str] = None   # ← NOVO: Dataset (opcional)
```

### Response `/ask` (atualizado)

```json
{
  "question": "Quantas vacinas em SP?",
  "dataset": "vacinacao-covid",           // ← NOVO: Qual foi usado
  "sql": "SELECT COUNT(*) FROM vacinacao...",
  "data": [[824]],
  "insight": "Em São Paulo foram aplicadas 824 doses...",
  "success": true
}
```

### Response `/questions`

```json
{
  "total_datasets": 3,
  "datasets": [
    {
      "dataset_id": "vacinacao-covid",
      "theme_color": "🩹",
      "theme_name": "Vacinação COVID-19",
      "description": "Dados de vacinação...",
      "question_count": 5,
      "questions": [...]
    }
  ]
}
```

---

## 🔍 Detecção de Dataset

### Como Funciona

1. **Análise de Palavras-Chave**
   ```
   "Quantas vacinas" → busca por "vacina" → vacinacao-covid
   "Casos dengue" → busca por "dengue" → dengue-2024
   ```

2. **Scoring**
   ```
   vacinacao-covid: 2 matches (vacina, aplicadas)
   dengue-2024: 0 matches
   influenza-2025: 0 matches
   → Winner: vacinacao-covid
   ```

3. **Confiança**
   ```
   Confiança = matches_dataset_vencedor / total_matches
   Exemplo: 2/2 = 100%
   ```

### Endpoint de Teste

```bash
curl -X POST "http://localhost:8000/api/questions/detect-dataset?question=Quantas%20vacinas?"

Response:
{
  "question": "Quantas vacinas?",
  "detected_dataset": "vacinacao-covid",
  "confidence": 1.0,
  "score": 1,
  "alternatives": []
}
```

---

## 📊 Arquitetura Escalável

```
┌─────────────────────────────────────┐
│   Frontend (React/Vue)              │
│  Mostra perguntas por dataset       │
└────────────┬────────────────────────┘
             │
      ┌──────┴─────────┐
      │                │
 ┌────▼────┐    ┌─────▼──────┐
 │ List    │    │ Ask        │
 │ Questions    │ (routing)  │
 └────┬────┘    └─────┬──────┘
      │               │
      └───────┬───────┘
              │
    ┌─────────▼──────────┐
    │  Router (Dataset)  │
    │  - Detecta        │
    │  - Valida         │
    │  - Roteia         │
    └─────────┬──────────┘
              │
    ┌─────────▼──────────────────┐
    │  Metadata Loader           │
    │  load_metadata(dataset_id) │
    └─────────┬──────────────────┘
              │
    ┌─────────▼──────────────────┐
    │  SQL Generation (LLM)      │
    │  generate_sql(meta, llm)   │
    └─────────┬──────────────────┘
              │
    ┌─────────▼──────────────────┐
    │  Query Execution           │
    │  ClickHouse                │
    └─────────┬──────────────────┘
              │
    ┌─────────▼──────────────────┐
    │  Interpretation (LLM)      │
    │  interpret_result()        │
    └────────────────────────────┘
```

---

## 🧪 Testes Inclusos

1. `test_quick_endpoints.py` - Teste rápido dos endpoints
2. `test_frontend_integration.py` - Simula fluxo frontend completo
3. `test_scalability.py` - Valida estrutura de datasets

---

## 📝 Mudanças Implementadas

### Novos Arquivos

- ✅ `routes/questions.py` - Endpoint de perguntas (230+ linhas)
- ✅ `FRONTEND_INTEGRATION.md` - Guia de integração frontend
- ✅ `test_quick_endpoints.py` - Testes básicos
- ✅ `test_frontend_integration.py` - Simulação frontend

### Arquivos Modificados

- ✅ `main.py` - Importa novo router `questions`
- ✅ `routes/query.py` - Adiciona parâmetro `dataset` ao `AskRequest`
- ✅ `is_valid_sql()` - Agnóstica quanto ao dataset (recebe dataset_id)

---

## 🚀 Como Usar

### 1. Iniciar o API

```bash
cd backend
python main.py
```

### 2. Listar Perguntas

```bash
curl http://localhost:8000/api/questions | jq .
```

### 3. Executar Pergunta Pré-Pronta

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quantas vacinas em SP?",
    "dataset": "vacinacao-covid"
  }'
```

### 4. Executar Pergunta Customizada

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Quantos casos de dengue em RJ?"
  }'
# Dataset será detectado automaticamente
```

---

## 📈 Próximas Etapas

1. ✅ Sistema de roteamento implementado
2. ⏳ Frontend React/Vue com integração
3. ⏳ Dashboard com gráficos por dataset
4. ⏳ Suporte a queries entre datasets
5. ⏳ Cache de perguntas frequentes
6. ⏳ Analytics de usage por dataset

---

## ✅ Status

- **Roteamento**: ✅ Implementado e testado
- **Perguntas Pré-prontas**: ✅ 13 perguntas em 3 datasets
- **Detecção Automática**: ✅ Funcional
- **Validação SQL**: ✅ Agnóstica por dataset
- **Documentação**: ✅ Guia frontend incluído

**Data**: 2026-04-05  
**Versão**: 1.2.0 (Roteamento por Dataset)
