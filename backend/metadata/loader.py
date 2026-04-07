import json
from pathlib import Path

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
        load_metadata("dengue-2024")  # Carrega dengue-2024
        load_metadata("influenza-2025")  # Carrega influenza-2025
    
    Estrutura esperada:
        metadata/
        └── datasets/
            ├── covid-19-vacinacao/
            │   └── schema.json
            ├── dengue-2024/
            │   └── schema.json
            └── influenza-2025/
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