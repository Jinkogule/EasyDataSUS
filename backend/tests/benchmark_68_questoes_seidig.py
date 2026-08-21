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
    python backend/tests/benchmark_68_questoes_seidig.py
    python backend/tests/benchmark_68_questoes_seidig.py --dataset covid-19-vacinacao
    python backend/tests/benchmark_68_questoes_seidig.py --verbose
    python backend/tests/benchmark_68_questoes_seidig.py --start 31 --end 45  # Apenas SRAG
"""

import sys
import json
import time
import re
from pathlib import Path
from datetime import datetime
import argparse
import os
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = PROJECT_ROOT / "backend"

# Adicionar backend ao path
sys.path.insert(0, str(BACKEND_DIR))

from routes.query import ask, AskRequest
from metadata.loader import load_metadata
from llm.router import get_model_identifier


INTEROPERABILITY_GOLD = {
    61: {
        "data_answerability": "full",
        "implementation_support": "supported",
        "expected_datasets": ["surtos-srag", "atencao-basica"],
        "expected_relationships": ["srag_ubs_municipio_notificacao"],
        "reference_sql": """WITH srag_municipalities AS (SELECT DISTINCT co_mun_not AS ibge FROM srag), ubs_municipalities AS (SELECT DISTINCT ibge FROM atencao_basica) SELECT COUNT(*) AS total_municipios FROM srag_municipalities AS s INNER JOIN ubs_municipalities AS u ON s.ibge = u.ibge""",
        "reference_result": None,
        "note": "Conta municípios com notificações de SRAG e UBS cadastradas usando o relacionamento municipal.",
    },
    62: {
        "data_answerability": "full",
        "implementation_support": "supported",
        "expected_datasets": ["surtos-srag", "atencao-basica"],
        "expected_relationships": ["srag_ubs_municipio_notificacao"],
        "reference_sql": """WITH srag_by_municipality AS (SELECT co_mun_not AS ibge, COUNT(*) AS total_srag FROM srag GROUP BY co_mun_not), ubs_by_municipality AS (SELECT ibge AS ibge, COUNT(DISTINCT cnes) AS total_ubs FROM atencao_basica GROUP BY ibge) SELECT s.ibge, s.total_srag, u.total_ubs FROM srag_by_municipality AS s INNER JOIN ubs_by_municipality AS u ON s.ibge = u.ibge ORDER BY s.total_srag DESC LIMIT 100""",
        "reference_result": None,
        "note": "Lista municípios com notificações de SRAG e quantidade de UBS usando relacionamento municipal.",
    },
    63: {
        "data_answerability": "full",
        "implementation_support": "supported",
        "expected_datasets": ["covid-19-vacinacao", "leitos"],
        "expected_relationships": ["vacinacao_leitos_uf"],
        "reference_sql": None,
        "reference_result": None,
        "note": "Compara registros de vacinação e leitos de UTI por UF usando relacionamento previamente cadastrado.",
    },
    64: {
        "data_answerability": "full",
        "implementation_support": "supported",
        "expected_datasets": ["covid-19-vacinacao", "leitos"],
        "expected_relationships": ["vacinacao_leitos_uf"],
        "reference_sql": None,
        "reference_result": None,
        "note": "Compara doses registradas e leitos de UTI por UF com pré-agregação dos dois lados.",
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
        "note": "Exige relacionamento SRAG–Leitos por UF ou município, ainda não cadastrado.",
    },
    67: {
        "data_answerability": "partial",
        "implementation_support": "unsupported",
        "expected_datasets": ["atencao-basica", "covid-19-vacinacao"],
        "expected_relationships": [],
        "reference_sql": None,
        "reference_result": None,
        "note": "Exige relacionamento UBS–Vacinação por UF ou município, ainda não cadastrado.",
    },
    68: {
        "data_answerability": "partial",
        "implementation_support": "unsupported",
        "expected_datasets": ["surtos-srag", "leitos", "atencao-basica"],
        "expected_relationships": [],
        "reference_sql": None,
        "reference_result": None,
        "note": "Exige consulta envolvendo três domínios e regra explícita para baixa disponibilidade de leitos.",
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


def _next_versioned_path(path: Path) -> Path:
    """Retorna path, path_V2, path_V3... sem sobrescrever resultados anteriores."""

    if not path.exists():
        return path

    version = 2
    while True:
        candidate = path.with_name(f"{path.stem}_V{version}{path.suffix}")
        if not candidate.exists():
            return candidate
        version += 1


def _format_metric(value):
    return value if value is not None else "n/a"


def _build_summary_lines(
    *,
    total_questions: int,
    total_passed: int,
    controlled_limitations: int,
    total_failed: int,
    fully_answerable_executed: int,
    fully_answerable_total: int,
    partial_total: int,
    unavailable_total: int,
    supported_total: int,
    evaluation_metrics: dict,
    total_time: float,
) -> list[str]:
    dataset_metrics = evaluation_metrics.get("dataset_selection", {})
    relationship_metrics = evaluation_metrics.get("relationship_selection", {})
    lines = [
        "RESUMO FINAL",
        f"Total: {total_questions} questões testadas",
        f"Sucessos: {total_passed} ({total_passed/total_questions*100:.1f}%)",
        f"Limitações controladas: {controlled_limitations} ({controlled_limitations/total_questions*100:.1f}%)",
        f"Falhas técnicas: {total_failed} ({total_failed/total_questions*100:.1f}%)",
    ]
    if fully_answerable_total:
        lines.append(
            "Execuções bem-sucedidas nas questões plenamente respondíveis: "
            f"{fully_answerable_executed}/{fully_answerable_total} "
            f"({fully_answerable_executed/fully_answerable_total*100:.1f}%)"
        )
    lines.extend([
        f"Questões parciais: {partial_total}",
        f"Questões indisponíveis com os dados atuais: {unavailable_total}",
        f"Questões com suporte implementado: {supported_total}",
    ])
    if evaluation_metrics.get("evaluated"):
        lines.extend([
            "Seleção de datasets: "
            f"P={_format_metric(dataset_metrics.get('precision'))} "
            f"R={_format_metric(dataset_metrics.get('recall'))} "
            f"F1={_format_metric(dataset_metrics.get('f1'))}",
            "Seleção de relacionamentos: "
            f"P={_format_metric(relationship_metrics.get('precision'))} "
            f"R={_format_metric(relationship_metrics.get('recall'))} "
            f"F1={_format_metric(relationship_metrics.get('f1'))}",
        ])
    lines.append(f"Tempo total: {total_time:.1f}s ({total_time/total_questions:.2f}s/questão)")
    return lines


def _check_ollama_model_available(model_name: str) -> tuple[bool, str, list[str]]:
    """Verifica se o modelo resolvido está disponível no Ollama usado pelo backend."""

    resolved_model = get_model_identifier(model_name)
    ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    try:
        response = requests.get(f"{ollama_host}/api/tags", timeout=10)
        response.raise_for_status()
        available = sorted(
            model.get("name")
            for model in response.json().get("models", [])
            if model.get("name")
        )
    except Exception as exc:
        raise RuntimeError(
            f"Não foi possível consultar os modelos do Ollama em {ollama_host}: {exc}"
        ) from exc

    return resolved_model in available, resolved_model, available


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
    
    markdown_file = PROJECT_ROOT / "docs" / "PERGUNTAS_SEIDIG_68.md"
    
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


def test_question(question_data: dict, model_name: str, verbose: bool = False) -> dict:
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
        "model": model_name,
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
            model=model_name,
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
            result["answerability"] = response.get("answerability")
            result["evaluation_metrics"] = response.get("evaluation_metrics")

            if response.get("success"):
                result["status"] = "success"
            elif (
                question_data.get("implementation_support") == "unsupported"
                or question_data.get("data_answerability") in {"partial", "unavailable"}
            ):
                result["status"] = "controlled_limitation"
                result["error_message"] = data.get("error") if isinstance(data, dict) else "Limitação prevista no gabarito"
            else:
                result["status"] = "error"
                result["error_message"] = data.get("error") if isinstance(data, dict) else "Falha no endpoint"

            if verbose:
                print("OK" if result["status"] == "success" else "FAIL")

            return result

        result["status"] = "error"
        result["error_message"] = "Resposta inválida do endpoint"
        if verbose:
            print("FAIL")
        return result
    
    except Exception as e:
        result["status"] = "error"
        result["error_message"] = str(e)
        if verbose:
            print("FAIL")
        return result


def run_test_suite(
    dataset_filter: str = None,
    start_q: int = None,
    end_q: int = None,
    verbose: bool = False,
    model_name: str = "deepseek-local",
):
    """
    Executa suite de teste das 68 questões SEIDIG.
    
    Args:
        dataset_filter: Filtrar por dataset específico
        start_q: Número da primeira questão
        end_q: Número da última questão
        verbose: Output detalhado
    """
    
    resolved_model = get_model_identifier(model_name)
    try:
        model_available, resolved_model, available_models = _check_ollama_model_available(model_name)
    except RuntimeError as exc:
        print(f"Erro: {exc}")
        return

    if not model_available:
        print("Modelo LLM não disponível no Ollama usado pelo backend.")
        print(f"   Modelo solicitado: {model_name}")
        print(f"   Modelo resolvido: {resolved_model}")
        print("   Modelos disponíveis nesse Ollama:")
        for available_model in available_models:
            print(f"   - {available_model}")
        print("\nInstale o modelo nesse mesmo Ollama antes de rodar o benchmark.")
        print(f"Exemplo: ollama pull {resolved_model}")
        return

    print("Carregando 68 Questões SEIDIG...")
    
    try:
        test_questions = parse_68_questions()
    except Exception as e:
        print(f"Erro ao parsear questões: {e}")
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
        print("Nenhuma questão para testar com os filtros aplicados")
        return
    
    # Executar testes
    print(f"\n{'='*100}")
    print("TESTE DE 68 QUESTÕES SEIDIG")
    print(f"{'='*100}")
    print(f"Modelo LLM: {model_name}")
    print(f"Modelo Ollama resolvido: {resolved_model}")
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
        
        print(f"Dataset: {dataset}")
        print(f"{'─'*100}")
        
        dataset_results = []
        passed = 0
        failed = 0
        controlled = 0
        
        for idx, question in enumerate(questions, 1):
            q_id = question["id"]
            bloco = question.get("bloco", "")
            comp = question.get("complexidade", "")
            
            if verbose:
                print(f"\nQ{q_id}: {question['question'][:70]}...")
                print(f"    Bloco: {bloco} | Complexidade: {comp}")
            else:
                print(f"Q{q_id:02d} | {question['question'][:60]:60s} | {comp:8s} | ", end="", flush=True)
            
            result = test_question(question, model_name=model_name, verbose=verbose)
            
            if not verbose:
                status_label = {
                    "success": "success",
                    "controlled_limitation": "controlled_limitation",
                }.get(result["status"], "error")
                print(status_label)
            
            if result["status"] == "success":
                passed += 1
            elif result["status"] == "controlled_limitation":
                controlled += 1
            else:
                failed += 1
            
            dataset_results.append(result)
            all_results.append(result)
        
        print(f"\nResultado: {passed}/{len(questions)} success | {controlled} controlled_limitation | {failed} error")
    
    # Resumo final
    total_time = time.time() - start_time_total
    total_passed = sum(1 for r in all_results if r["status"] == "success")
    controlled_limitations = sum(1 for r in all_results if r["status"] == "controlled_limitation")
    total_failed = len(all_results) - total_passed - controlled_limitations
    fully_answerable_results = [r for r in all_results if r.get("data_answerability") == "full"]
    partial_results = [r for r in all_results if r.get("data_answerability") == "partial"]
    unavailable_results = [r for r in all_results if r.get("data_answerability") == "unavailable"]
    supported_results = [r for r in all_results if r.get("implementation_support") == "supported"]
    fully_answerable_executed = sum(1 for r in fully_answerable_results if r["status"] == "success")
    evaluation_metrics = _compute_selection_metrics(all_results)
    summary_lines = _build_summary_lines(
        total_questions=len(all_results),
        total_passed=total_passed,
        controlled_limitations=controlled_limitations,
        total_failed=total_failed,
        fully_answerable_executed=fully_answerable_executed,
        fully_answerable_total=len(fully_answerable_results),
        partial_total=len(partial_results),
        unavailable_total=len(unavailable_results),
        supported_total=len(supported_results),
        evaluation_metrics=evaluation_metrics,
        total_time=total_time,
    )
    
    print(f"\n{'='*100}")
    print(summary_lines[0])
    print(f"{'='*100}")
    for line in summary_lines[1:]:
        print(line)
    
    # Salvar resultados
    experiments_dir = PROJECT_ROOT / "experimentos"
    experiments_dir.mkdir(exist_ok=True)
    results_file = _next_versioned_path(experiments_dir / "test_results_68_questoes.json")
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "sql_generation_strategy": os.getenv("SQL_GENERATION_STRATEGY", "llm_first"),
            "model": model_name,
            "model_alias": model_name,
            "resolved_model": resolved_model,
            "experiment_valid_for_model_comparison": True,
            "experiment_summary_comment": "\n".join(summary_lines),
            "summary_lines": summary_lines,
            "total_questions": len(all_results),
            "passed": total_passed,
            "controlled_limitations": controlled_limitations,
            "failed": total_failed,
            "success_rate": total_passed / len(all_results),
            "technical_failure_rate": total_failed / len(all_results),
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
    
    print(f"\nResultados salvos: {results_file}")


def main():
    parser = argparse.ArgumentParser(description="Teste das 68 Questões SEIDIG")
    parser.add_argument("--dataset", help="Filtrar por dataset")
    parser.add_argument("--start", type=int, help="Primeira questão (número)")
    parser.add_argument("--end", type=int, help="Última questão (número)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Output detalhado")
    parser.add_argument(
        "--model",
        default="deepseek-local",
        help="Modelo LLM usado no endpoint /api/ask, por exemplo: deepseek-local, deepseek-r1:7b ou deepseek-coder:latest",
    )
    parser.add_argument(
        "--generation-strategy",
        choices=["llm_first", "deterministic_first"],
        default="llm_first",
        help="Estratégia de geração SQL; experimentos Text-to-SQL usam llm_first",
    )
    
    args = parser.parse_args()
    os.environ["SQL_GENERATION_STRATEGY"] = args.generation_strategy
    
    run_test_suite(
        dataset_filter=args.dataset,
        start_q=args.start,
        end_q=args.end,
        verbose=args.verbose,
        model_name=args.model,
    )


if __name__ == "__main__":
    main()
