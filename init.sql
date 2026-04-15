-- Criar tabela vacinacao com schema correto
CREATE TABLE IF NOT EXISTS vacinacao (
    document_id String,
    paciente_id String,
    paciente_idade Int32,
    paciente_dataNascimento Nullable(Date),
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
ORDER BY (paciente_endereco_uf, paciente_id);

-- Índices para queries comuns
ALTER TABLE vacinacao ADD INDEX idx_uf paciente_endereco_uf TYPE set(0);
ALTER TABLE vacinacao ADD INDEX idx_municipio paciente_endereco_nmMunicipio TYPE set(0);
ALTER TABLE vacinacao ADD INDEX idx_data vacina_dataAplicacao TYPE set(0);
ALTER TABLE vacinacao ADD INDEX idx_vacina vacina_nome TYPE set(0);

-- Criar tabela leitos com schema para dados de capacidade hospitalar
CREATE TABLE IF NOT EXISTS leitos (
    COMP String,
    REGIAO String,
    UF String,
    CO_IBGE String,
    MUNICIPIO String,
    MOTIVO_DESABILITACAO Nullable(String),
    CNES String,
    NOME_ESTABELECIMENTO String,
    RAZAO_SOCIAL Nullable(String),
    TP_GESTAO Nullable(String),
    CO_TIPO_UNIDADE Nullable(String),
    DS_TIPO_UNIDADE Nullable(String),
    NATUREZA_JURIDICA Nullable(String),
    DESC_NATUREZA_JURIDICA Nullable(String),
    NO_LOGRADOURO Nullable(String),
    NU_ENDERECO Nullable(String),
    NO_COMPLEMENTO Nullable(String),
    NO_BAIRRO Nullable(String),
    CO_CEP Nullable(String),
    NU_TELEFONE Nullable(String),
    NO_EMAIL Nullable(String),
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
    UTI_QUEIMADO_EXIST Int32,
    UTI_QUEIMADO_SUS Int32,
    UTI_CORONARIANA_EXIST Int32,
    UTI_CORONARIANA_SUS Int32
) ENGINE = MergeTree()
ORDER BY (UF, MUNICIPIO, CNES);

-- Índices para queries comuns de leitos
ALTER TABLE leitos ADD INDEX idx_uf UF TYPE set(0);
ALTER TABLE leitos ADD INDEX idx_municipio MUNICIPIO TYPE set(0);
ALTER TABLE leitos ADD INDEX idx_regiao REGIAO TYPE set(0);
ALTER TABLE leitos ADD INDEX idx_cnes CNES TYPE set(0);
