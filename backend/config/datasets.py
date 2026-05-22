"""
Configuração centralizada de todos os datasets do sistema.

QUALQUER novo tema deve ser registrado aqui.
Este arquivo mapeia dataset → table_name e fornece utilidades centralizadas.
Inclui: Vacinação COVID-19, Leitos, SRAG, Atenção Básica
"""

DATASETS_CONFIG = {
    "covid-19-vacinacao": {
        "table_name": "vacinacao",
        "description": "Vacinação COVID-19 no Brasil",
        "name": "Campanha Nacional de Vacinação COVID-19",
        "schema_path": "backend/metadata/datasets/covid-19-vacinacao/schema.json",
        "csv_path": "backend/data/datasets/covid-19-vacinacao/vacinacao-covid.csv",
        "objetivo_estrategico": "OE 3.6.1",
        "dominio": "Imunização",
        "status": "implementado",
    },
    "leitos": {
        "table_name": "leitos",
        "description": "Dados de leitos em hospitais e estabelecimentos de saúde no Brasil",
        "name": "Leitos Hospitalares",
        "schema_path": "backend/metadata/datasets/leitos/schema.json",
        "csv_path": "backend/data/datasets/leitos/Leitos_2026.csv",
        "objetivo_estrategico": "OE 9.1",
        "dominio": "Gestão Assistencial",
        "status": "implementado",
    },
    "surtos-srag": {
        "table_name": "srag",
        "description": "Vigilância da Síndrome Respiratória Aguda Grave",
        "name": "Síndrome Respiratória Aguda Grave (SRAG)",
        "schema_path": "backend/metadata/datasets/surtos-srag/schema.json",
        "csv_path": "backend/data/datasets/surtos-srag/INFLUD26-18-05-2026.csv",
        "objetivo_estrategico": "OE 9.1",
        "dominio": "Vigilância Epidemiológica",
        "status": "implementado",
    },
    "atencao-basica": {
        "table_name": "atencao_basica",
        "description": "Unidades Básicas de Saúde no Brasil",
        "name": "Unidades Básicas de Saúde (Atenção Básica)",
        "schema_path": "backend/metadata/datasets/atencao-basica/schema.json",
        "csv_path": "backend/data/datasets/atencao-basica/Unidades_Basicas_Saude-UBS.csv",
        "objetivo_estrategico": "OE 3.6.1, OE 7.2/7.3",
        "dominio": "Atenção Primária",
        "status": "implementado",
    },
}


def get_table_name(dataset: str) -> str:
    """
    Retorna nome da tabela para um dataset.
    
    Args:
        dataset: ID do dataset (ex: "covid-19-vacinacao")
    
    Returns:
        Nome da tabela no ClickHouse (ex: "covid_19_vacinacao")
    
    Raises:
        ValueError: Se dataset não está configurado
    
    Exemplo:
        >>> get_table_name("covid-19-vacinacao")
        "covid_19_vacinacao"
        >>> get_table_name("dengue-2024")
        "dengue"
    """
    if dataset not in DATASETS_CONFIG:
        available = ", ".join(DATASETS_CONFIG.keys())
        raise ValueError(
            f"Dataset '{dataset}' não configurado. "
            f"Datasets disponíveis: {available}"
        )
    return DATASETS_CONFIG[dataset]["table_name"]


def get_dataset_config(dataset: str) -> dict:
    """
    Retorna configuração completa de um dataset.
    
    Args:
        dataset: ID do dataset
    
    Returns:
        Dicionário com "table_name" e "description"
    """
    return DATASETS_CONFIG.get(dataset, {})


def list_available_datasets() -> list:
    """
    Lista todos os datasets disponíveis.
    
    Returns:
        Lista com IDs dos datasets
    
    Exemplo:
        >>> list_available_datasets()
        ["covid-19-vacinacao", "dengue-2024", "influenza-2025"]
    """
    return list(DATASETS_CONFIG.keys())


def dataset_exists(dataset: str) -> bool:
    """
    Verifica se um dataset está registrado.
    
    Args:
        dataset: ID do dataset
    
    Returns:
        True se existe, False caso contrário
    """
    return dataset in DATASETS_CONFIG
