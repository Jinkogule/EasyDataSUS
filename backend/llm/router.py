from llm.ollama_provider import OllamaProvider

# Mapeamento de nomes amigáveis para modelos Ollama
MODELS = {
    "deepseek-local": {
        "model": "deepseek-coder:6.7b-base-q4_K_M",
        "description": "DeepSeek Coder 6.7B - Otimizado para SQL e código",
        "size": "4.1GB",
        "params": "6.7B"
    },
    "neural-local": {
        "model": "neural-chat",
        "description": "Neural Chat 7B - Melhor para português natural",
        "size": "4.7GB",
        "params": "7B"
    },
    "mistral-local": {
        "model": "mistral",
        "description": "Mistral 7B - Rápido, preciso e equilibrado",
        "size": "4GB",
        "params": "7B"
    },
    "orca-local": {
        "model": "orca-mini",
        "description": "Orca Mini 3B - Muito leve e rápido",
        "size": "2GB",
        "params": "3B"
    },
}

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
    
    # Usar deepseek como padrão
    if model_name not in MODELS:
        print(f"Modelo '{model_name}' desconhecido. Usando 'deepseek-local'")
        model_name = "deepseek-local"
    
    ollama_model = MODELS[model_name]["model"]
    return OllamaProvider(ollama_model, model_name)
    