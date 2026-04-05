# 🚀 Guia de Escalabilidade - EasyDataSUS

## Visão Geral da Refatoração

A estrutura foi refatorada para suportar **múltiplos datasets** sem conflitos. Agora você pode adicionar dados sobre dengue, influenza, tuberculose, etc., mantendo a mesma infraestrutura.

## Estrutura Nova (Escalável)

### Antes (Monolítica)
```
backend/
├── metadata/
│   └── vacinacao.json              # Genérico, difícil de escalar
├── data/
│   └── vacinacao-ac-es.csv         # Na raiz, sem organização
└── etl/
    └── load_csv.py                 # Função hardcoded
```

### Depois (Escalável)
```
backend/
├── metadata/
│   ├── README_DATASETS.md          # 📚 Documentação central
│   └── datasets/
│       ├── vacinacao-covid/
│       │   ├── schema.json         # Metadata do dataset
│       │   └── README.md           # Documentação específica
│       ├── dengue-2024/            # 🦟 Próximo dataset
│       │   └── schema.json
│       └── influenza-2025/         # 🦠 Futuro dataset
│           └── schema.json
├── data/
│   ├── README_DATASETS.md          # 📚 Documentação central
│   └── datasets/
│       ├── vacinacao-covid/
│       │   ├── vacinacao-ac-es.csv # 390K registros
│       │   └── README.md           # Documentação específica
│       ├── dengue-2024/            # 🦟 Dados de dengue
│       │   └── dengue-ac-es.csv
│       └── influenza-2025/         # 🦠 Dados de influenza
│           └── influenza-ac-es.csv
└── etl/
    └── load_csv.py                 # 🔧 Parametrizada por dataset
```

## Como Funciona

### 1️⃣ Carregamento de Metadados - Parametrizado

**Antes:**
```python
from metadata.loader import load_metadata
metadata = load_metadata()  # Sempre vacinacao.json
```

**Depois:**
```python
from metadata.loader import load_metadata

# Padrão (vacinacao-covid)
metadata = load_metadata()

# Dataset específico
metadata = load_metadata("dengue-2024")
metadata = load_metadata("influenza-2025")
```

### 2️⃣ Carregamento de CSV - Parametrizado

**Antes:**
```python
from etl.load_csv import load_csv
load_csv("data/vacinacao-ac-es.csv")  # Path hardcoded
```

**Depois:**
```python
from etl.load_csv import load_csv

# Padrão (busca em data/datasets/vacinacao-covid/)
load_csv()

# Dataset específico
load_csv(dataset="dengue-2024")
load_csv(dataset="influenza-2025")

# Ou com path customizado
load_csv("/path/to/file.csv", dataset="custom")
```

### 3️⃣ Código Automático - Descobre Datasets

```python
# load_csv() automaticamente:
# 1. Detecção: Procura em data/datasets/{dataset}/
# 2. Busca: Encontra o primeiro .csv na pasta
# 3. Validação: Verifica encoding UTF-8 e delimitador
# 4. Truncate: Limpa dados antigos
# 5. Carregamento: Envia para ClickHouse
```

## Adicionando Novo Dataset (Passo a Passo)

### Passo 1: Estrutura de Pastas
```powershell
# Windows PowerShell
mkdir metadata/datasets/dengue-2024
mkdir data/datasets/dengue-2024
```

### Passo 2: Schema JSON
Crie `metadata/datasets/dengue-2024/schema.json`:

```json
{
  "tabela": "dengue",
  "descricao": "Casos de Dengue no Brasil",
  "fonte": "Ministério da Saúde",
  "colunas_principais": {
    "paciente_endereco_uf": {
      "tipo": "String",
      "descricao": "Estado do paciente",
      "exemplo": "RJ"
    },
    "dengue_tipo": {
      "tipo": "String",
      "descricao": "Tipo de Dengue (1, 2, 3, 4)",
      "exemplo": "2"
    },
    "data_sintomas": {
      "tipo": "Date",
      "descricao": "Data de início dos sintomas",
      "exemplo": "2024-03-15"
    }
  }
}
```

### Passo 3: Arquivo CSV
Coloque o arquivo em `data/datasets/dengue-2024/dengue-ac-es.csv`:

```csv
paciente_id;paciente_endereco_uf;dengue_tipo;data_sintomas;...
PAC-001;RJ;2;2024-03-15;...
PAC-002;SP;1;2024-03-16;...
```

Requisitos:
- **Delimitador**: Ponto-e-vírgula (`;`)
- **Encoding**: UTF-8 sem BOM
- **Header**: Primeira linha com nomes de colunas
- **Extensão**: `.csv`

### Passo 4: Usar na Aplicação

```python
from etl.load_csv import load_csv
from services.sql_service import generate_sql
from metadata.loader import load_metadata

# Carrega dados
load_csv(dataset="dengue-2024")

# Usa em queries
metadata = load_metadata("dengue-2024")
sql = generate_sql("Quantos casos de dengue em SP?", metadata, "deepseek-local")
```

## Checklist para Novo Dataset

- [ ] **Pasta criada**: `metadata/datasets/{dataset}/`
- [ ] **Schema criado**: `metadata/datasets/{dataset}/schema.json`
- [ ] **Documentação**: `metadata/datasets/{dataset}/README.md`
- [ ] **Pasta de dados**: `data/datasets/{dataset}/`
- [ ] **CSV adicionado**: `data/datasets/{dataset}/*.csv`
- [ ] **Documentação**: `data/datasets/{dataset}/README.md`
- [ ] **Teste carregamento**: `load_csv(dataset="{dataset}")`
- [ ] **Teste query**: `generate_sql(..., load_metadata("{dataset}"), ...)`

## Exemplo Real: Adicionar Dengue 2024

```bash
# 1. Criar pasta structure
mkdir -p backend/metadata/datasets/dengue-2024
mkdir -p backend/data/datasets/dengue-2024

# 2. Adicionar schema.json (copiar de vacinacao e adaptar)
cp backend/metadata/datasets/vacinacao-covid/schema.json \
   backend/metadata/datasets/dengue-2024/schema.json
# Editar para refletir colunas de dengue

# 3. Adicionar CSV
cp ~/Downloads/dengue-ac-es.csv \
   backend/data/datasets/dengue-2024/

# 4. Testar carregamento
cd backend
python -c "
from etl.load_csv import load_csv
load_csv(dataset='dengue-2024')
print('✅ Dengue 2024 carregado!')
"
```

## Tabela de Datasets Planejados

| Dataset | Status | Colunas | Registros Estimados | Tabela ClickHouse |
|---------|--------|---------|---------------------|------------------|
| `vacinacao-covid` | ✅ Ativo | 32 | 390K | `vacinacao` |
| `dengue-2024` | ⏳ Planejado | TBD | 500K+ | `dengue` |
| `influenza-2025` | ⏳ Planejado | TBD | 300K+ | `influenza` |
| `tuberculose-2024` | ⏳ Planejado | TBD | 100K+ | `tuberculose` |
| `covid-casos` | ⏳ Planejado | TBD | 1M+ | `covid_casos` |

## Vantagens da Nova Estrutura

✅ **Escalabilidade**: Adicione datasets sem modificar código  
✅ **Isolamento**: Cada dataset é independente  
✅ **Documentação**: Cada dataset tem seu README  
✅ **Descoberta**: API descobre datasets automaticamente  
✅ **Manutenção**: Fácil identificar qual dataset usar  
✅ **Versionamento**: Suporta `dengue-2023`, `dengue-2024`, etc  
✅ **Testes**: Script de teste valida estrutura  

## Arquitetura

```
╔═══════════════════════════════════════════════════════════════╗
║                    APPLICATION LAYER                          ║
║  routes/query.py → generate_sql() → interpret_result()        ║
╠═══════════════════════════════════════════════════════════════╣
║                    METADATA LAYER                             ║
║  load_metadata("{dataset}")                                   ║
║  ├── metadata/datasets/vacinacao-covid/schema.json            ║
║  ├── metadata/datasets/dengue-2024/schema.json                ║
║  └── metadata/datasets/influenza-2025/schema.json             ║
╠═══════════════════════════════════════════════════════════════╣
║                    DATA LAYER                                 ║
║  load_csv(dataset="{dataset}")                                ║
║  ├── data/datasets/vacinacao-covid/vacinacao-ac-es.csv        ║
║  ├── data/datasets/dengue-2024/dengue-ac-es.csv               ║
║  └── data/datasets/influenza-2025/influenza-ac-es.csv         ║
╠═══════════════════════════════════════════════════════════════╣
║                    DATABASE LAYER                             ║
║  ClickHouse                                                    ║
║  ├── TABLE vacinacao (390K registros)                         ║
║  ├── TABLE dengue (planejado)                                 ║
║  └── TABLE influenza (planejado)                              ║
╚═══════════════════════════════════════════════════════════════╝
```

## Próximas Etapas Recomendadas

1. **Adicionar Dengue**: Implementar dataset de dengue 2024
2. **Queries Multi-Dataset**: Permitir joins entre datasets
3. **Validação de Schema**: Auto-validar CSVs contra schema
4. **Compressão**: Suportar `.csv.gz` para grandes arquivos
5. **Versionamento**: `metadata/datasets/vacinacao-covid/v1/schema.json`
6. **Cache**: Cachear metadados para performance

## Troubleshooting

### Erro: "Nenhum arquivo CSV encontrado"
```python
# Verifique se o arquivo existe:
import os
os.listdir("data/datasets/seu-dataset/")
# Deve conter: seu-arquivo.csv
```

### Erro: "Metadata não encontrado"
```python
# Verifique se o schema.json existe:
import os
os.path.exists("metadata/datasets/seu-dataset/schema.json")
# Deve ser: True
```

### CSV com encoding errado
```python
# Salve em UTF-8 no seu editor:
# VS Code: File → Save with Encoding → UTF-8
# Ou use PowerShell:
# Get-Content arquivo.csv -Encoding UTF8 | Set-Content arquivo.csv -Encoding UTF8
```

---

**Última atualização**: 2026-04-05  
**Status**: ✅ Refatoração Completa e Testada
