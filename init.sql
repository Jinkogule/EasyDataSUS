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
