#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script de Automação - Inicia todos os serviços EasyDataSUS

Este script inicia:
1. ClickHouse (banco de dados)
2. Ollama (LLM local)
3. FastAPI Backend
4. (Opcionalmente) testa as 68 questões

Uso:
    python run_all_services.py                # Inicia todos os serviços
    python run_all_services.py --test         # Inicia + executa testes
    python run_all_services.py --test-verbose # Inicia + testes detalhado
"""

import subprocess
import time
import sys
import os
import signal
from pathlib import Path
import argparse
import json

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(msg):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{msg.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")

def print_success(msg):
    print(f"{Colors.OKGREEN}✅ {msg}{Colors.ENDC}")

def print_info(msg):
    print(f"{Colors.OKCYAN}ℹ️  {msg}{Colors.ENDC}")

def print_warning(msg):
    print(f"{Colors.WARNING}⚠️  {msg}{Colors.ENDC}")

def print_error(msg):
    print(f"{Colors.FAIL}❌ {msg}{Colors.ENDC}")

def check_docker():
    """Check if Docker is installed and running"""
    print_info("Verificando Docker...")
    try:
        result = subprocess.run(["docker", "ps"], capture_output=True, timeout=5)
        if result.returncode == 0:
            print_success("Docker está rodando")
            return True
        else:
            print_error("Docker não está rodando. Inicie com: docker-compose up -d")
            return False
    except FileNotFoundError:
        print_error("Docker não encontrado. Instale Docker Desktop.")
        return False

def check_ollama():
    """Check if Ollama is accessible"""
    print_info("Verificando Ollama...")
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:11434/api/tags"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print_success("Ollama está acessível em http://localhost:11434")
            return True
        else:
            print_warning("Ollama não respondeu. Será iniciado...")
            return False
    except Exception as e:
        print_warning(f"Ollama não encontrado: {e}")
        return False

def check_clickhouse():
    """Check if ClickHouse is running"""
    print_info("Verificando ClickHouse...")
    try:
        result = subprocess.run(
            ["docker", "exec", "easydatasus-clickhouse-1", "clickhouse-client", "--query", "SELECT 1"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print_success("ClickHouse está rodando")
            return True
        else:
            print_warning("ClickHouse não respondeu. Será iniciado...")
            return False
    except Exception as e:
        print_warning(f"ClickHouse não acessível: {e}")
        return False

def start_clickhouse():
    """Start ClickHouse via docker-compose"""
    print_info("Iniciando ClickHouse...")
    try:
        result = subprocess.run(
            ["docker-compose", "up", "-d", "clickhouse"],
            cwd=Path(__file__).parent,
            capture_output=True,
            timeout=30
        )
        if result.returncode == 0:
            print_success("ClickHouse iniciado")
            time.sleep(3)  # Wait for ClickHouse to be ready
            return True
        else:
            print_error(f"Erro ao iniciar ClickHouse: {result.stderr.decode()}")
            return False
    except Exception as e:
        print_error(f"Erro ao iniciar ClickHouse: {e}")
        return False

def start_ollama():
    """Start Ollama as a background process"""
    print_info("Iniciando Ollama...")
    try:
        # Check if ollama command exists
        result = subprocess.run(["where", "ollama"], capture_output=True, timeout=5)
        if result.returncode != 0:
            print_error("Ollama não encontrado no PATH. Instale com: choco install ollama")
            return False
        
        # Start Ollama in background
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        
        print_info("Aguardando Ollama inicializar...")
        time.sleep(5)
        
        # Verify Ollama is running
        for attempt in range(10):
            try:
                result = subprocess.run(
                    ["curl", "-s", "http://localhost:11434/api/tags"],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    print_success("Ollama iniciado em http://localhost:11434")
                    return True
            except:
                pass
            time.sleep(1)
        
        print_warning("Ollama pode estar iniciando ainda...")
        return True
    except Exception as e:
        print_error(f"Erro ao iniciar Ollama: {e}")
        return False

def start_fastapi():
    """Start FastAPI backend"""
    print_info("Iniciando FastAPI Backend...")
    try:
        backend_dir = Path(__file__).parent / "backend"
        
        # Create subprocess for FastAPI
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
            cwd=backend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        print_info("Aguardando FastAPI inicializar...")
        time.sleep(5)
        
        # Verify FastAPI is running
        for attempt in range(10):
            try:
                result = subprocess.run(
                    ["curl", "-s", "http://localhost:8000/docs"],
                    capture_output=True,
                    timeout=2
                )
                if result.returncode == 0:
                    print_success("FastAPI iniciado em http://localhost:8000")
                    print_info("Documentação em http://localhost:8000/docs")
                    return process
            except:
                pass
            time.sleep(1)
        
        print_warning("FastAPI pode estar iniciando ainda...")
        return process
    except Exception as e:
        print_error(f"Erro ao iniciar FastAPI: {e}")
        return None

def run_tests(verbose=False):
    """Run the 68 questions tests"""
    print_header("🧪 EXECUTANDO TESTES DAS 68 QUESTÕES")
    
    try:
        cmd = [sys.executable, "test_68_questoes_seidig.py"]
        if verbose:
            cmd.append("--verbose")
        
        result = subprocess.run(cmd, cwd=Path(__file__).parent)
        
        if result.returncode == 0:
            print_success("Testes completados com sucesso!")
            
            # Try to display results summary
            results_file = Path(__file__).parent / "test_results_68_questoes.json"
            if results_file.exists():
                with open(results_file, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                
                print_info(f"Total: {results['total_questions']} questões")
                print_success(f"Passaram: {results['passed']} ({results['success_rate']*100:.1f}%)")
                print_info(f"Tempo total: {results['total_time']:.1f}s")
            
            return True
        else:
            print_error("Testes falharam")
            return False
    except Exception as e:
        print_error(f"Erro ao executar testes: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Automação EasyDataSUS - Inicia todos os serviços")
    parser.add_argument("--test", action="store_true", help="Executar testes após iniciar serviços")
    parser.add_argument("--test-verbose", action="store_true", help="Executar testes com saída detalhada")
    
    args = parser.parse_args()
    
    print_header("🚀 AUTOMAÇÃO EASYDATASUS - INICIANDO SERVIÇOS")
    
    # Check prerequisites
    print("\n" + "─"*80)
    print("1️⃣  VERIFICANDO PREREQUISITOS")
    print("─"*80 + "\n")
    
    if not check_docker():
        print_error("Docker é necessário. Instale e tente novamente.")
        return
    
    # Start ClickHouse
    print("\n" + "─"*80)
    print("2️⃣  INICIANDO BANCO DE DADOS (ClickHouse)")
    print("─"*80 + "\n")
    
    if not check_clickhouse():
        if not start_clickhouse():
            print_error("Falha ao iniciar ClickHouse")
            return
    
    # Start Ollama
    print("\n" + "─"*80)
    print("3️⃣  INICIANDO LLM LOCAL (Ollama)")
    print("─"*80 + "\n")
    
    if not check_ollama():
        if not start_ollama():
            print_warning("Ollama não foi iniciado - alguns testes podem falhar")
    
    # Start FastAPI
    print("\n" + "─"*80)
    print("4️⃣  INICIANDO API REST (FastAPI)")
    print("─"*80 + "\n")
    
    fastapi_process = start_fastapi()
    if not fastapi_process:
        print_warning("FastAPI não iniciado - você pode iniciá-lo manualmente em backend/")
    
    # Summary
    print_header("✅ TODOS OS SERVIÇOS INICIADOS")
    
    print(f"{Colors.OKGREEN}{Colors.BOLD}")
    print("Serviços Disponíveis:")
    print(f"  🗄️  ClickHouse:  http://localhost:9000 (admin:admin)")
    print(f"  🧠 Ollama:      http://localhost:11434")
    print(f"  🔌 FastAPI:     http://localhost:8000")
    print(f"  📚 Documentação: http://localhost:8000/docs")
    print(f"{Colors.ENDC}")
    
    # Run tests if requested
    if args.test or args.test_verbose:
        print("\n")
        time.sleep(2)
        run_tests(verbose=args.test_verbose)
    
    # Keep running
    print("\n" + "─"*80)
    print("Pressione Ctrl+C para parar os serviços")
    print("─"*80 + "\n")
    
    try:
        if fastapi_process:
            fastapi_process.wait()
        else:
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nParando serviços...")
        if fastapi_process:
            fastapi_process.terminate()
            fastapi_process.wait(timeout=5)
        print_success("Serviços parados")

if __name__ == "__main__":
    main()
