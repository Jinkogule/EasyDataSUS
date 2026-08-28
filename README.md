# EasyDataSUS

EasyDataSUS is a research-oriented computational artifact for querying selected public health datasets from DataSUS using natural language. It combines semantic metadata, hybrid SQL generation, structural validation and ClickHouse execution to support factual, read-only analytical answers over one or more public health domains.

The project is currently focused on a controlled experimental setting. Local documentation and experiment outputs are intentionally kept out of the remote repository; this README contains the relevant public setup and usage instructions.

## Scope

Supported datasets:

| Dataset | ClickHouse table | Domain |
|---|---|---|
| `covid-19-vacinacao` | `vacinacao` | COVID-19 vaccination |
| `leitos` | `leitos` | Hospital capacity |
| `surtos-srag` | `srag` | SARI/SRAG surveillance |
| `atencao-basica` | `atencao_basica` | Primary care facilities |

Supported cross-dataset relationships:

| Relationship | Datasets | Join level |
|---|---|---|
| `vacinacao_leitos_uf` | vaccination + hospital beds | State code (`UF`) |
| `srag_ubs_municipio_notificacao` | SARI/SRAG + primary care facilities | Municipality code (`IBGE`) |

## Project structure and query flow

Main backend modules:

| Path | Purpose |
|---|---|
| `backend/main.py` | Starts the FastAPI application |
| `backend/routes/query.py` | Orchestrates question processing through the `/api/ask` endpoint |
| `backend/config/datasets.py` | Registers supported datasets, table names, CSV paths and scope notes |
| `backend/metadata/datasets/*/schema.json` | Describes dataset attributes used to build SQL prompts and validate generated queries |
| `backend/metadata/relationships.json` | Defines supported cross-dataset relationships, join keys, granularity and preaggregation rules |
| `backend/services/sql_service.py` | Generates and validates single-dataset SQL |
| `backend/services/multibase_service.py` | Handles dataset selection, relationship retrieval, cross-dataset SQL generation and structural validation |
| `backend/services/result_formatter.py` | Builds factual summaries, highlights and warnings from query results |
| `backend/services/interpretation_service.py` | Produces or validates natural-language answers from factual results |
| `backend/llm/` | Contains the Ollama provider and model alias resolution |
| `backend/etl/load_csv.py` | Reloads CSV data into the existing ClickHouse tables |
| `backend/tests/benchmark_68_questoes_seidig.py` | Runs the experimental question set and records evaluation metadata |

The system uses a hybrid query strategy:

1. The API receives a natural-language question.
2. If the request does not specify a dataset, the system selects one or more datasets using heuristics and, when needed, the configured LLM.
3. For single-dataset questions, the SQL service builds a prompt from the dataset metadata, examples and dataset-specific rules. The LLM receives this prompt and returns SQL only.
4. For cross-dataset questions, the multibase service retrieves predefined relationship metadata and either generates a deterministic query for supported patterns or asks the LLM to generate SQL using the allowed tables, columns, join keys and preaggregation rules.
5. Generated SQL is sanitized, identifiers are canonicalized and the query is structurally validated before execution. The validator checks read-only access, allowed tables, allowed columns, joins and relationship constraints.
6. If LLM generation fails or produces invalid SQL, deterministic fallback rules attempt to generate a safe query for known analytical patterns.
7. ClickHouse executes the validated query, and the response formatter returns factual results, warnings, highlights and evaluation metadata.

Deterministic rules are implemented in code for recurring, well-defined analytical patterns, such as counts by state, ICU bed availability in the latest competence, neonatal ICU availability and supported cross-dataset aggregations. Non-deterministic generation is performed by the selected LLM through prompts assembled at runtime from the metadata and the user question. The LLM does not read project scripts directly.

## Requirements

- Python 3.10+
- Docker and Docker Compose
- Ollama model available in the `easydatasus-ollama` container
- DataSUS CSV files for the datasets to be loaded

The default benchmark model alias is `deepseek-local`. Other installed Ollama models can be selected with `--model`.

## Start infrastructure

From the project root:

```powershell
docker compose up -d
```

This starts:

- ClickHouse, using `init_all_tables.sql` to create the analytical tables on first initialization;
- Ollama, used by the local language-model provider.

If the ClickHouse volume already exists, Docker will not rerun the initialization script automatically. In that case, recreate the volume or apply schema changes manually before loading data.

Install at least one Ollama model inside the container before running questions or benchmarks:

```powershell
docker exec easydatasus-ollama ollama pull qwen2.5-coder:7b
```

To check installed models:

```powershell
docker exec easydatasus-ollama ollama list
```

## Prepare the backend

From the project root:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Load DataSUS CSV files

The DataSUS CSV files are external input data and must be placed under the corresponding configured folders in `backend/data/datasets` before running the loader.

Then, from `backend`:

```powershell
python etl/load_csv.py
```

This command clears and reloads every configured dataset.

To reload only one dataset:

```powershell
python etl/load_csv.py --dataset leitos
```

The loader does not create ClickHouse tables from metadata. Table creation is defined by `init_all_tables.sql`; the loader reads the existing table schema, maps CSV columns case-insensitively, converts supported values and inserts the rows.

## Run the API

From `backend`:

```powershell
python main.py
```

Example request:

```powershell
curl -X POST "http://localhost:8000/api/ask" `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"Quantas doses de vacina contra a COVID-19 foram registradas no conjunto de dados carregado?\"}"
```

Responses include the selected dataset, generated SQL, query result, factual insight, timing information and experiment-oriented evaluation metadata.

## Run the 68-question benchmark

From the project root:

```powershell
python backend/tests/benchmark_68_questoes_seidig.py
```

Run with a specific model:

```powershell
python backend/tests/benchmark_68_questoes_seidig.py --model qwen2.5-coder:7b
```

Run a subset:

```powershell
python backend/tests/benchmark_68_questoes_seidig.py --start 61 --end 68
python backend/tests/benchmark_68_questoes_seidig.py --dataset leitos
```

Benchmark outputs are saved locally in `experimentos/` with automatic versioning.

## Automated tests

```powershell
python -m pytest backend/tests
```

## License

MIT.
