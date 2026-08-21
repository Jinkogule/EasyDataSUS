import os

from llm.ollama_provider import OllamaProvider

# Mapeamento de nomes amigáveis para modelos Ollama
MODELS = {
    "deepseek-local": {
        "model_env": "OLLAMA_MODEL",
        "default_model": "deepseek-coder:6.7b-base-q4_K_M",
        "description": "DeepSeek Coder local configurado por OLLAMA_MODEL",
    },
    "neural-local": {
        "default_model": "neural-chat",
        "description": "Neural Chat 7B - Melhor para português natural",
        "size": "4.7GB",
        "params": "7B"
    },
    "mistral-local": {
        "default_model": "mistral",
        "description": "Mistral 7B - Rápido, preciso e equilibrado",
        "size": "4GB",
        "params": "7B"
    },
    "orca-local": {
        "default_model": "orca-mini",
        "description": "Orca Mini 3B - Muito leve e rápido",
        "size": "2GB",
        "params": "3B"
    },
}


def get_model_identifier(model_name: str = "deepseek-local") -> str:
    """Resolve o identificador Ollama, incluindo sobrescritas do ambiente."""
    if model_name and ":" in model_name:
        return model_name

    if model_name not in MODELS:
        model_name = "deepseek-local"

    config = MODELS[model_name]
    environment_variable = config.get("model_env")
    if environment_variable:
        configured_model = os.getenv(environment_variable, "").strip()
        if configured_model:
            return configured_model

    return config["default_model"]

def get_available_models():
    """Retorna lista de modelos disponíveis"""
    return {name: info["description"] for name, info in MODELS.items()}

def get_llm(model_name: str = "deepseek-local"):
    """Retorna instância do provider Ollama com modelo específico
    
    Args:
        model_name: Nome do modelo ("deepseek-local", "neural-local", "mistral-local", "orca-local")
    
    Returns:
        OllamaProvider configurado com o modelo escolhido
    """
    
    if model_name and ":" in model_name:
        return OllamaProvider(model_name, model_name)

    # Usar deepseek como padrão
    if model_name not in MODELS:
        print(f"Modelo '{model_name}' desconhecido. Usando 'deepseek-local'")
        model_name = "deepseek-local"
    
    ollama_model = get_model_identifier(model_name)
    return OllamaProvider(ollama_model, model_name)
