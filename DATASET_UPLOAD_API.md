# 📤 Upload e Gerenciamento de Datasets

## Overview

O sistema agora suporta upload de novos arquivos CSV via API REST! Não é mais necessário copiar manualmente arquivos para pastas.

---

## Endpoints Administrativos

### 1️⃣ Upload de CSV (Com Validação)

```http
POST /api/admin/datasets/upload?dataset=vacinacao-covid
Content-Type: multipart/form-data

file: <arquivo.csv>
```

**Exemplo com cURL:**
```bash
curl -X POST "http://localhost:8000/api/admin/datasets/upload?dataset=vacinacao-covid" \
  -F "file=@vacina-sp.csv"
```

**Exemplo com Python:**
```python
import requests

url = "http://localhost:8000/api/admin/datasets/upload"
params = {"dataset": "vacinacao-covid"}
files = {"file": open("vacina-sp.csv", "rb")}

response = requests.post(url, params=params, files=files)
print(response.json())

# Resposta:
# {
#   "success": true,
#   "dataset": "vacinacao-covid",
#   "filename": "vacina-sp.csv",
#   "rows_loaded": 250000,
#   "message": "Dataset 'vacinacao-covid' carregado com sucesso! (250000 linhas)"
# }
```

**Exemplo com fetch (Frontend JavaScript/React):**
```javascript
const formData = new FormData();
formData.append("file", fileInput.files[0]);

const response = await fetch(
  `http://localhost:8000/api/admin/datasets/upload?dataset=vacinacao-covid`,
  { method: "POST", body: formData }
);

const result = await response.json();
console.log(result);
```

---

### 2️⃣ Validar CSV Antes de Upload

Teste o schema sem fazer upload ainda:

```bash
curl -X POST "http://localhost:8000/api/admin/datasets/validate?dataset=vacinacao-covid" \
  -F "file=@vacina-sp.csv"
```

**Resposta:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Colunas extras no CSV (serão ignoradas): coluna_extra"],
  "rows_preview": 100
}
```

Se houver erros:
```json
{
  "valid": false,
  "errors": [
    {
      "field": "columns",
      "issue": "Colunas faltando: paciente_id, vacina_nome",
      "suggestion": "Adicione as colunas requeridas ao CSV"
    }
  ],
  "warnings": [],
  "rows_preview": 0
}
```

---

### 3️⃣ Listar Todos os Datasets

```bash
curl http://localhost:8000/api/admin/datasets/available
```

**Resposta:**
```json
[
  {
    "id": "vacinacao-covid",
    "name": "vacinacao-covid",
    "description": "Dados de vacinação contra COVID-19 no Brasil",
    "table_name": "vacinacao",
    "csv_count": 2,
    "total_size_mb": 385.5
  },
  {
    "id": "dengue-2024",
    "name": "dengue-2024",
    "description": "Casos de Dengue registrados em 2024",
    "table_name": "dengue",
    "csv_count": 0,
    "total_size_mb": 0.0
  }
]
```

---

### 4️⃣ Informações de um Dataset Específico

```bash
curl http://localhost:8000/api/admin/datasets/vacinacao-covid/info
```

---

### 5️⃣ Deletar um Arquivo CSV

```bash
curl -X DELETE "http://localhost:8000/api/admin/datasets/vacinacao-covid/files/vacina-sp.csv"
```

⚠️ **Nota**: Isso remove apenas o arquivo, não os dados já carregados no ClickHouse!

---

### 6️⃣ Recarregar Dataset Completo

Se o schema mudou ou houve erro anterior:

```bash
curl -X POST "http://localhost:8000/api/admin/datasets/vacinacao-covid/reload"
```

Recarrega TODOS os CSVs da pasta.

---

## 🎯 Fluxo Completo do Frontend

### Opção 1: Upload Simples

```javascript
// 1. Usuário seleciona arquivo
const file = document.getElementById("fileInput").files[0];

// 2. Fazer upload
const formData = new FormData();
formData.append("file", file);

const response = await fetch(
  `http://localhost:8000/api/admin/datasets/upload?dataset=vacinacao-covid`,
  { method: "POST", body: formData }
);

const result = await response.json();

if (result.success) {
  alert(`✅ ${result.rows_loaded} linhas carregadas!`);
} else {
  alert(`❌ ${result.message}`);
}
```

### Opção 2: Upload com Validação Prévia

```javascript
// 1. Validar primeiro
const validateResponse = await fetch(
  `http://localhost:8000/api/admin/datasets/validate?dataset=vacinacao-covid`,
  { method: "POST", body: formData }
);

const validation = await validateResponse.json();

if (!validation.valid) {
  // Mostrar erros
  validation.errors.forEach(err => {
    console.error(`${err.field}: ${err.issue}`);
    console.log(`Sugestão: ${err.suggestion}`);
  });
  return;
}

// 2. Se válido, fazer upload
const uploadResponse = await fetch(
  `http://localhost:8000/api/admin/datasets/upload?dataset=vacinacao-covid`,
  { method: "POST", body: formData }
);

const result = await uploadResponse.json();
// ...
```

---

## ✅ O Que o Sistema Valida

Quando você faz upload, o sistema automaticamente:

1. **Verifica Schema**
   - Todas as colunas requeridas estão presentes?
   - Tipos de dados corretos?

2. **Detecta Problemas**
   - Colunas faltando
   - Colunas extras (aviso, não erro)
   - Arquivo vazio

3. **Salva Arquivo**
   - Gera nome único se duplicação
   - Coloca em `data/datasets/{dataset}/`

4. **Carrega no ClickHouse**
   - Converte o CSV para TSV
   - Valida dados durante leitura
   - Consolida com CSVs anteriores

5. **Retorna Status**
   - Sucesso/erro
   - Número de linhas carregadas
   - Mensagem amigável

---

## 📋 Estrutura de Resposta

### Sucesso
```json
{
  "success": true,
  "dataset": "vacinacao-covid",
  "filename": "vacina-sp.csv",
  "rows_loaded": 250000,
  "message": "Dataset 'vacinacao-covid' carregado com sucesso! (250000 linhas)",
  "errors": null
}
```

### Erro - Schema Inválido
```json
{
  "detail": "Validação falhou: columns: Colunas faltando: paciente_id"
}
```

### Erro - ClickHouse
```json
{
  "detail": "Erro ao carregar dados: connection timeout"
}
```

---

## 🔒 Segurança

- ✅ Path traversal bloqueado (`..` não permitido)
- ✅ Somente administradores devem ter acesso aos endpoints `/admin/*`
- ✅ CSV validado contra schema antes de inserção
- ✅ Dados sensíveis não são expostos em respostas de erro

---

## 🧪 Teste Local

```bash
# 1. Iniciar backend
cd backend
python main.py

# 2. Em outro terminal, fazer upload
curl -X POST "http://localhost:8000/api/admin/datasets/upload?dataset=vacinacao-covid" \
  -F "file=@backend/data/datasets/vacinacao-covid/vacinacao-ac-es.csv"

# 3. Verificar resultado
curl http://localhost:8000/api/admin/datasets/vacinacao-covid/info
```

---

## 📚 Frontend Integration Example (React)

```jsx
import { useState } from 'react';

function DatasetUpload() {
  const [file, setFile] = useState(null);
  const [dataset, setDataset] = useState('vacinacao-covid');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file) return;

    setLoading(true);
    
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(
        `http://localhost:8000/api/admin/datasets/upload?dataset=${dataset}`,
        { method: 'POST', body: formData }
      );

      const data = await response.json();
      
      if (response.ok) {
        setResult({
          type: 'success',
          message: `✅ ${data.rows_loaded} linhas carregadas!`
        });
      } else {
        setResult({
          type: 'error',
          message: `❌ ${data.detail || 'Erro desconhecido'}`
        });
      }
    } catch (error) {
      setResult({
        type: 'error',
        message: `❌ Erro: ${error.message}`
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2>Carregar Dataset</h2>
      
      <form onSubmit={handleUpload}>
        <select value={dataset} onChange={(e) => setDataset(e.target.value)}>
          <option value="vacinacao-covid">Vacinação COVID-19</option>
          <option value="dengue-2024">Dengue 2024</option>
          <option value="influenza-2025">Influenza 2025</option>
        </select>

        <input 
          type="file" 
          accept=".csv"
          onChange={(e) => setFile(e.target.files[0])}
          required
        />

        <button type="submit" disabled={loading}>
          {loading ? 'Carregando...' : 'Upload'}
        </button>
      </form>

      {result && (
        <div className={`result ${result.type}`}>
          {result.message}
        </div>
      )}
    </div>
  );
}

export default DatasetUpload;
```

---

## 📝 Checklist de Setup

- [ ] Backend rodando (`python main.py`)
- [ ] ClickHouse ativo e com tabelas criadas
- [ ] Credentials ClickHouse corretas em `.env`
- [ ] Datasets já têm `metadata/datasets/{dataset}/schema.json`
- [ ] Frontend preparado para fazer POST multi-part/form-data

Pronto! 🚀
