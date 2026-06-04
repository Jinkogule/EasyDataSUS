#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script para testar as 68 Questões SEIDIG da ferramenta EasyDataSUS.

Essas questões estão alinhadas com Objetivos Estratégicos do SEIDIG:
- OE 3.6.1: Imunização (COVID-19 + UBS)
- OE 9.1: Vigilância Epidemiológica (SRAG) + Gestão Assistencial (Leitos)

Distribuição:
- COVID-19: 15 questões (Q1-Q15)
- UBS: 15 questões (Q16-Q30)
- SRAG: 15 questões (Q31-Q45)
- Leitos: 15 questões (Q46-Q60)
- Interoperabilidade: 8 questões (Q61-Q68)

Uso:
    python test_68_questoes_seidig.py
    python test_68_questoes_seidig.py --dataset covid-19-vacinacao
    python test_68_questoes_seidig.py --verbose
    python test_68_questoes_seidig.py --start 31 --end 45  # Apenas SRAG
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
from config.datasets import get_table_name, DATASETS_CONFIG
from metadata.loader import load_metadata


def parse_68_questions() -> dict:
    """
    Parse as 68 questões SEIDIG do markdown.
    
    Returns:
        {
            "covid-19-vacinacao": [
                {
                    "id": 1,
                    "question": "...",
                    "objetivo": "...",
                    "complexidade": "Simples|Média|Complexa",
                    "bloco": "Monitoramento de Cobertura"
                },
                ...
            ],
            "surtos-srag": [...],
            "atencao-basica": [...],
            "leitos": [...],
            "interoperabilidade": [...]
        }
    """
    
    markdown_file = Path(__file__).parent / "docs" / "PERGUNTAS_SEIDIG_68.md"
    
    if not markdown_file.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {markdown_file}")
    
    with open(markdown_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    questions_dict = {}
    current_dataset = None
    current_bloco = None
    question_id = 0
    
    # Mapping de seções para dataset
    dataset_mapping = {
        "COVID-19 Vacinação": "covid-19-vacinacao",
        "ATENÇÃO PRIMÁRIA: UBS": "atencao-basica",
        "VIGILÂNCIA EPIDEMIOLÓGICA: SRAG": "surtos-srag",
        "GESTÃO ASSISTENCIAL: Leitos": "leitos",
        "INTEROPERABILIDADE: Análises Integradas": "interoperabilidade"
    }
    
    # Inicializar datasets
    for dataset in dataset_mapping.values():
        questions_dict[dataset] = []
    
    # Parse por seção
    lines = content.split('\n')
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Detectar seção de dataset
        for section_name, dataset_id in dataset_mapping.items():
            if section_name in line and "##" in line:
                current_dataset = dataset_id
                current_bloco = None
                break
        
        # Detectar bloco
        if line.startswith("#### ") and current_dataset:
            current_bloco = line.replace("#### ", "").strip()
        
        # Detectar questão numerada
        match = re.match(r"^(\d+)\. \*?\*?([^*]+)\*?\*?$", line)
        if match and current_dataset:
            q_num = int(match.group(1))
            q_text = match.group(2).strip()
            
            # Extrair objetivo e complexidade das próximas linhas
            objetivo = None
            complexidade = "Média"  # default
            campos = None
            
            j = i + 1
            while j < len(lines) and j < i + 10:
                next_line = lines[j]
                
                if "Objetivo:" in next_line:
                    objetivo = next_line.split("Objetivo:")[-1].strip()
                
                if "Complexidade:" in next_line:
                    match_comp = re.search(r"(Simples|Média|Complexa)", next_line)
                    if match_comp:
                        complexidade = match_comp.group(1)
                
                if "Campo" in next_line or "Campos:" in next_line:
                    campos = next_line.split("Campo")[-1].strip()
                
                # Parar se encontrou próxima questão
                if re.match(r"^\d+\. \*?\*?", next_line):
                    break
                
                j += 1
            
            question_id += 1
            questions_dict[current_dataset].append({
                "id": question_id,
                "number": q_num,
                "question": q_text,
                "objetivo": objetivo or "Não especificado",
                "complexidade": complexidade,
                "bloco": current_bloco or "Geral",
                "dataset": current_dataset
            })
        
        i += 1
    
    if not any(questions_dict.values()):
        raise ValueError(f"Nenhuma pergunta encontrada em {markdown_file}")
    
    return questions_dict


def test_question(question_data: dict, verbose: bool = False) -> dict:
    """
    Testa uma pergunta individual.
    
    Returns:
        {
            "question_id": int,
            "question": str,
            "dataset": str,
            "status": "success" | "sql_error" | "exec_error" | "interp_error" | "error",
            "sql_generated": str,
            "execution_time": float,
            "result_rows": int,
            "interpretation": str,
            "error_message": str
        }
    """
    dataset = question_data["dataset"]
    
    result = {
        "question_id": question_data["id"],
        "question": question_data["question"],
        "dataset": dataset,
        "bloco": question_data.get("bloco"),
        "complexidade": question_data.get("complexidade"),
        "status": "pending",
        "sql_generated": None,
        "execution_time": 0,
        "result_rows": 0,
        "interpretation": None,
        "error_message": None
    }
    
    try:
        # Carregar metadata
        metadata = None
        try:
            metadata = load_metadata(dataset)
            if isinstance(metadata, dict):
                metadata = json.dumps(metadata, ensure_ascii=False)
        except Exception:
            metadata = "{}"
        
        # Gerar SQL
        if verbose:
            print(f"  [SQL]...", end=" ", flush=True)
        
        sql = generate_sql(
            question=question_data["question"],
            metadata=metadata,
            model_name="deepseek-local",
            dataset=dataset
        )
        
        if not sql:
            result["status"] = "sql_error"
            result["error_message"] = "Nenhum SQL gerado"
            return result
        
        result["sql_generated"] = sql
        
        if verbose:
            print(f"✓ | [EXEC]...", end=" ", flush=True)
        
        # Executar query
        start = time.time()
        query_result = run_query(sql)
        execution_time = time.time() - start
        
        result["execution_time"] = execution_time
        
        if isinstance(query_result, dict) and "error" in query_result:
            result["status"] = "exec_error"
            result["error_message"] = query_result.get("error")
            if verbose:
                print(f"✗")
            return result
        
        result["result_rows"] = len(query_result) if isinstance(query_result, list) else 0
        
        if verbose:
            print(f"✓ ({result['result_rows']} linhas, {execution_time:.2f}s) | [INTERP]...", end=" ", flush=True)
        
        # Interpretar resultado
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
            print(f"✗")
        return result


def run_test_suite(dataset_filter: str = None, start_q: int = None, end_q: int = None, verbose: bool = False):
    """
    Executa suite de teste das 68 questões SEIDIG.
    
    Args:
        dataset_filter: Filtrar por dataset específico
        start_q: Número da primeira questão
        end_q: Número da última questão
        verbose: Output detalhado
    """
    
    print(f"📖 Carregando 68 Questões SEIDIG...")
    
    try:
        test_questions = parse_68_questions()
    except Exception as e:
        print(f"❌ Erro ao parsear questões: {e}")
        return
    
    # Montar lista de questões para testar
    all_questions = []
    for dataset, questions in test_questions.items():
        all_questions.extend(questions)
    
    # Aplicar filtros
    if dataset_filter:
        all_questions = [q for q in all_questions if q["dataset"] == dataset_filter]
    
    if start_q or end_q:
        start_q = start_q or 1
        end_q = end_q or len(all_questions)
        all_questions = [q for q in all_questions if start_q <= q["id"] <= end_q]
    
    if not all_questions:
        print("❌ Nenhuma questão para testar com os filtros aplicados")
        return
    
    # Executar testes
    print(f"\n{'='*100}")
    print(f"🧪 TESTE DE 68 QUESTÕES SEIDIG")
    print(f"{'='*100}")
    print(f"Total de questões: {len(all_questions)}\n")
    
    all_results = []
    start_time_total = time.time()
    
    # Agrupar por dataset
    questions_by_dataset = {}
    for q in all_questions:
        ds = q["dataset"]
        if ds not in questions_by_dataset:
            questions_by_dataset[ds] = []
        questions_by_dataset[ds].append(q)
    
    for dataset, questions in sorted(questions_by_dataset.items()):
        print(f"\n{'─'*100}")
        
        # Mapa de emojis
        emoji_map = {
            "covid-19-vacinacao": "💉",
            "atencao-basica": "🏘️",
            "surtos-srag": "🦠",
            "leitos": "🛏️",
            "interoperabilidade": "🔗"
        }
        
        emoji = emoji_map.get(dataset, "📊")
        print(f"{emoji} Dataset: {dataset}")
        print(f"{'─'*100}")
        
        dataset_results = []
        passed = 0
        failed = 0
        
        for idx, question in enumerate(questions, 1):
            q_id = question["id"]
            bloco = question.get("bloco", "")
            comp = question.get("complexidade", "")
            
            if verbose:
                print(f"\nQ{q_id}: {question['question'][:70]}...")
                print(f"    Bloco: {bloco} | Complexidade: {comp}")
            else:
                print(f"Q{q_id:02d} | {question['question'][:60]:60s} | {comp:8s} | ", end="", flush=True)
            
            result = test_question(question, verbose=verbose)
            
            if not verbose:
                status_emoji = "✅" if result["status"] == "success" else "❌"
                print(f"{status_emoji} {result['status']}")
            
            if result["status"] == "success":
                passed += 1
            else:
                failed += 1
            
            dataset_results.append(result)
            all_results.append(result)
        
        print(f"\nResultado: {passed}/{len(questions)} ✅")
    
    # Resumo final
    total_time = time.time() - start_time_total
    total_passed = sum(1 for r in all_results if r["status"] == "success")
    total_failed = len(all_results) - total_passed
    
    print(f"\n{'='*100}")
    print(f"📊 RESUMO FINAL")
    print(f"{'='*100}")
    print(f"Total: {len(all_results)} questões testadas")
    print(f"✅ Sucessos: {total_passed} ({total_passed/len(all_results)*100:.1f}%)")
    print(f"❌ Falhas: {total_failed} ({total_failed/len(all_results)*100:.1f}%)")
    print(f"⏱️  Tempo total: {total_time:.1f}s ({total_time/len(all_results):.2f}s/questão)")
    
    # Salvar resultados
    results_file = Path(__file__).parent / "test_results_68_questoes.json"
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_questions": len(all_results),
            "passed": total_passed,
            "failed": total_failed,
            "success_rate": total_passed / len(all_results),
            "total_time": total_time,
            "results": all_results
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Resultados salvos: {results_file}")


def main():
    parser = argparse.ArgumentParser(description="Teste das 68 Questões SEIDIG")
    parser.add_argument("--dataset", help="Filtrar por dataset")
    parser.add_argument("--start", type=int, help="Primeira questão (número)")
    parser.add_argument("--end", type=int, help="Última questão (número)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Output detalhado")
    
    args = parser.parse_args()
    
    run_test_suite(
        dataset_filter=args.dataset,
        start_q=args.start,
        end_q=args.end,
        verbose=args.verbose
    )


if __name__ == "__main__":
    main()
