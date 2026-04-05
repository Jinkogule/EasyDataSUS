# 🎯 Guia de Integração Frontend - Roteamento por Dataset

## Visão Geral

O sistema agora suporta **múltiplos datasets com roteamento inteligente**. Quando o usuário seleciona uma pergunta pré-pronta, o frontend sabe qual dataset usar, garantindo escalabilidade.

---

## 🔄 Fluxo de Integração

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (React/Vue)                   │
└────────────────────┬────────────────────────────────────────┘
                     │
          ┌──────────▼──────────┐
          │  GET /api/questions │  ← Listar perguntas pré-prontas
          └──────────┬──────────┘
                     │
     ┌───────────────▼───────────────┐
     │  Usuário seleciona pergunta   │
     │  (mostra com dataset asociado)│
     └───────────────┬───────────────┘
                     │
          ┌──────────▼────────────┐
          │  POST /api/ask        │  ← Envia pergunta + dataset
          │  {                    │
          │    question: "...",   │
          │    dataset: "...covid"│
          │  }                    │
          └──────────┬────────────┘
                     │
          ┌──────────▼──────────┐
          │  ClickHouse (SQL)   │
          │  + LLM Ollama       │
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │  Resposta JSON      │
          │  {                  │
          │    dataset: "...",  │
          │    sql: "...",      │
          │    insight: "...",  │
          │    data: [...]      │
          │  }                  │
          └─────────────────────┘
```

---

## 1️⃣ Listar Perguntas Disponíveis

### Endpoint

```http
GET /api/questions
GET /api/questions?dataset=vacinacao-covid
GET /api/questions/{dataset_id}
```

### Exemplo - React

```javascript
// Componente que lista perguntas pré-prontas
import { useEffect, useState } from 'react';

function QuestionsList() {
  const [datasets, setDatasets] = useState([]);

  useEffect(() => {
    // [1] Buscar perguntas do backend
    fetch('http://localhost:8000/api/questions')
      .then(r => r.json())
      .then(data => {
        console.log('Datasets disponíveis:', data.total_datasets);
        setDatasets(data.datasets);
      });
  }, []);

  return (
    <div>
      {datasets.map(dataset => (
        <div key={dataset.dataset_id}>
          <h2>{dataset.theme_color} {dataset.theme_name}</h2>
          <p>{dataset.description}</p>
          
          <ul>
            {dataset.questions.map(q => (
              <li 
                key={q.id}
                onClick={() => handleSelectQuestion(q, dataset.dataset_id)}
              >
                {q.question}
                <small>{q.category}</small>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
```

### Resposta

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
      "questions": [
        {
          "id": "vac-001",
          "theme": "Quantidade Total",
          "question": "Quantas vacinas foram aplicadas no Brasil?",
          "description": "Total de doses...",
          "category": "statistics"
        }
      ]
    }
  ]
}
```

---

## 2️⃣ Executar Pergunta com Dataset

### Exemplo - Pergunta Pré-Pronta

Quando usuário clica em uma pergunta pré-pronta, **enviar o dataset junto**:

```javascript
async function handleSelectQuestion(question, dataset) {
  // [2] Enviar pergunta + dataset para /ask
  const response = await fetch('http://localhost:8000/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: question.question,      // "Quantas vacinas em SP?"
      model: "deepseek-local",           // LLM a usar
      dataset: dataset                   // "vacinacao-covid" ← IMPORTANTE!
    })
  });

  const result = await response.json();
  console.log('SQL:', result.sql);
  console.log('Resposta:', result.insight);
  console.log('Dados:', result.data);
}
```

### Exemplo - Pergunta Customizada

Se usuário fizer pergunta customizada, deixar o backend **detectar o dataset**:

```javascript
async function handleCustomQuestion(customQuestion) {
  // Sem especificar dataset - será detectado automaticamente
  const response = await fetch('http://localhost:8000/api/ask', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      question: customQuestion,
      model: "deepseek-local"
      // dataset não especificado → será detectado
    })
  });

  const result = await response.json();
  console.log('Dataset detectado:', result.dataset);
  console.log('Resposta:', result.insight);
}
```

### Resposta

```json
{
  "question": "Quantas vacinas foram aplicadas em SP?",
  "dataset": "vacinacao-covid",
  "sql": "SELECT COUNT(*) FROM vacinacao WHERE paciente_endereco_uf = 'SP' LIMIT 10000",
  "data": [[824]],
  "insight": "Em São Paulo foram aplicadas 824 doses de vacina.",
  "success": true
}
```

---

## 3️⃣ Endpoints Auxiliares

### Detectar Dataset para Pergunta

```http
POST /api/questions/detect-dataset?question=Quantas%20vacinas%20em%20SP?
```

Útil para perguntas customizadas:

```javascript
async function detectDataset(question) {
  const response = await fetch(
    `http://localhost:8000/api/questions/detect-dataset?question=${encodeURIComponent(question)}`,
    { method: 'POST' }
  );
  
  const result = await response.json();
  return result.detected_dataset;  // "vacinacao-covid"
}
```

### Listar Datasets Disponíveis

```http
GET /api/datasets/available
```

```javascript
async function getAvailableDatasets() {
  const response = await fetch('http://localhost:8000/api/datasets/available');
  const data = await response.json();
  
  console.log('Datasets disponíveis:', data.available_datasets);
  // ["vacinacao-covid", "dengue-2024"]
}
```

---

## 📱 Componente React Completo

```javascript
import React, { useState, useEffect } from 'react';

function QueryInterface() {
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [custom, setCustom] = useState('');

  // [1] Carregar perguntas ao montar
  useEffect(() => {
    fetch('http://localhost:8000/api/questions')
      .then(r => r.json())
      .then(data => setDatasets(data.datasets));
  }, []);

  // [2] Executar pergunta selecionada
  const executeQuestion = async (question, dataset_id) => {
    setLoading(true);
    
    try {
      const response = await fetch('http://localhost:8000/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: question,
          model: "deepseek-local",
          dataset: dataset_id  // ← Dataset específico!
        })
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      console.error('Erro:', error);
      setResult({ error: error.message });
    } finally {
      setLoading(false);
    }
  };

  // [3] Executar pergunta customizada
  const executeCustom = async () => {
    if (!custom.trim()) return;
    
    setLoading(true);
    
    try {
      const response = await fetch('http://localhost:8000/api/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: custom,
          model: "deepseek-local"
          // sem dataset - detectado automaticamente
        })
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      setResult({ error: error.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="query-interface">
      <h1>EasyDataSUS - Consultas de Dados</h1>

      {/* Perguntas Pré-Prontas */}
      <section className="prebuilt-questions">
        <h2>Perguntas Pré-Prontas</h2>
        
        {datasets.map(dataset => (
          <div key={dataset.dataset_id} className="dataset-group">
            <h3>{dataset.theme_color} {dataset.theme_name}</h3>
            <p>{dataset.description}</p>

            <ul className="questions-list">
              {dataset.questions.map(q => (
                <li key={q.id}>
                  <button
                    onClick={() => executeQuestion(q.question, dataset.dataset_id)}
                    disabled={loading}
                  >
                    {q.question}
                  </button>
                  <span className="category">{q.category}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </section>

      {/* Pergunta Customizada */}
      <section className="custom-question">
        <h2>Hacer uma Pergunta Personalizada</h2>
        
        <div className="input-group">
          <input
            type="text"
            value={custom}
            onChange={e => setCustom(e.target.value)}
            placeholder="Ex: Quantas vacinas foram aplicadas no Nordeste?"
            disabled={loading}
          />
          
          <button
            onClick={executeCustom}
            disabled={loading || !custom.trim()}
          >
            {loading ? 'Processando...' : 'Enviar'}
          </button>
        </div>
      </section>

      {/* Resultado */}
      {result && (
        <section className="result">
          <h2>Resultado</h2>
          
          {result.success ? (
            <>
              <div className="dataset-info">
                <strong>Dataset:</strong> {result.dataset}
              </div>
              
              <div className="insight">
                <strong>Resposta:</strong> {result.insight}
              </div>
              
              <details>
                <summary>SQL Gerado</summary>
                <pre>{result.sql}</pre>
              </details>
              
              <details>
                <summary>Dados Brutos</summary>
                <pre>{JSON.stringify(result.data, null, 2)}</pre>
              </details>
            </>
          ) : (
            <div className="error">
              <strong>Erro:</strong> {result.error || result.insight}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

export default QueryInterface;
```

---

## 🎨 UI/UX Recomendações

### Layout de Abas

```
┌────────────────────────────────────────────────┐
│  🩹 Vacinação  │  🦟 Dengue  │  🦠 Influenza  │
├────────────────────────────────────────────────┤
│                                                │
│  • Quantas vacinas foram aplicadas?            │
│  • Qual estado recebeu mais vacinas?           │
│  • Qual fabricante foi mais utilizado?         │
│                                                │
└────────────────────────────────────────────────┘
```

### Cores por Dataset

- 🩹 **Vacinação COVID**: Azul (#007AFF)
- 🦟 **Dengue**: Vermelho (#FF3B30)
- 🦠 **Influenza**: Laranja (#FF9500)

### Estados de Carregamento

```javascript
{loading && (
  <div className="spinner">
    <span>⏳ Processando sua pergunta...</span>
    <p>Gerando SQL → Executando → Interpretando</p>
  </div>
)}
```

---

## 📊 Formatação de Dados

### Exemplo de Response Estruturado para UI

```javascript
function ResultDisplay({ result }) {
  if (!result.success) {
    return <ErrorMessage error={result.insight} />;
  }

  return (
    <div>
      {/* Badge de dataset */}
      <Badge dataset={result.dataset} />

      {/* Resposta em destaque */}
      <Card className="insight">
        <h3>📊 Resultado</h3>
        <p className="answer">{result.insight}</p>
      </Card>

      {/* Gráfico se houver múltiplas linhas */}
      {result.data.length > 1 && (
        <Chart data={result.data} />
      )}

      {/* SQL para curiosos */}
      <Collapsible title="Ver SQL">
        <code>{result.sql}</code>
      </Collapsible>
    </div>
  );
}
```

---

## 🔒 Segurança e Boas Práticas

1. **Validar entrada no frontend**: Não enviar perguntas muito curtas/longas
2. **Tratar erros**: Sempre verificar `success` antes de processar
3. **Rate limiting**: Implementar no frontend para evitar spam
4. **CORS**: Backend já está configurado (`allow_origins=["*"]`)

```javascript
// Boa prática
async function safeRequest(payload) {
  if (!payload.question || payload.question.length < 3) {
    throw new Error('Pergunta muito curta');
  }

  try {
    const response = await fetch('...', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Erro na requisição:', error);
    throw error;
  }
}
```

---

## 📈 Próximas Melhorias

- [ ] Cache de queries no frontend
- [ ] Histórico de perguntas do usuário
- [ ] Integração com gráficos (Chart.js, Recharts)
- [ ] Dark mode por dataset
- [ ] Sugestões de perguntas relacionadas
- [ ] Exportar resultado (CSV, PDF)
- [ ] Compartilhar query via link

---

**Status:** ✅ Endpoints produção-ready  
**Próximo:** Implementar frontend React/Vue
