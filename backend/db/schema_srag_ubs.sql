-- ============================================================================
-- Schema DDL para ClickHouse - SRAG e Atenção Básica
-- ============================================================================

-- Tabela: SRAG (Síndrome Respiratória Aguda Grave)
-- Documentação: backend/metadata/datasets/surtos-srag/schema.json
-- Registros esperados: ~50,000+ (amostra inicial)
-- Período: 2019-2026

CREATE TABLE IF NOT EXISTS srag (
    nu_notific Int64,              -- Número único de notificação
    dt_notific Date,               -- Data da notificação
    sem_not Int32,                 -- Semana epidemiológica
    dt_sin_pri Date,               -- Data do primeiro sintoma
    sg_uf_not String,              -- UF de notificação
    co_mun_not Int32,              -- Código IBGE município de notificação
    cs_sexo String,                -- Sexo (M/F)
    dt_nasc Date,                  -- Data de nascimento
    nu_idade_n Int32,              -- Idade em anos
    
    -- Sintomas
    febre Int32,                   -- 1=sim, 2=não, 9=não informado
    tosse Int32,
    garganta Int32,
    dispneia Int32,
    diarreia Int32,
    vomito Int32,
    
    -- Fatores de risco
    cardiopati Int32,              -- Doença cardiovascular
    diabetes Int32,
    asma Int32,
    pneumopati Int32,              -- Doença pulmonar crônica
    imunodepre Int32,              -- Imunodeficiência
    renal Int32,
    obesidade Int32,
    
    -- Hospitalização
    hospital Int32,                -- 1=sim, 2=não
    dt_interna Date,               -- Data de internação
    co_mu_inte Int32,              -- Município de internação
    uti Int32,                     -- Necessidade de UTI
    
    -- Testes laboratoriais
    amostra Int32,                 -- Coleta de amostra
    dt_coleta Date,
    pcr_resul Int32,               -- Resultado PCR
    pos_pcrflu Int32,              -- PCR positivo influenza
    tp_flu_pcr Int32,              -- Tipo de influenza
    pcr_vsr Int32,                 -- PCR para VSR
    pcr_sars2 Int32,               -- PCR para SARS-CoV-2
    
    -- Classificação e evolução
    classi_fin Int32,              -- 1=confirmado, 2=descartado, 3=provável
    evolucao Int32,                -- 1=cura, 2=óbito, 3=óbito outras causas
    dt_evoluca Date,               -- Data da evolução
    
    -- Vacinação COVID-19
    vacina_cov Int32,
    dose_1_cov Date,
    dose_2_cov Date
) ENGINE = MergeTree()
ORDER BY (dt_notific, sg_uf_not, co_mun_not)
PARTITION BY toYYYYMM(dt_notific);

-- Índices para queries comuns
CREATE INDEX idx_srag_uf ON srag (sg_uf_not) TYPE set(0) GRANULARITY 4;
CREATE INDEX idx_srag_municipio ON srag (co_mun_not) TYPE set(0) GRANULARITY 4;
CREATE INDEX idx_srag_hospital ON srag (hospital) TYPE set(0) GRANULARITY 4;
CREATE INDEX idx_srag_evolucao ON srag (evolucao) TYPE set(0) GRANULARITY 4;
CREATE INDEX idx_srag_classi ON srag (classi_fin) TYPE set(0) GRANULARITY 4;
CREATE INDEX idx_srag_pcr ON srag (pcr_sars2) TYPE set(0) GRANULARITY 4;

-- ============================================================================

-- Tabela: Atenção Básica (UBS)
-- Documentação: backend/metadata/datasets/atencao-basica/schema.json
-- Registros: 47,721 UBS ativas
-- Cobertura: 27 estados, 5,483 municípios

CREATE TABLE IF NOT EXISTS atencao_basica (
    cnes Int32,                    -- Código CNES (identificador único)
    uf Int32,                      -- Código numérico da UF
    ibge Int32,                    -- Código IBGE do município
    nome String,                   -- Nome da UBS
    logradouro String,             -- Endereço completo
    bairro String,                 -- Bairro
    latitude Float64,              -- Coordenada geográfica (WGS84)
    longitude Float64              -- Coordenada geográfica (WGS84)
) ENGINE = MergeTree()
ORDER BY (ibge, cnes)
PARTITION BY uf;

-- Índices para queries comuns
CREATE INDEX idx_ubs_uf ON atencao_basica (uf) TYPE set(0) GRANULARITY 4;
CREATE INDEX idx_ubs_municipio ON atencao_basica (ibge) TYPE set(0) GRANULARITY 4;
CREATE INDEX idx_ubs_bairro ON atencao_basica (bairro) TYPE set(1) GRANULARITY 4;

-- ============================================================================

-- Views auxiliares para análise

-- View: Casos SRAG por UF
CREATE OR REPLACE VIEW srag_by_uf AS
SELECT 
    sg_uf_not as uf,
    COUNT(*) as total_casos,
    SUM(IF(hospital = 1, 1, 0)) as casos_hospitalizados,
    SUM(IF(evolucao = 2, 1, 0)) as obitos,
    ROUND(SUM(IF(evolucao = 2, 1, 0)) / COUNT(*) * 100, 2) as taxa_mortalidade,
    MIN(dt_notific) as primeira_notificacao,
    MAX(dt_notific) as ultima_notificacao
FROM srag
GROUP BY sg_uf_not;

-- View: Distribuição de UBS por UF
CREATE OR REPLACE VIEW ubs_by_uf AS
SELECT 
    uf,
    COUNT(*) as total_ubs,
    COUNT(DISTINCT ibge) as municipios_cobertos
FROM atencao_basica
GROUP BY uf;

-- View: SRAG com sintomas de gravidade (febre + tosse + dispneia)
CREATE OR REPLACE VIEW srag_grave AS
SELECT 
    nu_notific,
    dt_notific,
    sg_uf_not,
    co_mun_not,
    nu_idade_n,
    cs_sexo,
    hospital,
    uti,
    evolucao
FROM srag
WHERE febre = 1 AND tosse = 1 AND dispneia = 1;

-- ============================================================================
-- Verificação pós-criação
-- ============================================================================

-- Execute após criar as tabelas para verificar:
-- SELECT * FROM system.tables WHERE database = 'default' AND name IN ('srag', 'atencao_basica');
-- SELECT COUNT(*) FROM srag;
-- SELECT COUNT(*) FROM atencao_basica;
