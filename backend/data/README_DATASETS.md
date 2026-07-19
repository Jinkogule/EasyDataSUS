# Data - Estrutura de Datasets

Esta pasta contém os **arquivos de dados (CSVs)** para cada dataset suportado por EasyDataSUS.

## Estrutura

```
data/
└── datasets/
    ├── covid-19-vacinacao/
    │   ├── vacinacao-ac-es.csv  # Data file (390K+ registros)
    │   └── README.md             # Documentação
    ├── dengue-2024/              # (Futuro)
    │   └── dengue-ac-es.csv
    └── influenza-2025/           # (Futuro)
        └── influenza-ac-es.csv
```

## Como Carregar um Dataset

```python
from etl.load_csv import load_csv

# Limpa e recarrega todos os datasets configurados
load_csv()

# Carrega um dataset específico
load_csv(dataset="leitos")
load_csv(dataset="surtos-srag")

# Ou especifique o caminho completo
load_csv("/path/to/custom.csv", dataset="leitos")
```

## Formato dos Arquivos CSV

- **Delimitador**: Ponto-e-vírgula (`;`)
- **Encoding**: UTF-8
- **Header**: Primeira linha com nomes de colunas
- **Linhas**: Uma por registro

**Exemplo**:
```csv
document_id;paciente_id;paciente_idade;...
DOC-001;PAC-001;45;...
DOC-002;PAC-002;32;...
```

## processo de Carga

1. **Validação**: Verifica se arquivo existe
2. **Truncate**: Limpa tabela ClickHouse para evitar duplicações
3. **Parsing**: Converte datas, números, textos e valores nulos
4. **Insert**: Envia os dados em lotes para o ClickHouse
5. **Verificação**: Exibe estatísticas de carga

## Adicionando Novo Dataset

1. **Criar pasta**:
   ```powershell
   mkdir data/datasets/seu-dataset/
   ```

2. **Adicionar CSV**:
   - Coloque o arquivo `.csv` na pasta
   - Certifique-se do encoding UTF-8 e delimitador `;`

3. **Criar metadata correspondente**:
   - `metadata/datasets/seu-dataset/schema.json`

4. **Usar na aplicação**:
   ```python
   load_csv(dataset="seu-dataset")
   ```

## Datasets Suportados

| Dataset | Arquivo | Status | Registros |
|---------|---------|--------|-----------|
| `covid-19-vacinacao` | vacinacao-ac-es.csv | ✅ Ativo | 390.911+ |
| `dengue-2024` | dengue-ac-es.csv | ⏳ Planejado | TBD |
| `influenza-2025` | influenza-ac-es.csv | ⏳ Planejado | TBD |

## Tratamento de Erros

- **Arquivo não encontrado**: Verifique se o CSV existe em `data/datasets/{dataset}/`
- **Coluna faltante**: Verifique correspondência com `schema.json`
- **Erro de encoding**: Certifique-se de usar UTF-8
- **Erros de parse**: Verifique delimitador (`;`) e tipo de dato

## Performance

- Sem argumento, todas as tabelas configuradas são limpas e recarregadas
- Com `dataset=...`, somente a tabela correspondente é substituída
- A pré-validação ocorre antes de qualquer TRUNCATE
- Logging detalhado mostra progresso
- ~10K linhas/segundo em ambiente Docker

## Exemplo Completo

```python
# 1. Carregar dados
from etl.load_csv import load_csv
load_csv(dataset="covid-19-vacinacao")

# 2. Usar em queries
from services.sql_service import generate_sql
from db.clickhouse import run_query
from metadata.loader import load_metadata

metadata = load_metadata("covid-19-vacinacao")
sql = "SELECT COUNT(*) FROM vacinacao WHERE paciente_endereco_uf='SP'"
result = run_query(sql)
print(result)  # [824]
```

## Escalabilidade

Esta estrutura permite:
- ✅ Múltiplos datasets coexistindo
- ✅ Fácil adição de novos datasets
- ✅ TRUNCATE seletivo por dataset
- ✅ Queries entre datasets por relacionamentos semânticos cadastrados
- ✅ Versionamento de datasets (ex: dengue-2023, dengue-2024)
