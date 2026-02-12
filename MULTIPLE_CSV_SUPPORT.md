# 📁 Suporte a Múltiplos CSVs por Dataset

## ✅ Alteração Implementada

O `etl/load_csv.py` foi atualizado para **carregar TODOS os arquivos CSV de um dataset**, não apenas o primeiro.

---

## Como Funciona Agora

### Antes ❌
```
data/datasets/vacinacao-covid/
├── vacinacao-ac-es.csv       ← Carregava apenas isso
├── vacinacao-sp.csv          ← Ignorava
└── vacinacao-rj.csv          ← Ignorava
```

### Depois ✅
```
data/datasets/vacinacao-covid/
├── vacinacao-ac-es.csv       ← Carrega todos
├── vacinacao-sp.csv          ← AMBOS são processados
└── vacinacao-rj.csv          ← E consolidados na tabela
```

---

## Uso

### Carregar TODOS os CSVs de um dataset
```bash
cd backend
python etl/load_csv.py
# Carrega TODOS os CSVs em data/datasets/vacinacao-covid/
```

### Carregar todos de outro dataset
```bash
python -c "from etl.load_csv import load_csv; load_csv(dataset='dengue-2024')"
# Carrega TODOS os CSVs em data/datasets/dengue-2024/
```

### Carregar um arquivo específico (compatível)
```bash
python -c "from etl.load_csv import load_csv; load_csv('/path/to/custom.csv')"
# Carrega apenas esse arquivo
```

---

## O Que Mudou no Código

### 1️⃣ Detecção de Múltiplos Arquivos
```python
# ANTES: csv_files[0]  ← Apenas primeiro
# DEPOIS:
csv_files = sorted(list(base_path.glob("*.csv")))  # ← TODOS!
```

### 2️⃣ Loop Para Carregar Cada Um
```python
for file_idx, csv_file in enumerate(csv_files, 1):
    # Processa vacinacao-ac-es.csv
    # Processa vacinacao-sp.csv
    # Processa vacinacao-rj.csv
    # ... todos em sequência
```

### 3️⃣ TRUNCATE Uma Única Vez
```python
# Se múltiplos arquivos, limpa tabela apenas uma vez
if len(csv_files) > 1:
    client.command("TRUNCATE TABLE vacinacao")
    # Então insere todos os arquivos sem deletar um do outro
```

### 4️⃣ Estatísticas Consolidadas
```python
total_rows_all = 0
total_errors_all = 0

# Ao final:
logger.info(f"✅ Total de arquivos: {len(csv_files)}")
logger.info(f"✅ Total carregado: {total_rows_all}")  ← Soma de todos
logger.info(f"📍 Total na tabela: {total}")            ← Final consolidado
```

---

## Exemplo Prático

**Cenário**: Você tem dados de vacinação de 3 regiões em CSVs separados

```bash
mkdir -p data/datasets/vacinacao-covid

# Adicione 3 arquivos
data/datasets/vacinacao-covid/
├── vacinacao-ac-es.csv       (100K registros)
├── vacinacao-sp.csv          (250K registros)
└── vacinacao-rj.csv          (150K registros)
```

**Execute:**
```bash
python etl/load_csv.py
```

**Resultado:**
```
📂 Encontrados 3 arquivo(s) CSV no dataset 'vacinacao-covid':
   • vacinacao-ac-es.csv
   • vacinacao-rj.csv
   • vacinacao-sp.csv

[1/3] Carregando: vacinacao-ac-es.csv
✅ CSV convertido: 100000 linhas válidas

[2/3] Carregando: vacinacao-rj.csv
✅ CSV convertido: 150000 linhas válidas

[3/3] Carregando: vacinacao-sp.csv
✅ CSV convertido: 250000 linhas válidas

📊 RESUMO FINAL DE CARGA
✅ Total de arquivos processados: 3
✅ Total de linhas carregadas: 500000
📍 Total de registros na tabela: 500000
```

---

## Benefícios

✅ **Escalável**: Adiciona novo CSV? Sistema detecta automaticamente
✅ **Sem duplicação**: Truncate apenas uma vez, inserts sequenciais
✅ **Consolidado**: Estatísticas mostram total de TODOS os arquivos
✅ **Backward Compatible**: Código antigo que passava arquivo específico ainda funciona

---

## Para Adicionar Novo Dataset com Múltiplos CSVs

```bash
# 1. Criar pasta
mkdir -p data/datasets/internacao-uti

# 2. Colocar todos os CSVs
cp file1.csv data/datasets/internacao-uti/
cp file2.csv data/datasets/internacao-uti/
cp file3.csv data/datasets/internacao-uti/

# 3. Rodar carregamento
python -c "from etl.load_csv import load_csv; load_csv(dataset='internacao-uti')"

# PRONTO! Todos os 3 arquivos foram consolidados na tabela internacao_uti
```
