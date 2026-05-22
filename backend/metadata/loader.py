import json
from pathlib import Path
from typing import List, Dict, Optional

def load_metadata(dataset: str = "covid-19-vacinacao") -> str:
    """
    Carrega metadados (schema) de um dataset específico.
    
    Args:
        dataset (str): Nome do dataset dentro de metadata/datasets/
                      Padrão: "covid-19-vacinacao"
    
    Returns:
        str: JSON formatado com metadados do dataset
    
    Exemplos:
        load_metadata()  # Usa covid-19-vacinacao
        load_metadata("surtos-srag")  # Carrega SRAG
        load_metadata("atencao-basica")  # Carrega UBS
        load_metadata("leitos")  # Carrega leitos
    
    Estrutura esperada:
        metadata/
        └── datasets/
            ├── covid-19-vacinacao/
            │   └── schema.json
            ├── surtos-srag/
            │   └── schema.json
            ├── atencao-basica/
            │   └── schema.json
            └── leitos/
                └── schema.json
    """
    base_path = Path(__file__).parent
    file_path = base_path / "datasets" / dataset / "schema.json"

    if not file_path.exists():
        raise FileNotFoundError(
            f"Metadata não encontrado: {file_path}\n"
            f"   Certifique-se de que o dataset '{dataset}' existe em metadata/datasets/"
        )

    with open(file_path, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    return json.dumps(metadata, ensure_ascii=False, indent=2)


def load_all_metadata() -> Dict[str, str]:
    """
    Carrega metadados de TODOS os datasets disponíveis.
    Útil para contexto LLM que precisa conhecer todas as bases.
    
    Returns:
        Dict[str, str]: Dicionário {dataset_name: json_schema}
    
    Exemplo:
        all_metadata = load_all_metadata()
        # all_metadata["covid-19-vacinacao"] = JSON schema
        # all_metadata["surtos-srag"] = JSON schema
        # all_metadata["atencao-basica"] = JSON schema
        # all_metadata["leitos"] = JSON schema
    """
    base_path = Path(__file__).parent
    datasets_path = base_path / "datasets"
    
    all_metadata = {}
    
    # Iterar sobre cada diretório de dataset
    for dataset_dir in datasets_path.iterdir():
        if dataset_dir.is_dir():
            schema_file = dataset_dir / "schema.json"
            if schema_file.exists():
                dataset_name = dataset_dir.name
                try:
                    with open(schema_file, "r", encoding="utf-8") as f:
                        metadata = json.load(f)
                    all_metadata[dataset_name] = json.dumps(metadata, ensure_ascii=False, indent=2)
                except Exception as e:
                    print(f"Aviso: Erro ao carregar {dataset_name}: {e}")
    
    return all_metadata


def get_available_datasets() -> List[str]:
    """
    Lista todos os datasets disponíveis.
    
    Returns:
        List[str]: Lista de nomes de datasets
    
    Exemplo:
        datasets = get_available_datasets()
        # ["covid-19-vacinacao", "leitos", "surtos-srag", "atencao-basica"]
    """
    base_path = Path(__file__).parent
    datasets_path = base_path / "datasets"
    
    datasets = []
    for dataset_dir in sorted(datasets_path.iterdir()):
        if dataset_dir.is_dir():
            schema_file = dataset_dir / "schema.json"
            if schema_file.exists():
                datasets.append(dataset_dir.name)
    
    return datasets


def get_metadata_by_dataset(dataset: str) -> Dict[str, any]:
    """
    Carrega metadados como dicionário (não JSON string).
    Útil para análise programática.
    
    Args:
        dataset: Nome do dataset
    
    Returns:
        Dict: Metadados parseados
    """
    metadata_str = load_metadata(dataset)
    return json.loads(metadata_str)