# Passos Para Testar o Projeto EasyDataSUS

Este documento descreve um fluxo pratico para testar o projeto do zero no Windows.

## 1. Pre-requisitos
Antes de iniciar, confirme que voce tem:
- Docker Desktop instalado e aberto
- Python 3.10+ instalado
- Git instalado
- Espaco em disco livre (recomendado: 15 GB ou mais)

Validacao rapida no terminal:

```bash
docker --version
docker-compose --version
python --version
```

## 2. Abrir o Docker Desktop
1. Abra o Docker Desktop.
2. Espere o status ficar como Running.

Sem isso, os containers de ClickHouse e Ollama nao sobem.

## 3. Subir os containers
Na raiz do projeto, execute:

```bash
docker-compose up -d
```

Verifique se os dois principais servicos estao no ar:

```bash
docker-compose ps
```

Voce deve ver pelo menos:
- easydatasus-clickhouse
- easydatasus-ollama

## 4. Preparar ambiente Python do backend
Entre na pasta do backend e crie o ambiente virtual:

```bash
cd backend
python -m venv venv
```

Ative o ambiente no PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

Instale dependencias:

```bash
pip install -r requirements.txt
```

## 5. Configurar variaveis de ambiente
Crie o arquivo backend/.env com este conteudo base:

```env
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=admin
CLICKHOUSE_PASSWORD=admin
CLICKHOUSE_DATABASE=default

OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=deepseek-coder:6.7b-base-q4_K_M
OLLAMA_TIMEOUT=180

FASTAPI_HOST=localhost
FASTAPI_PORT=8000
```

## 6. Baixar e aquecer modelo no Ollama
Baixe o modelo principal:

```bash
docker exec easydatasus-ollama ollama pull deepseek-coder:6.7b-base-q4_K_M
```

Warmup (importante para reduzir falhas na primeira chamada):

```bash
docker exec easydatasus-ollama ollama run deepseek-coder:6.7b-base-q4_K_M "Hello"
```

## 7. Carregar dados no ClickHouse
Ainda dentro de backend, execute:

```bash
python etl/load_csv.py
```

Se quiser carregar um dataset especifico:

```bash
python etl/load_csv.py --dataset leitos
```

## 8. Subir a API
Inicie a aplicacao:

```bash
python main.py
```

API esperada em:
- http://localhost:8000
- http://localhost:8000/docs
- http://localhost:8000/health

## 9. Teste rapido de saude
Em outro terminal, valide:

```bash
curl http://localhost:8000/health
```

Resposta esperada aproximada:

```json
{"status":"ok","service":"EasyDataSUS"}
```

## 10. Teste funcional principal (pergunta em linguagem natural)
Teste o endpoint principal:

```bash
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Quantas vacinas foram aplicadas em SP?", "dataset": "covid-19-vacinacao"}'
```

Verifique no retorno:
- Campo sql preenchido
- Campo success igual a true
- Campo insight com interpretacao

## 11. Testar perguntas pre-prontas
Listar perguntas disponiveis:

```bash
curl "http://localhost:8000/api/questions"
```

Filtrar por dataset:

```bash
curl "http://localhost:8000/api/questions?dataset=leitos"
```

## 12. Rodar scripts de validacao do repositorio
Na raiz do projeto:

```bash
python test_leitos_query.py
python test_52_questions.py --dataset covid-19-vacinacao
python test_52_questions.py --dataset leitos
```

Observacao: esses scripts sao uteis para verificacao pratica, mas nao substituem uma suite formal de testes automatizados.

## 13. Checklist de conclusao
Considere o teste bem-sucedido quando:
- Docker Desktop esta Running
- Containers clickhouse e ollama estao Up
- Modelo Ollama foi baixado e respondeu ao warmup
- ETL carregou dados sem erro
- API subiu e respondeu /health
- /api/ask retornou SQL + insight com success true
- Scripts de teste executaram sem erro critico

## 14. Problemas comuns e correcoes rapidas
1. Porta ocupada (8123, 11434, 8000)
- Pare servicos conflitantes ou ajuste portas.

2. Ollama lento ou timeout
- Repita warmup e aumente OLLAMA_TIMEOUT no .env.

3. Falha no ETL por encoding
- Confira se o CSV esta no formato esperado e com delimitador ;

4. API sobe, mas consulta falha
- Verifique se ClickHouse recebeu os dados e se dataset informado existe.

5. Modelo nao encontrado
- Rode novamente o comando ollama pull dentro do container.

## 15. Encerramento
Para parar os containers:

```bash
docker-compose down
```

Para parar e remover volumes locais (cuidado: apaga dados locais do banco/modelos):

```bash
docker-compose down -v
```
