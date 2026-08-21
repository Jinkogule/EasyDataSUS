# EasyDataSUS

Natural-language query system for selected public health datasets from DataSUS. The backend selects datasets, retrieves semantic metadata, generates read-only SQL, validates the query, executes it in ClickHouse and returns factual responses with execution/evaluation metadata.

## Current scope

Supported datasets:

| Dataset | ClickHouse table |
|---|---|
| `covid-19-vacinacao` | `vacinacao` |
| `leitos` | `leitos` |
| `surtos-srag` | `srag` |
| `atencao-basica` | `atencao_basica` |

Supported cross-dataset relationships:

| Relationship | Datasets |
|---|---|
| `vacinacao_leitos_uf` | vaccination + hospital beds |
| `srag_ubs_municipio_notificacao` | SARI/SRAG + primary care facilities |

## Setup

From the project root:

```powershell
docker-compose up -d
```

Inside `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python etl/load_csv.py
python main.py
```

`python etl/load_csv.py` clears and reloads every configured dataset. To reload a single dataset:

```powershell
python etl/load_csv.py --dataset leitos
```

## Ask a question

```powershell
curl -X POST "http://localhost:8000/api/ask" `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"Quantas doses de vacina contra a COVID-19 foram registradas no conjunto de dados carregado?\"}"
```

Responses include `sql`, `data`, `insight`, `timing_s` and `evaluation_metrics`.

## Run the 68-question benchmark

From the project root:

```powershell
python backend/tests/benchmark_68_questoes_seidig.py
```

Examples:

```powershell
python backend/tests/benchmark_68_questoes_seidig.py --start 61 --end 68
python backend/tests/benchmark_68_questoes_seidig.py --dataset leitos
```

The aggregated result is saved as `test_results_68_questoes.json`.

## Automated tests

```powershell
python -m pytest backend/tests
```

## Documentation

Current documentation is in `docs`:

- `docs/SISTEMA_ATUAL.md`
- `docs/EXPERIMENTOS_METRICAS.md`
- `docs/PERGUNTAS_SEIDIG_68.md`

## License

MIT.
