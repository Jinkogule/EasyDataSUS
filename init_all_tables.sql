-- Script para criar/recriar TODAS as tabelas do EasyDataSUS
-- Execução manual: docker exec -i easydatasus-clickhouse clickhouse-client < init_all_tables.sql

-- ============================================================================
-- 1. TABELA: COVID-19 VACINAÇÃO
-- ============================================================================

DROP TABLE IF EXISTS vacinacao;

CREATE TABLE vacinacao (
    document_id String,
    paciente_id String,
    paciente_idade Int32,
    paciente_dataNascimento Nullable(Date32),
    paciente_enumSexoBiologico Nullable(String),
    paciente_racaCor_codigo Nullable(String),
    paciente_racaCor_valor Nullable(String),
    paciente_endereco_coIbgeMunicipio Nullable(String),
    paciente_endereco_coPais Nullable(String),
    paciente_endereco_nmMunicipio Nullable(String),
    paciente_endereco_nmPais Nullable(String),
    paciente_endereco_uf String,
    paciente_endereco_cep Nullable(String),
    paciente_nacionalidade_enumNacionalidade Nullable(String),
    estabelecimento_valor Nullable(String),
    estabelecimento_razaoSocial Nullable(String),
    estalecimento_noFantasia Nullable(String),
    estabelecimento_municipio_codigo Nullable(String),
    estabelecimento_municipio_nome Nullable(String),
    estabelecimento_uf Nullable(String),
    vacina_grupoAtendimento_codigo Nullable(String),
    vacina_grupoAtendimento_nome Nullable(String),
    vacina_categoria_codigo Nullable(String),
    vacina_categoria_nome Nullable(String),
    vacina_lote Nullable(String),
    vacina_fabricante_nome Nullable(String),
    vacina_fabricante_referencia Nullable(String),
    vacina_dataAplicacao Nullable(Date),
    vacina_descricao_dose Nullable(String),
    vacina_codigo Nullable(String),
    vacina_nome Nullable(String),
    sistema_origem Nullable(String)
) ENGINE = MergeTree()
ORDER BY (paciente_endereco_uf, paciente_id)
PARTITION BY toYYYYMM(vacina_dataAplicacao);

ALTER TABLE vacinacao ADD INDEX idx_uf paciente_endereco_uf TYPE set(0);
ALTER TABLE vacinacao ADD INDEX idx_municipio paciente_endereco_nmMunicipio TYPE set(0);
ALTER TABLE vacinacao ADD INDEX idx_data vacina_dataAplicacao TYPE set(0);
ALTER TABLE vacinacao ADD INDEX idx_vacina vacina_nome TYPE set(0);

-- ============================================================================
-- 2. TABELA: LEITOS
-- ============================================================================

DROP TABLE IF EXISTS leitos;

CREATE TABLE leitos (
    COMP String,
    REGIAO String,
    UF String,
    CO_IBGE String,
    MUNICIPIO String,
    MOTIVO_DESABILITACAO String,
    CNES String,
    NOME_ESTABELECIMENTO String,
    RAZAO_SOCIAL String,
    TP_GESTAO String,
    CO_TIPO_UNIDADE String,
    DS_TIPO_UNIDADE String,
    NATUREZA_JURIDICA String,
    DESC_NATUREZA_JURIDICA String,
    NO_LOGRADOURO String,
    NU_ENDERECO String,
    NO_COMPLEMENTO String,
    NO_BAIRRO String,
    CO_CEP String,
    NU_TELEFONE String,
    NO_EMAIL String,
    LEITOS_EXISTENTES Int32,
    LEITOS_SUS Int32,
    UTI_TOTAL_EXIST Int32,
    UTI_TOTAL_SUS Int32,
    UTI_ADULTO_EXIST Int32,
    UTI_ADULTO_SUS Int32,
    UTI_PEDIATRICO_EXIST Int32,
    UTI_PEDIATRICO_SUS Int32,
    UTI_NEONATAL_EXIST Int32,
    UTI_NEONATAL_SUS Int32,
    UTI_CORONARIANA_EXIST Int32,
    UTI_CORONARIANA_SUS Int32,
    UTI_QUEIMADO_EXIST Int32,
    UTI_QUEIMADO_SUS Int32
) ENGINE = MergeTree()
ORDER BY (UF, MUNICIPIO, CNES);

ALTER TABLE leitos ADD INDEX idx_uf UF TYPE set(0);
ALTER TABLE leitos ADD INDEX idx_municipio MUNICIPIO TYPE set(0);
ALTER TABLE leitos ADD INDEX idx_tipo DS_TIPO_UNIDADE TYPE set(0);
ALTER TABLE leitos ADD INDEX idx_gestao TP_GESTAO TYPE set(0);

-- ============================================================================
-- 3. TABELA: SRAG (Síndrome Respiratória Aguda Grave)
-- ============================================================================

DROP TABLE IF EXISTS srag;

CREATE TABLE srag (
    nu_notific Int64,
    dt_notific Date,
    sem_not Int32,
    sem_pri Nullable(Int32),
    dt_sin_pri Nullable(Date),
    sg_uf_not String,
    sg_uf Nullable(String),
    co_mun_not Int32,
    co_mun_res Nullable(Int32),
    nu_idade_n Nullable(Int32),
    tp_idade Nullable(Int32),
    cs_sexo Nullable(String),
    dt_nasc Nullable(Date32),
    id_municip Int32,
    co_regiao Int32,
    classi_fin Int32,
    evolucao Int32,
    dt_evoluca Nullable(Date),
    dt_interna Nullable(Date),
    co_mu_inte Nullable(Int32),
    dt_encerra Nullable(Date),
    dt_digita Nullable(Date),
    dt_notif Nullable(Date),
    febre Int32,
    tosse Int32,
    garganta Int32,
    dispneia Int32,
    desc_resp Int32,
    saturacao Int32,
    diarreia Int32,
    vomito Int32,
    outro_sin Int32,
    cardiopati Int32,
    hematologi Int32,
    hepatica Int32,
    asma Int32,
    diabetes Int32,
    neurologic Int32,
    pneumopati Int32,
    imunodepre Int32,
    renal Int32,
    obesidade Int32,
    hospital Int32,
    uti Int32,
    amostra Nullable(Int32),
    dt_coleta Nullable(Date),
    suport_ven Int32,
    ventilatad Int32,
    antiviral Int32,
    antibiotico Int32,
    antitromb Int32,
    corticoide Int32,
    outro_medic Int32,
    pcr_sars2 Int32,
    pos_pcrflu Int32,
    tp_flu_pcr Nullable(Int32),
    pcr_vsr Int32,
    pcr_para Int32,
    pcr_outro Int32,
    pcr_resul Int32,
    vacina_cov Nullable(Int32),
    dose_1_cov Nullable(Date),
    dose_2_cov Nullable(Date)
) ENGINE = MergeTree()
ORDER BY (dt_notific, sg_uf_not, co_mun_not)
PARTITION BY toYYYYMM(dt_notific);

ALTER TABLE srag ADD INDEX idx_srag_uf sg_uf_not TYPE set(0);
ALTER TABLE srag ADD INDEX idx_srag_municipio co_mun_not TYPE set(0);
ALTER TABLE srag ADD INDEX idx_srag_hospital hospital TYPE set(0);
ALTER TABLE srag ADD INDEX idx_srag_evolucao evolucao TYPE set(0);
ALTER TABLE srag ADD INDEX idx_srag_classi classi_fin TYPE set(0);
ALTER TABLE srag ADD INDEX idx_srag_pcr pcr_sars2 TYPE set(0);

-- ============================================================================
-- 4. TABELA: ATENÇÃO BÁSICA (UBS)
-- ============================================================================

DROP TABLE IF EXISTS atencao_basica;

CREATE TABLE atencao_basica (
    cnes Int32,
    uf String,
    ibge Int32,
    nome String,
    logradouro String,
    bairro String,
    latitude Float64,
    longitude Float64
) ENGINE = MergeTree()
ORDER BY (ibge, cnes)
PARTITION BY uf;

ALTER TABLE atencao_basica ADD INDEX idx_ubs_uf uf TYPE set(0);
ALTER TABLE atencao_basica ADD INDEX idx_ubs_ibge ibge TYPE set(0);
ALTER TABLE atencao_basica ADD INDEX idx_ubs_cnes cnes TYPE set(0);

-- ============================================================================
-- VIEWS ANALÍTICAS
-- ============================================================================

-- Vista: SRAG por Estado
CREATE OR REPLACE VIEW srag_by_uf AS
SELECT 
    sg_uf_not as estado,
    COUNT(*) as total_casos,
    SUM(CASE WHEN hospital = 1 THEN 1 ELSE 0 END) as hospitalizados,
    SUM(CASE WHEN evolucao = 2 THEN 1 ELSE 0 END) as mortes,
    SUM(CASE WHEN uti = 1 THEN 1 ELSE 0 END) as uti_internados
FROM srag
GROUP BY sg_uf_not
ORDER BY total_casos DESC;

-- Vista: UBS por Estado
CREATE OR REPLACE VIEW ubs_by_uf AS
SELECT 
    uf,
    COUNT(DISTINCT cnes) as total_ubs,
    COUNT(DISTINCT ibge) as municipios_cobertos
FROM atencao_basica
GROUP BY uf
ORDER BY total_ubs DESC;

-- Vista: SRAG Grave (casos com hospitalização e múltiplos sintomas)
CREATE OR REPLACE VIEW srag_grave AS
SELECT 
    nu_notific,
    dt_notific,
    sg_uf_not,
    co_mun_not,
    (febre + tosse + dispneia + saturacao) as score_gravidade,
    evolucao,
    hospital,
    uti
FROM srag
WHERE hospital = 1 
  AND (febre + tosse + dispneia + saturacao) >= 3
ORDER BY dt_notific DESC;

-- ============================================================================
-- VERIFICAÇÃO
-- ============================================================================

-- Tabelas criadas
SHOW TABLES;

-- Info das tabelas
DESCRIBE TABLE vacinacao;
DESCRIBE TABLE leitos;
DESCRIBE TABLE srag;
DESCRIBE TABLE atencao_basica;

-- ============================================================================
-- USUÁRIO SOMENTE LEITURA DA APLICAÇÃO
-- O entrypoint executa este arquivo com o usuário administrativo do compose.
-- ============================================================================

CREATE USER IF NOT EXISTS easydatasus_ro
IDENTIFIED WITH plaintext_password BY 'easydatasus_ro';

GRANT SELECT ON default.* TO easydatasus_ro;
