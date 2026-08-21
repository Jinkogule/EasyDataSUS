# EasyDataSUS

Sistema para consulta em linguagem natural a bases públicas de saúde do DataSUS. O backend seleciona datasets, usa metadados semânticos, gera SQL de leitura, valida a consulta, executa no ClickHouse e retorna uma resposta factual acompanhada de métricas de execução.

## Estado atual

O sistema trabalha com quatro datasets carregados no ClickHouse:

| Dataset | Tabela |
|---|---|
| `covid-19-vacinacao` | `vacinacao` |
| `leitos` | `leitos` |
| `surtos-srag` | `srag` |
| `atencao-basica` | `atencao_basica` |

Relações interdomínio cadastradas:

| Relação | Datasets |
|---|---|
| `vacinacao_leitos_uf` | vacinação + leitos |
| `srag_ubs_municipio_notificacao` | SRAG + UBS |

## Preparar ambiente

Na raiz do projeto:

```powershell
docker-compose up -d
```

Dentro de `backend`:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python etl/load_csv.py
python main.py
```

O comando `python etl/load_csv.py` limpa e recarrega todos os datasets configurados. Para recarregar apenas um dataset:

```powershell
python etl/load_csv.py --dataset leitos
```

## Testar uma pergunta

Com a API rodando:

```powershell
curl -X POST "http://localhost:8000/api/ask" `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"Quantas doses de vacina contra a COVID-19 foram registradas no conjunto de dados carregado?\"}"
```

A resposta inclui, entre outros campos:

- `dataset` e `datasets`;
- `cross_dataset`;
- `relationships`;
- `sql`;
- `data`;
- `insight`;
- `timing_s`;
- `evaluation_metrics`.

## Executar as perguntas experimentais

Na raiz do projeto:

```powershell
python backend/tests/benchmark_68_questoes_seidig.py
```

Intervalo específico:

```powershell
python backend/tests/benchmark_68_questoes_seidig.py --start 61 --end 68
```

Dataset específico:

```powershell
python backend/tests/benchmark_68_questoes_seidig.py --dataset leitos
```

O resultado agregado é salvo em:

```text
test_results_68_questoes.json
```

## Testes automatizados

Os testes unitários e de consistência ficam em `backend/tests`.

```powershell
python -m pytest backend/tests
```

## Documentação

A documentação atual fica em `docs`:

- `docs/SISTEMA_ATUAL.md`
- `docs/EXPERIMENTOS_METRICAS.md`
- `docs/PERGUNTAS_SEIDIG_68.md`

## Licença

MIT.
