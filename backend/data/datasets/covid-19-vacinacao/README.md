# Dataset: Vacinação COVID-19

## Descrição
Dados de vacinação COVID-19 dos estados de Acre (AC) e Espírito Santo (ES).

## Arquivos
- `vacinacao-ac-es.csv` - 390.911+ registros de aplicação de vacinas

## Formato
- **Delimitador**: Ponto-e-vírgula (`;`)
- **Encoding**: UTF-8
- **Linhas**: 390.911 registros (AC + ES)
- **Colunas**: 32 (correspondentes ao schema.json em metadata/)

## Carregamento
```python
from etl.load_csv import load_csv

# Carrega dados deste dataset
load_csv(dataset="covid-19-vacinacao")

# Ou use o padrão (covid-19-vacinacao é o default)
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
A função `load_csv()` automaticamente executará TRUNCATE TABLE vacinacao 
ANTES de carregar novos dados, evitando duplicações.
