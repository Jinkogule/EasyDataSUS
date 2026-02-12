# Metadata - Estrutura de Datasets

Esta pasta contém os **esquemas (schemas)** de cada dataset suportado pelo EasyDataSUS.

## Estrutura

```
metadata/
└── datasets/
    ├── vacinacao-covid/
    │   ├── schema.json      # Schema das 32 colunas
    │   └── README.md        # Documentação do dataset
    ├── dengue-2024/         # (Futuro)
    │   └── schema.json
    └── influenza-2025/      # (Futuro)
        └── schema.json
```

## Como Carregar um Dataset

```python
from metadata.loader import load_metadata

# Carrega o schema padrão (vacinacao-covid)
metadata = load_metadata()

# Carrega um schema específico
metadata = load_metadata("dengue-2024")
metadata = load_metadata("influenza-2025")
```

## Estrutura do Schema

Cada `schema.json` deve ser um array de objetos com:

```json
[
  {
    "nome": "document_id",
    "tipo": "string",
    "descricao": "ID único do documento"
  },
  ...
]
```

## Adicionando Novo Dataset

1. **Criar pasta**:
   ```
   mkdir -p metadata/datasets/seu-dataset/
   ```

2. **Criar schema.json** com descrição das colunas

3. **Usar na aplicação**:
   ```python
   metadata = load_metadata("seu-dataset")
   ```

4. **Correspondência de dados**:
   - Crie também `data/datasets/seu-dataset/` com os dados
   - Certifique-se que as colunas do CSV correspondem ao schema

## Datasets Suportados

| Dataset | Status | Descrição |
|---------|--------|-----------|
| `vacinacao-covid` | ✅ Ativo | Vacinação COVID-19 (AC, ES) - 390K+ registros |
| `dengue-2024` | ⏳ Planejado | Casos de Dengue 2024 |
| `influenza-2025` | ⏳ Planejado | Casos de Influenza 2025+ |

## Notas Importantes

- **Nome do dataset**: Deve ser o mesmo em `metadata/datasets/` e `data/datasets/`
- **Arquivo schema**: Sempre nomeado como `schema.json`
- **Arquivo de dados**: Pode ter qualquer nome `.csv` dentro do dataset folder
- **Backward compatibility**: Código que não especifica dataset usa "vacinacao-covid"
