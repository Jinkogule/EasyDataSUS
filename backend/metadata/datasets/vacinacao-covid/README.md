# Dataset: Vaccinação COVID-19

## Descrição
Schema de dados para vaccinnação COVID-19 no Brasil (AC e ES).

## Arquivo Schema
- `schema.json` - Metadados das 32 colunas do dataset

## Campos Principais
- **Paciente**: Dados demográficos (idade, sexo, raça/cor, localização)
- **Estabelecimento**: Informações da unidade vacinadora
- **Vacina**: Detalhes da vacinação (tipo, fabricante, dose, data)
- **Sistema**: Origem dos dados

## Uso
```python
from metadata.loader import load_metadata

# Carrega metadados deste dataset
metadata = load_metadata("vacinacao-covid")

# Ou use o padrão (vacinacao-covid é o default)
metadata = load_metadata()
```

## Adição de Novos Datasets
1. Crie uma pasta `metadata/datasets/{novo-dataset}/`
2. Coloque um arquivo `schema.json` com o schema
3. Use `load_metadata("{novo-dataset}")` para carregá-lo

Exemplo: `metadata/datasets/dengue-2024/schema.json`
