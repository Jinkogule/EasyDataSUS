# Dataset: Vacinação COVID-19

## Descrição
Recorte local de registros de vacinação contra a COVID-19 utilizado pelo protótipo.

## Arquivos
- `vacinacao-covid.csv` - arquivo utilizado pela configuração atual

## Formato
- **Delimitador**: Ponto-e-vírgula (`;`)
- **Encoding**: UTF-8
- **Linhas**: aproximadamente 390 mil registros no recorte atual
- **Colunas**: 32 (correspondentes ao schema.json em metadata/)

## Carregamento
```python
from etl.load_csv import load_csv

# Carrega dados deste dataset
load_csv(dataset="covid-19-vacinacao")

# Sem argumento, limpa e recarrega todos os datasets configurados
load_csv()
```

## Adição de Novos Datasets
1. Crie uma pasta `data/datasets/{novo-dataset}/`
2. Coloque o arquivo CSV dentro (ex: `dengue-ac-es.csv`)
3. Use `load_csv(dataset="{novo-dataset}")` para carregá-lo

Estrutura esperada:
```
data/datasets/
├── covid-19-vacinacao/
│   └── vacinacao-ac-es.csv
├── dengue-2024/
│   └── dengue-ac-es.csv
└── influenza-2025/
    └── influenza-ac-es.csv
```

## Truncamento Automático
A função `load_csv()` sem argumentos substitui os dados de todas as tabelas
configuradas. Use `load_csv(dataset="covid-19-vacinacao")` para substituir
somente a tabela de vacinação.
