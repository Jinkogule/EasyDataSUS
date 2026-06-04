"""
Script de teste das perguntas para validação da ferramenta EasyDataSUS.

Este script testa a ferramenta contra todas as perguntas definidas no documento
PERGUNTAS_TESTE_GESTOR.md, permitindo uma abordagem agnóstica ao conteúdo.

Uso:
    python test_52_questions.py
    python test_52_questions.py --dataset covid-19-vacinacao  # Apenas COVID
    python test_52_questions.py --dataset leitos              # Apenas Leitos
    python test_52_questions.py --verbose                      # Com output detalhado
    python test_52_questions.py --questions-file custom.md    # Arquivo customizado
"""

import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime
import argparse

# Adicionar backend ao path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from services.sql_service import generate_sql
from db.clickhouse import run_query
from services.interpretation_service import interpret_result
from config.datasets import get_table_name
from metadata.loader import load_metadata


def parse_questions_from_markdown(markdown_file: Path) -> dict:
    """
    Parse questions from markdown file dynamically.
    
    Esperado formato:
    ## 📊 DATASET: <dataset_name>
    
    ### Categoria 1: <category_name>
    
    1. **Question text here?**
       - Campo: ...
       - Objetivo: ...
    
    2. **Another question?**
       ...
    
    Args:
        markdown_file: Path to PERGUNTAS_TESTE_GESTOR.md
    
    Returns:
        {
            "covid-19-vacinacao": [
                {"id": 1, "question": "...", "category": "..."},
                ...
            ],
            "leitos": [...]
        }
    """
    if not markdown_file.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {markdown_file}")
    
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    questions_dict = {}
    current_dataset = None
    current_category = None
    question_id = 0
    
    # Pattern para seções de dataset
    # Usa split para dividir o arquivo por cada "## ... DATASET:" header
    dataset_sections = re.split(r"(?=^## .* DATASET:)", content, flags=re.MULTILINE)
    
    for dataset_section in dataset_sections:
        # Extrair nome do dataset do header
        dataset_match = re.search(r"^## .* DATASET: ([^\n]+)", dataset_section, re.MULTILINE)
        if not dataset_match:
            continue  # Pular se não tiver header válido
        
        dataset_name = dataset_match.group(1).strip()
        questions_dict[dataset_name] = []
        
        # Pattern para categorias dentro do dataset
        category_pattern = r"### Categoria \d+:\s+(.+?)(?=###|$)"
        
        for category_match in re.finditer(category_pattern, dataset_section, re.DOTALL):
            category_name = category_match.group(1).strip()
            category_section = category_match.group(0)
            
            # Pattern para questões numeradas
            # Procura por: "1. **Question text?**" ou "1. Question text?"
            question_pattern = r"^(\d+)\.\s+\*?\*?([^*\n]+?)\*?\*?$"
            
            for question_match in re.finditer(question_pattern, category_section, re.MULTILINE):
                question_num = int(question_match.group(1))
                question_text = question_match.group(2).strip()
                
                # Limpar marcação de negrito se houver
                question_text = re.sub(r'\*+', '', question_text).strip()
                
                if question_text:
                    question_id += 1
                    questions_dict[dataset_name].append({
                        "id": question_id,
                        "number": question_num,
                        "question": question_text,
                        "category": category_name,
                        "dataset": dataset_name
                    })
    
    if not questions_dict:
        raise ValueError(f"Nenhuma pergunta encontrada em {markdown_file}")
    
    return questions_dict

def test_question(question_data: dict, dataset: str, verbose: bool = False) -> dict:
    """
    Testa uma pergunta individual e retorna resultado detalhado.
    
    Returns:
        {
            "question_id": int,
            "question": str,
            "dataset": str,
            "status": "success" | "sql_error" | "exec_error" | "interp_error",
            "sql_generated": str | None,
            "sql_valid": bool,
            "execution_time": float,
            "result_rows": int,
            "interpretation": str | None,
            "error_message": str | None
        }
    """
    result = {
        "question_id": question_data["id"],
        "question": question_data["question"],
        "dataset": dataset,
        "category": question_data.get("category"),
        "status": "pending",
        "sql_generated": None,
        "sql_valid": False,
        "execution_time": 0,
        "result_rows": 0,
        "interpretation": None,
        "error_message": None
    }
    
    try:
        # Carregar metadata do dataset
        metadata = None
        try:
            metadata = load_metadata(dataset)
            # Garantir que é string JSON
            if isinstance(metadata, dict):
                metadata = json.dumps(metadata, ensure_ascii=False)
        except Exception as e:
            # Fallback: string JSON vazia
            metadata = "{}"
        
        # Step 1: Gerar SQL
        if verbose:
            print(f"  [Gerando SQL]...", end=" ", flush=True)
        
        sql = generate_sql(
            question=question_data["question"],
            metadata=metadata,
            model_name="deepseek-local",
            dataset=dataset
        )
        
        if not sql:
            result["status"] = "sql_error"
            result["error_message"] = "Nenhum SQL foi gerado"
            return result
        
        result["sql_generated"] = sql
        result["sql_valid"] = True
        
        if verbose:
            print(f"✓")
            print(f"    SQL: {sql[:80]}...")
        
        # Step 2: Executar query
        if verbose:
            print(f"  [Executando]...", end=" ", flush=True)
        
        start_time = time.time()
        query_result = run_query(sql)
        execution_time = time.time() - start_time
        
        result["execution_time"] = execution_time
        
        if isinstance(query_result, dict) and "error" in query_result:
            result["status"] = "exec_error"
            result["error_message"] = query_result.get("error", "Erro desconhecido")
            if verbose:
                print(f"✗")
            return result
        
        result["result_rows"] = len(query_result) if isinstance(query_result, list) else 0
        
        if verbose:
            print(f"✓ ({result['result_rows']} linhas, {execution_time:.2f}s)")
        
        # Step 3: Interpretar resultado
        if verbose:
            print(f"  [Interpretando]...", end=" ", flush=True)
        
        interpretation = interpret_result(
            question=question_data["question"],
            result=query_result,
            model_name="deepseek-local",
            dataset=dataset
        )
        
        if isinstance(interpretation, dict):
            if "error" in interpretation:
                result["status"] = "interp_error"
                result["error_message"] = interpretation.get("error")
                if verbose:
                    print(f"✗")
                return result
            
            result["interpretation"] = interpretation.get("insight") or str(interpretation)
        else:
            result["interpretation"] = str(interpretation)
        
        result["status"] = "success"
        
        if verbose:
            print(f"✓")
        
        return result
    
    except Exception as e:
        result["status"] = "error"
        result["error_message"] = str(e)
        if verbose:
            print(f"✗ ({str(e)[:50]})")
        return result


def run_test_suite(markdown_file: Path = None, dataset_filter: str = None, verbose: bool = False):
    """
    Executa suite completo de testes lendo perguntas do markdown.
    
    Args:
        markdown_file: Path to questions markdown file. Se None, usa PERGUNTAS_TESTE_GESTOR.md
        dataset_filter: Se especificado, testa apenas esse dataset
        verbose: Se True, mostra saída detalhada
    """
    
    # Detectar arquivo de perguntas
    if markdown_file is None:
        markdown_file = Path(__file__).parent / "docs" / "PERGUNTAS_TESTE_GESTOR.md"
    else:
        markdown_file = Path(markdown_file)
    
    if not markdown_file.exists():
        print(f"❌ Arquivo de perguntas não encontrado: {markdown_file}")
        print(f"   Procure por: docs/PERGUNTAS_TESTE_GESTOR.md")
        return
    
    print(f"📖 Carregando perguntas de: {markdown_file}")
    
    try:
        test_questions = parse_questions_from_markdown(markdown_file)
    except Exception as e:
        print(f"❌ Erro ao parsear arquivo de perguntas: {e}")
        return
    
    # Filtrar datasets se especificado
    datasets_to_test = {}
    
    if dataset_filter:
        if dataset_filter not in test_questions:
            print(f"❌ Dataset '{dataset_filter}' não encontrado")
            print(f"   Datasets disponíveis: {', '.join(test_questions.keys())}")
            return
        datasets_to_test[dataset_filter] = test_questions[dataset_filter]
    else:
        datasets_to_test = test_questions
    
    # Executar testes
    all_results = []
    start_time_total = time.time()
    
    for dataset, questions in datasets_to_test.items():
        print(f"\n{'='*80}")
        print(f"🔬 Testando Dataset: {dataset}")
        print(f"{'='*80}")
        print(f"Total de questões: {len(questions)}\n")
        
        dataset_results = []
        
        for idx, question_data in enumerate(questions, 1):
            q_id = question_data["id"]
            question = question_data["question"]
            
            print(f"[{idx:2d}/{len(questions)}] Q{q_id}: {question[:60]}...")
            
            result = test_question(question_data, dataset, verbose=verbose)
            dataset_results.append(result)
            all_results.append(result)
            
            if verbose and result["status"] != "success":
                print(f"      ❌ Error: {result['error_message']}")
        
        # Estatísticas do dataset
        success_count = sum(1 for r in dataset_results if r["status"] == "success")
        print(f"\n📊 Resumo {dataset}:")
        print(f"   ✅ Sucesso: {success_count}/{len(questions)} ({100*success_count/len(questions):.1f}%)")
        print(f"   ❌ Falhas: {len(questions) - success_count}/{len(questions)}")
        
        # Detalhamento de erros
        error_counts = {}
        for r in dataset_results:
            if r["status"] != "success":
                error_type = r["status"]
                error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        if error_counts:
            print(f"\n   Detalhamento de erros:")
            for error_type, count in sorted(error_counts.items()):
                print(f"      • {error_type}: {count}")
    
    # Resumo final
    total_time = time.time() - start_time_total
    total_success = sum(1 for r in all_results if r["status"] == "success")
    total_questions = len(all_results)
    
    print(f"\n{'='*80}")
    print(f"📈 RESUMO FINAL")
    print(f"{'='*80}")
    print(f"Total de questões testadas: {total_questions}")
    print(f"Sucesso: {total_success}/{total_questions} ({100*total_success/total_questions:.1f}%)")
    print(f"Tempo total: {total_time:.2f}s")
    print(f"Tempo médio por questão: {total_time/total_questions:.2f}s")
    
    # Salvar resultados
    output_file = Path(__file__).parent / f"test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    
    print(f"\n📁 Resultados salvos em: {output_file}")
    
    return all_results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Teste das perguntas da ferramenta EasyDataSUS (dinâmico)"
    )
    parser.add_argument(
        "--questions-file",
        type=str,
        default=None,
        help="Arquivo markdown com as perguntas (padrão: docs/PERGUNTAS_TESTE_GESTOR.md)"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        help="Testar apenas um dataset específico"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Mostra saída detalhada de cada teste"
    )
    
    args = parser.parse_args()
    
    try:
        run_test_suite(
            markdown_file=args.questions_file,
            dataset_filter=args.dataset,
            verbose=args.verbose
        )
    except Exception as e:
        print(f"\n❌ Erro ao executar testes: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
