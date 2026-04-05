#!/usr/bin/env python
"""
Script para gerenciar models locais do Ollama.
Instala múltiplos modelos para comparação.
"""

import subprocess
import sys
import time

# Modelos disponíveis para instalação
MODELS = {
    "deepseek-coder:6.7b-base-q4_K_M": {
        "name": "deepseek-local",
        "description": "DeepSeek Coder 6.7B - Otimizado para SQL",
        "size": "4.1GB",
        "installed": True  # Este já está instalado
    },
    "neural-chat": {
        "name": "neural-local",
        "description": "Neural Chat 7B - Melhor para português",
        "size": "4.7GB",
        "installed": False
    },
    "mistral": {
        "name": "mistral-local",
        "description": "Mistral 7B - Rápido e preciso",
        "size": "4GB",
        "installed": False
    },
    "orca-mini": {
        "name": "orca-local",
        "description": "Orca Mini 3B - Extremamente leve",
        "size": "2GB",
        "installed": False
    },
}

def list_models():
    """Lista todos os modelos disponíveis"""
    print("\n🤖 MODELOS DISPONÍVEIS PARA OLLAMA:\n")
    print(f"{'Model':<15} {'Nome':<20} {'Tamanho':<10} {'Descrição':<50}")
    print("-" * 95)
    for model, info in MODELS.items():
        status = "✅ Instalado" if info['installed'] else "⏳ Não instalado"
        print(f"{model:<15} {info['name']:<20} {info['size']:<10} {info['description']:<50}")
        print(f"                          {status}")
    print()

def pull_model(model_name):
    """Baixa um modelo do Ollama"""
    print(f"\n📥 Baixando modelo: {model_name}...")
    print(f"   Descrição: {MODELS[model_name]['description']}")
    print(f"   Tamanho: {MODELS[model_name]['size']}")
    print(f"   Isso pode levar vários minutos...\n")
    
    try:
        # Usar docker exec para puxar o modelo
        cmd = ['docker', 'exec', 'easydatasus-ollama', 'ollama', 'pull', model_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ Modelo '{model_name}' baixado com sucesso!")
            return True
        else:
            print(f"❌ Erro ao baixar '{model_name}':")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Erro ao executar comando: {e}")
        return False

def list_installed():
    """Lista modelos instalados no Ollama"""
    print("\n📦 MODELOS INSTALADOS NO OLLAMA:\n")
    try:
        cmd = ['docker', 'exec', 'easydatasus-ollama', 'ollama', 'list']
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)
        return True
    except Exception as e:
        print(f"❌ Erro ao listar modelos: {e}")
        return False

def test_model(model_name):
    """Testa um modelo com um prompt simples"""
    print(f"\n🧪 Testando modelo: {model_name}...")
    test_prompt = "Responda em uma frase: O que é vacinação?"
    
    try:
        cmd = [
            'docker', 'exec', 'easydatasus-ollama', 'ollama', 'run',
            model_name, test_prompt
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0:
            print(f"✅ Teste bem-sucedido!")
            print(f"Resposta: {result.stdout.strip()[:200]}")
            return True
        else:
            print(f"❌ Erro ao testar:")
            print(result.stderr)
            return False
    except Exception as e:
        print(f"❌ Erro: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("""
🌐 Gerenciador de Modelos Ollama do EasyDataSUS

Uso: python manage_models.py <comando> [modelo]

COMANDOS:
  list       - Lista todos os modelos disponíveis
  installed  - Lista modelos já instalados
  pull       - Baixa um modelo (e.g., 'pull mistral:7b-instruct-q4_K_M')
  test       - Testa um modelo instalado
  install-all - Instala todos os modelos recomendados

EXEMPLO:
  python manage_models.py pull neural-chat:7b-v3.1-q4_K_M
  python manage_models.py test deepseek-coder:6.7b-base-q4_K_M
  python manage_models.py install-all
        """)
        return
    
    cmd = sys.argv[1]
    
    if cmd == "list":
        list_models()
    elif cmd == "installed":
        list_installed()
    elif cmd == "pull" and len(sys.argv) > 2:
        model = sys.argv[2]
        pull_model(model)
    elif cmd == "test" and len(sys.argv) > 2:
        model = sys.argv[2]
        test_model(model)
    elif cmd == "install-all":
        print("⚙️  Instalando todos os modelos recomendados...\n")
        for model in MODELS.keys():
            if model != "deepseek-coder:6.7b-base-q4_K_M":  # Pular deepseek que já está
                pull_model(model)
                print()
    else:
        print(f"❌ Comando desconhecido: {cmd}")

if __name__ == "__main__":
    main()
