# Revisao Estrutural Atual do EasyDataSUS

## Visao Geral
A arquitetura esta bem separada por camadas e ja tem uma base solida para crescer:
- API com FastAPI em backend/main.py
- Rotas em backend/routes/query.py, backend/routes/questions.py, backend/routes/admin.py
- Regras de negocio em backend/services/sql_service.py e backend/services/interpretation_service.py
- Acesso a dados em backend/db/clickhouse.py
- Metadata por dataset em backend/metadata/datasets/covid-19-vacinacao/schema.json e backend/metadata/datasets/leitos/schema.json
- ETL em backend/etl/load_csv.py

Resumo: base boa, mas com divida tecnica em validacao SQL, padronizacao de contratos, testes e operacao.

## Pontos Fortes
- Boa separacao de responsabilidades entre rotas, servicos, LLM e banco.
- Estrutura multi-dataset ja existe em backend/config/datasets.py.
- Retry de query no ClickHouse em backend/db/clickhouse.py.
- Pipeline de fallback quando LLM falha em backend/services/sql_service.py.
- Infra docker simples de subir em docker-compose.yml.

## Achados Criticos (Alta)
1. Cobertura de testes automatizados insuficiente
- Existem scripts manuais como test_52_questions.py, mas falta suite robusta de unit/integration com execucao continua.
- Risco: regressoes passam sem deteccao.

2. Validacao SQL duplicada e divergente
- Regras aparecem em mais de um lugar, especialmente backend/services/sql_service.py e backend/routes/query.py.
- Risco: um caminho aceita SQL que outro rejeita.

3. Fallback SQL grande e muito acoplado a heuristicas
- Nucleo de fallback em backend/services/sql_service.py esta extenso e hardcoded por dataset.
- Risco: manutencao cara e erro facil ao adicionar novos temas.

4. Inconsistencias de contrato entre metadata e consumo
- Metadata e carregada por backend/metadata/loader.py, mas ha pontos que presumem formatos/chaves diferentes.
- Risco: contexto quebrar silenciosamente e degradar qualidade da resposta.

## Achados Importantes (Media)
1. ETL acoplado ao ambiente local
- backend/etl/load_csv.py mistura cliente Python com chamadas docker exec.
- Risco: baixa portabilidade para CI/CD e ambientes remotos.

2. Duplicacao de heuristica de dataset
- Logica parecida em backend/routes/query.py e backend/routes/questions.py.
- Risco: drift de comportamento.

3. Respostas potencialmente grandes sem estrategia clara de paginacao
- Pode pressionar memoria e serializacao em cenarios de grande volume.

4. Observabilidade limitada
- Logging existe, mas sem padrao de correlacao fim a fim para troubleshooting em producao.

## Achados Menores (Baixa)
1. Documentacao e nomenclatura misturadas entre portugues/ingles.
2. Falta guia unico e curto para onboarding de novo dataset.
3. Dependencia de varios pontos hardcoded em vez de constantes centralizadas.

## Prioridades Recomendadas

### Prioridade 1 (curto prazo)
1. Criar suite de testes automatizados para servicos e rotas criticas.
2. Unificar validacao/sanitizacao SQL em um unico componente reutilizavel.
3. Corrigir inconsistencias de contrato de metadata.

### Prioridade 2
1. Extrair deteccao de dataset para um servico unico.
2. Introduzir paginacao/limites consistentes de retorno.
3. Melhorar logs com contexto por requisicao.

### Prioridade 3
1. Reduzir acoplamento do ETL ao docker exec.
2. Publicar checklist oficial para adicionar dataset novo.
3. Consolidar constantes de paths e chaves em modulo unico.

## Conclusao
A estrutura atual e boa e ja esta acima do prototipo desorganizado. O principal gargalo hoje e consistencia interna entre modulos, seguido por testes e operacao. Com uma rodada de padronizacao de contratos e validacao SQL, o projeto ganha estabilidade rapida sem reescrever arquitetura.
