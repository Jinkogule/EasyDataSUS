"""
Configuração centralizada de todos os datasets do sistema.

QUALQUER novo tema deve ser registrado aqui.
Este arquivo mapeia dataset → table_name e fornece utilidades centralizadas.
"""

DATASETS_CONFIG = {
    "covid-19-vacinacao": {
        "table_name": "vacinacao",
        "description": "Vacinação COVID-19 no Brasil",
    },
    "leitos": {
        "table_name": "leitos",
        "description": "Dados de leitos em hospitais e estabelecimentos de saúde no Brasil",
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
