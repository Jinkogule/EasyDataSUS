# EasyDataSUS

EasyDataSUS é um artefato computacional de pesquisa para consulta em linguagem natural a bases públicas selecionadas do DataSUS. O sistema combina metadados semânticos, geração híbrida de SQL, validação estrutural e execução em ClickHouse para produzir respostas analíticas factuais, somente de leitura, sobre um ou mais domínios de saúde pública.

O projeto está atualmente voltado a um cenário experimental controlado. Documentação local e saídas dos experimentos ficam fora do repositório remoto; este README reúne as instruções públicas essenciais de instalação e uso.

## Escopo

Datasets suportados:

| Dataset | Tabela no ClickHouse | Domínio |
|---|---|---|
| `covid-19-vacinacao` | `vacinacao` | vacinação contra COVID-19 |
| `leitos` | `leitos` | capacidade hospitalar |
| `surtos-srag` | `srag` | vigilância de SRAG |
| `atencao-basica` | `atencao_basica` | unidades de atenção básica |

Relacionamentos interdomínio suportados:

| Relacionamento | Datasets | Nível de junção |
|---|---|---|
| `vacinacao_leitos_uf` | vacinação + leitos | código da UF |
| `srag_ubs_municipio_notificacao` | SRAG + atenção básica | código IBGE do município |

## Estrutura do projeto e fluxo de consulta

Principais módulos do backend:

| Caminho | Finalidade |
|---|---|
| `backend/main.py` | Inicia a aplicação FastAPI |
| `backend/routes/query.py` | Orquestra o processamento de perguntas pelo endpoint `/api/ask` |
| `backend/config/datasets.py` | Registra datasets suportados, tabelas, caminhos dos CSVs e observações de escopo |
| `backend/metadata/datasets/*/schema.json` | Descreve atributos dos datasets usados nos prompts SQL e na validação das consultas |
| `backend/metadata/relationships.json` | Define relações interdomínio suportadas, chaves de junção, granularidade e regras de pré-agregação |
| `backend/services/sql_service.py` | Gera e valida SQL para consultas em uma única base |
| `backend/services/multibase_service.py` | Faz seleção de datasets, recuperação de relacionamentos, geração SQL multibase e validação estrutural |
| `backend/services/result_formatter.py` | Gera resumos factuais, destaques e alertas a partir dos resultados |
| `backend/services/interpretation_service.py` | Produz ou valida respostas em linguagem natural a partir dos resultados factuais |
| `backend/llm/` | Contém o provedor Ollama e a resolução de aliases de modelos |
| `backend/etl/load_csv.py` | Recarrega os CSVs nas tabelas já existentes do ClickHouse |
| `backend/tests/benchmark_68_questoes_seidig.py` | Executa o conjunto experimental de perguntas e registra metadados de avaliação |

O sistema usa uma estratégia híbrida de consulta:

1. A API recebe uma pergunta em linguagem natural.
2. Se a requisição não informar um dataset, o sistema seleciona uma ou mais bases por heurísticas e, quando necessário, pela LLM configurada.
3. Para consultas sobre uma única base, o serviço SQL monta um prompt com metadados do dataset, exemplos e regras específicas da base. A LLM recebe esse prompt e deve retornar apenas SQL.
4. Para consultas interdomínio, o serviço multibase recupera os relacionamentos previamente definidos e gera uma consulta determinística para padrões suportados ou solicita à LLM uma consulta usando apenas tabelas, colunas, chaves de junção e regras de pré-agregação permitidas.
5. A SQL gerada é sanitizada, os identificadores são padronizados e a consulta passa por validação estrutural antes da execução. A validação verifica acesso somente de leitura, tabelas permitidas, colunas permitidas, junções e restrições dos relacionamentos.
6. Se a geração por LLM falhar ou produzir SQL inválida, regras determinísticas de fallback tentam gerar uma consulta segura para padrões analíticos conhecidos.
7. O ClickHouse executa a consulta validada, e o formatador retorna resultados factuais, alertas, destaques e metadados de avaliação.

As regras determinísticas são implementadas no código para padrões analíticos recorrentes e bem definidos, como contagens por UF, disponibilidade de leitos de UTI na competência mais recente, municípios com UTI neonatal e agregações interdomínio suportadas. A geração não determinística é feita pela LLM selecionada a partir de prompts montados em tempo de execução com os metadados e a pergunta do usuário. A LLM não lê diretamente os scripts do projeto.

## Requisitos

- Python 3.10+
- Docker e Docker Compose
- Modelo Ollama disponível no container `easydatasus-ollama`
- Arquivos CSV do DataSUS referentes aos datasets que serão carregados

O alias padrão do benchmark é `deepseek-local`. Outros modelos instalados no Ollama podem ser usados com `--model`.

## Subir a infraestrutura

Na raiz do projeto:

```powershell
docker compose up -d
```

Esse comando sobe:

- ClickHouse, usando `init_all_tables.sql` para criar as tabelas analíticas na primeira inicialização;
- Ollama, usado pelo provedor local de modelos de linguagem.

Se o volume do ClickHouse já existir, o Docker não executará novamente o script de criação das tabelas automaticamente. Nesse caso, recrie o volume ou aplique alterações de schema manualmente antes da carga dos dados.

Instale ao menos um modelo Ollama dentro do container antes de executar perguntas ou benchmarks:

```powershell
docker exec easydatasus-ollama ollama pull qwen2.5-coder:7b
```

Para verificar os modelos instalados:

```powershell
docker exec easydatasus-ollama ollama list
```

## Preparar o backend

Na raiz do projeto:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Carregar os CSVs do DataSUS

Os arquivos CSV do DataSUS são dados externos de entrada e devem ser colocados nas pastas configuradas correspondentes em `backend/data/datasets` antes da execução do carregador.

Depois, dentro de `backend`:

```powershell
python etl/load_csv.py
```

Esse comando limpa e recarrega todos os datasets configurados.

Para recarregar apenas um dataset:

```powershell
python etl/load_csv.py --dataset leitos
```

O carregador não cria as tabelas do ClickHouse a partir dos metadados. A criação das tabelas é definida em `init_all_tables.sql`; o carregador lê o schema existente, mapeia as colunas do CSV sem diferenciar maiúsculas/minúsculas, converte valores suportados e insere os registros.

## Rodar a API

Dentro de `backend`:

```powershell
python main.py
```

Exemplo de requisição:

```powershell
curl -X POST "http://localhost:8000/api/ask" `
  -H "Content-Type: application/json" `
  -d "{\"question\":\"Quantas doses de vacina contra a COVID-19 foram registradas no conjunto de dados carregado?\"}"
```

A resposta inclui dataset selecionado, SQL gerado, resultado da consulta, insight factual, tempos de execução e metadados de avaliação voltados aos experimentos.

## Executar o benchmark com 68 perguntas

Na raiz do projeto:

```powershell
python backend/tests/benchmark_68_questoes_seidig.py
```

Executar com um modelo específico:

```powershell
python backend/tests/benchmark_68_questoes_seidig.py --model qwen2.5-coder:7b
```

Executar um subconjunto:

```powershell
python backend/tests/benchmark_68_questoes_seidig.py --start 61 --end 68
python backend/tests/benchmark_68_questoes_seidig.py --dataset leitos
```

As saídas do benchmark são salvas localmente em `experimentos/`, com versionamento automático.

## Testes automatizados

```powershell
python -m pytest backend/tests
```

## Licença

MIT.
