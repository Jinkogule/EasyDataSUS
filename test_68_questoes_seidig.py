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

from routes.query import ask, AskRequest
from metadata.loader import load_metadata


INTEROPERABILITY_GOLD = {
    61: {
        "data_answerability": "full",
        "implementation_support": "supported",
        "expected_datasets": ["surtos-srag", "atencao-basica"],
        "expected_relationships": ["srag_ubs_municipio_notificacao"],
        "reference_sql": """WITH srag_municipalities AS (SELECT DISTINCT co_mun_not AS ibge FROM srag), ubs_municipalities AS (SELECT DISTINCT ibge FROM atencao_basica) SELECT COUNT(*) AS total_municipios FROM srag_municipalities AS s INNER JOIN ubs_municipalities AS u ON s.ibge = u.ibge""",
        "reference_result": None,
        "note": "Conta municípios com SRAG e cobertura de UBS usando o relacionamento municipal.",
    },
    62: {
        "data_answerability": "partial",
        "implementation_support": "supported",
        "expected_datasets": ["surtos-srag", "atencao-basica"],
        "expected_relationships": ["srag_ubs_municipio_notificacao"],
        "reference_sql": None,
        "reference_result": None,
        "note": "A cobertura exige denominador populacional; a formulação atual é parcial.",
    },
    63: {
        "data_answerability": "unavailable",
        "implementation_support": "unsupported",
        "expected_datasets": ["surtos-srag", "leitos", "atencao-basica"],
        "expected_relationships": [],
        "reference_sql": None,
        "reference_result": None,
        "note": "A regra de < 5 leitos por 10k hab exige população, ausente no conjunto atual.",
    },
    64: {
        "data_answerability": "partial",
        "implementation_support": "unsupported",
        "expected_datasets": ["covid-19-vacinacao", "surtos-srag"],
        "expected_relationships": [],
        "reference_sql": None,
        "reference_result": None,
        "note": "Incidência e cobertura exigem denominadores populacionais, ausentes no conjunto atual.",
    },
    65: {
        "data_answerability": "partial",
        "implementation_support": "unsupported",
        "expected_datasets": ["surtos-srag", "leitos"],
        "expected_relationships": [],
        "reference_sql": None,
        "reference_result": None,
        "note": "Exige relacionamento SRAG–Leitos e definição explícita da taxa de UTI disponível.",
    },
    66: {
        "data_answerability": "partial",
        "implementation_support": "unsupported",
        "expected_datasets": ["surtos-srag", "leitos"],
        "expected_relationships": [],
        "reference_sql": None,
        "reference_result": None,
        "note": "A métrica de internação em 7 dias pode ser respondida apenas se a base expuser datas compatíveis.",
    },
    67: {
        "data_answerability": "unavailable",
        "implementation_support": "unsupported",
        "expected_datasets": ["atencao-basica", "covid-19-vacinacao"],
        "expected_relationships": [],
        "reference_sql": None,
        "reference_result": None,
        "note": "A correlação em densidade por estado precisa de população ou de uma definição alternativa de densidade.",
    },
    68: {
        "data_answerability": "partial",
        "implementation_support": "unsupported",
        "expected_datasets": ["surtos-srag", "leitos", "atencao-basica"],
        "expected_relationships": [],
        "reference_sql": None,
        "reference_result": None,
        "note": "O déficit de resposta depende de uma regra explícita para leitos insuficientes.",
    },
}


def get_interoperability_rubric(question_number: int) -> dict:
    return INTEROPERABILITY_GOLD.get(question_number, {})


def _normalize_string_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[,;]", value) if item.strip()]
    if isinstance(value, dict):
        for key in ("id", "name", "table_name", "relationship", "dataset"):
            if key in value and value[key]:
                return [str(value[key]).strip()]
        return []
    if isinstance(value, list):
        normalized = []
        for item in value:
            if isinstance(item, dict):
                for key in ("id", "name", "table_name", "relationship", "dataset"):
                    if key in item and item[key]:
                        normalized.append(str(item[key]).strip())
                        break
            elif item is not None:
                normalized.append(str(item).strip())
        return [item for item in normalized if item]
    return [str(value).strip()]


def _relationship_key(value):
    if isinstance(value, dict):
        for key in ("id", "name", "relationship", "relationship_id"):
            if key in value and value[key]:
                return str(value[key]).strip()
        source = value.get("source_dataset") or value.get("source")
        target = value.get("target_dataset") or value.get("target")
        if source and target:
            return f"{source}:{target}"
    return str(value).strip() if value is not None else ""


def _compute_selection_metrics(results: list[dict]) -> dict:
    dataset_evaluated = [result for result in results if result.get("expected_datasets")]
    relationship_evaluated = [
        result
        for result in results
        if result.get("implementation_support") == "supported"
        and result.get("expected_relationships")
    ]
    if not dataset_evaluated:
        return {"evaluated": 0}

    dataset_tp = dataset_fp = dataset_fn = 0
    relationship_tp = relationship_fp = relationship_fn = 0
    exact_matches = 0
    relationship_exact_matches = 0

    for result in dataset_evaluated:
        expected_datasets = set(_normalize_string_list(result.get("expected_datasets")))
        predicted_datasets = set(_normalize_string_list(result.get("datasets")))
        dataset_tp += len(expected_datasets & predicted_datasets)
        dataset_fp += len(predicted_datasets - expected_datasets)
        dataset_fn += len(expected_datasets - predicted_datasets)
        if expected_datasets == predicted_datasets:
            exact_matches += 1

    for result in relationship_evaluated:
        expected_relationships = set(_normalize_string_list(result.get("expected_relationships")))
        predicted_relationships = {
            _relationship_key(item)
            for item in _normalize_string_list(result.get("relationships"))
        }
        relationship_tp += len(expected_relationships & predicted_relationships)
        relationship_fp += len(predicted_relationships - expected_relationships)
        relationship_fn += len(expected_relationships - predicted_relationships)
        if expected_relationships == predicted_relationships:
            relationship_exact_matches += 1

    def _prf(tp, fp, fn):
        precision = tp / (tp + fp) if (tp + fp) else None
        recall = tp / (tp + fn) if (tp + fn) else None
        f1 = (2 * precision * recall / (precision + recall)) if precision is not None and recall is not None and (precision + recall) else None
        return {"precision": precision, "recall": recall, "f1": f1}

    return {
        "evaluated": len(dataset_evaluated),
        "dataset_selection": {
            **_prf(dataset_tp, dataset_fp, dataset_fn),
            "evaluated": len(dataset_evaluated),
            "exact_match_rate": exact_matches / len(dataset_evaluated),
        },
        "relationship_selection": {
            **_prf(relationship_tp, relationship_fp, relationship_fn),
            "evaluated": len(relationship_evaluated),
            "exact_match_rate": (
                relationship_exact_matches / len(relationship_evaluated)
                if relationship_evaluated else None
            ),
        },
    }


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
            rubric = get_interoperability_rubric(q_num) if current_dataset == "interoperabilidade" else {}
            questions_dict[current_dataset].append({
                "id": question_id,
                "number": q_num,
                "question": q_text,
                "objetivo": objetivo or "Não especificado",
                "complexidade": complexidade,
                "bloco": current_bloco or "Geral",
                "dataset": current_dataset,
                **rubric,
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
    use_endpoint_dataset = None if dataset == "interoperabilidade" else dataset
    
    result = {
        "question_id": question_data["id"],
        "question": question_data["question"],
        "dataset": dataset,
        "bloco": question_data.get("bloco"),
        "complexidade": question_data.get("complexidade"),
        "data_answerability": question_data.get("data_answerability"),
        "implementation_support": question_data.get("implementation_support"),
        "expected_datasets": question_data.get("expected_datasets"),
        "expected_relationships": question_data.get("expected_relationships"),
        "reference_sql": question_data.get("reference_sql"),
        "reference_result": question_data.get("reference_result"),
        "benchmark_note": question_data.get("note"),
        "status": "pending",
        "sql_generated": None,
        "execution_time": 0,
        "result_rows": 0,
        "interpretation": None,
        "error_message": None
    }
    
    try:
        if verbose:
            print(f"  [ASK]...", end=" ", flush=True)

        request = AskRequest(
            question=question_data["question"],
            model="deepseek-local",
            dataset=use_endpoint_dataset,
        )

        start = time.time()
        response = ask(request)
        execution_time = time.time() - start
        result["execution_time"] = execution_time

        if isinstance(response, dict):
            result["sql_generated"] = response.get("sql")
            data = response.get("data")
            result["result_rows"] = len(data) if isinstance(data, list) else 0
            result["interpretation"] = response.get("insight")
            result["datasets"] = response.get("datasets")
            result["cross_dataset"] = response.get("cross_dataset")
            result["relationships"] = response.get("relationships")
            result["routing_mode"] = response.get("routing_mode")
            result["sql_generation_mode"] = response.get("sql_generation_mode")
            result["validation"] = response.get("validation")
            result["timing_s"] = response.get("timing_s")

            if response.get("success"):
                result["status"] = "success"
            else:
                result["status"] = "error"
                result["error_message"] = data.get("error") if isinstance(data, dict) else "Falha no endpoint"

            if verbose:
                print("✓" if result["status"] == "success" else "✗")

            return result

        result["status"] = "error"
        result["error_message"] = "Resposta inválida do endpoint"
        if verbose:
            print("✗")
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
    fully_answerable_results = [r for r in all_results if r.get("data_answerability") == "full"]
    partial_results = [r for r in all_results if r.get("data_answerability") == "partial"]
    unavailable_results = [r for r in all_results if r.get("data_answerability") == "unavailable"]
    supported_results = [r for r in all_results if r.get("implementation_support") == "supported"]
    fully_answerable_executed = sum(1 for r in fully_answerable_results if r["status"] == "success")
    evaluation_metrics = _compute_selection_metrics(all_results)
    
    print(f"\n{'='*100}")
    print(f"📊 RESUMO FINAL")
    print(f"{'='*100}")
    print(f"Total: {len(all_results)} questões testadas")
    print(f"✅ Sucessos: {total_passed} ({total_passed/len(all_results)*100:.1f}%)")
    print(f"❌ Falhas: {total_failed} ({total_failed/len(all_results)*100:.1f}%)")
    if fully_answerable_results:
        print(f"🎯 Execuções bem-sucedidas nas questões plenamente respondíveis: {fully_answerable_executed}/{len(fully_answerable_results)} ({fully_answerable_executed/len(fully_answerable_results)*100:.1f}%)")
    print(f"🟨 Questões parciais: {len(partial_results)}")
    print(f"🟥 Questões indisponíveis com os dados atuais: {len(unavailable_results)}")
    print(f"🧩 Questões com suporte implementado: {len(supported_results)}")
    if evaluation_metrics.get("evaluated"):
        dataset_metrics = evaluation_metrics.get("dataset_selection", {})
        relationship_metrics = evaluation_metrics.get("relationship_selection", {})
        print(
            "📐 Seleção de datasets: "
            f"P={dataset_metrics.get('precision') if dataset_metrics.get('precision') is not None else 'n/a'} "
            f"R={dataset_metrics.get('recall') if dataset_metrics.get('recall') is not None else 'n/a'} "
            f"F1={dataset_metrics.get('f1') if dataset_metrics.get('f1') is not None else 'n/a'}"
        )
        print(
            "🔗 Seleção de relacionamentos: "
            f"P={relationship_metrics.get('precision') if relationship_metrics.get('precision') is not None else 'n/a'} "
            f"R={relationship_metrics.get('recall') if relationship_metrics.get('recall') is not None else 'n/a'} "
            f"F1={relationship_metrics.get('f1') if relationship_metrics.get('f1') is not None else 'n/a'}"
        )
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
            "fully_answerable_total": len(fully_answerable_results),
            "fully_answerable_executed": fully_answerable_executed,
            "fully_answerable_execution_rate": (fully_answerable_executed / len(fully_answerable_results)) if fully_answerable_results else None,
            "partial_total": len(partial_results),
            "unavailable_total": len(unavailable_results),
            "implementation_supported_total": len(supported_results),
            "evaluation": evaluation_metrics,
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
