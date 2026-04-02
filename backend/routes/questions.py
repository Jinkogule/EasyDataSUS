"""
Endpoint de perguntas pré-prontas com roteamento por dataset.

Implementa descoberta automática de datasets e associação
de perguntas ao dataset correto, essencial para escalabilidade.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from metadata.loader import load_metadata
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# ============================================================================
# PERGUNTAS PRÉ-PRONTAS ASSOCIADAS A DATASETS
# ============================================================================
# Estrutura: cada pergunta está associada a um dataset específico
# Isso permite roteamento automático e escalabilidade

PREBUILT_QUESTIONS = {
    "vacinacao-covid": {
        "theme_color": "",
        "theme_name": "Vacinação COVID-19",
        "description": "Dados de vacinação contra COVID-19 no Brasil",
        "questions": [
            {
                "id": "vac-001",
                "theme": "Quantidade Total",
                "question": "Quantas vacinas foram aplicadas no Brasil?",
                "description": "Total de doses de vacina COVID-19 aplicadas",
                "category": "statistics"
            },
            {
                "id": "vac-002",
                "theme": "Por Estado",
                "question": "Quantas vacinas foram aplicadas em SP?",
                "description": "Total de doses aplicadas em São Paulo",
                "category": "regional"
            },
            {
                "id": "vac-003",
                "theme": "Por Estado",
                "question": "Qual estado recebeu mais vacinas?",
                "description": "Estado com maior número de doses aplicadas",
                "category": "comparison"
            },
            {
                "id": "vac-004",
                "theme": "Por Faixa Etária",
                "question": "Quantas vacinas foram aplicadas em crianças?",
                "description": "Doses aplicadas em pacientes menores de idade",
                "category": "demographics"
            },
            {
                "id": "vac-005",
                "theme": "Por Fabricante",
                "question": "Qual fabricante de vacina foi mais utilizado?",
                "description": "Fabricante com maior número de doses aplicadas",
                "category": "manufacturers"
            }
        ]
    },
    
    "dengue-2024": {
        "theme_color": "",
        "theme_name": "Dengue 2024",
        "description": "Casos de Dengue registrados em 2024",
        "questions": [
            {
                "id": "den-001",
                "theme": "Quantidade Total",
                "question": "Quantos casos de dengue foram registrados em 2024?",
                "description": "Total de casos de dengue confirmados",
                "category": "statistics"
            },
            {
                "id": "den-002",
                "theme": "Por Estado",
                "question": "Qual estado teve mais casos de dengue?",
                "description": "Estado com maior número de casos",
                "category": "regional"
            },
            {
                "id": "den-003",
                "theme": "Por Estado",
                "question": "Quantos casos de dengue foram registrados em RJ?",
                "description": "Total de casos no Rio de Janeiro",
                "category": "regional"
            },
            {
                "id": "den-004",
                "theme": "Gravidade",
                "question": "Quantos óbitos por dengue foram registrados?",
                "description": "Total de mortes confirmadas por dengue",
                "category": "severity"
            },
            {
                "id": "den-005",
                "theme": "Evolução",
                "question": "Como evoluiu o número de casos de dengue ao longo do ano?",
                "description": "Tendência temporal de novos casos",
                "category": "temporal"
            }
        ]
    },
    
    "influenza-2025": {
        "theme_color": "",
        "theme_name": "Influenza 2025",
        "description": "Casos de Influenza registrados em 2025",
        "questions": [
            {
                "id": "inf-001",
                "theme": "Quantidade Total",
                "question": "Quantos casos de influenza foram registrados em 2025?",
                "description": "Total de casos de influenza confirmados",
                "category": "statistics"
            },
            {
                "id": "inf-002",
                "theme": "Por Tipo",
                "question": "Qual tipo de influenza foi mais prevalente?",
                "description": "Tipo de influenza (A, B, C) com mais casos",
                "category": "classification"
            },
            {
                "id": "inf-003",
                "theme": "Por Região",
                "question": "Qual região teve mais casos de influenza?",
                "description": "Região com maior número de casos",
                "category": "regional"
            }
        ]
    }
}

# ============================================================================
# MODELOS PYDANTIC
# ============================================================================

class Question(BaseModel):
    """Modelo de uma pergunta pré-pronta"""
    id: str
    theme: str
    question: str
    description: str
    category: str


class DatasetInfo(BaseModel):
    """Informações sobre um dataset"""
    dataset_id: str
    theme_color: str
    theme_name: str
    description: str
    question_count: int
    questions: List[Question]


class QuestionsResponse(BaseModel):
    """Resposta com múltiplos datasets e perguntas"""
    total_datasets: int
    datasets: List[DatasetInfo]


class QuestionRecommendation(BaseModel):
    """Recomendação de dataset para uma pergunta"""
    dataset_id: str
    confidence: Optional[float] = None
    theme: str
    reason: Optional[str] = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/questions", response_model=QuestionsResponse, tags=["questions"])
def list_all_questions(
    dataset: Optional[str] = Query(None, description="Filtrar por dataset específico")
):
    """
    Lista todas as perguntas pré-prontas disponíveis, opcionalmente filtradas por dataset.
    
    **Exemplos:**
    
    - `GET /api/questions` - Lista perguntas de todos os datasets
    - `GET /api/questions?dataset=vacinacao-covid` - Apenas perguntas de vacinação
    - `GET /api/questions?dataset=dengue-2024` - Apenas perguntas de dengue
    
    **Proposito:**
    - Descoberta: Usuários veem exemplos de perguntas possíveis
    - Roteamento: Sistema sabe qual dataset processar
    - Escalabilidade: Novos datasets adicionados automaticamente
    
    **Resposta:**
    ```json
    {
      "total_datasets": 3,
      "datasets": [
        {
          "dataset_id": "vacinacao-covid",
          "theme_color": "",
          "theme_name": "Vacinação COVID-19",
          "description": "Dados de vacinação...",
          "question_count": 5,
          "questions": [...]
        }
      ]
    }
    ```
    """
    
    if dataset:
        # Filtrar por dataset específico
        if dataset not in PREBUILT_QUESTIONS:
            available = ", ".join(PREBUILT_QUESTIONS.keys())
            raise HTTPException(
                status_code=404,
                detail=f"Dataset '{dataset}' não encontrado. Disponíveis: {available}"
            )
        datasets_to_show = {dataset: PREBUILT_QUESTIONS[dataset]}
    else:
        # Mostrar todos
        datasets_to_show = PREBUILT_QUESTIONS
    
    # Montar resposta
    datasets_list = []
    for dataset_id, data in datasets_to_show.items():
        questions = [
            Question(**q) for q in data["questions"]
        ]
        dataset_info = DatasetInfo(
            dataset_id=dataset_id,
            theme_color=data["theme_color"],
            theme_name=data["theme_name"],
            description=data["description"],
            question_count=len(questions),
            questions=questions
        )
        datasets_list.append(dataset_info)
    
    return QuestionsResponse(
        total_datasets=len(datasets_list),
        datasets=datasets_list
    )


@router.get("/questions/{dataset_id}", tags=["questions"])
def get_dataset_questions(dataset_id: str):
    """
    Retorna todas as perguntas pré-prontas para um dataset específico.
    
    **Path Parameters:**
    - `dataset_id`: ID do dataset (ex: "vacinacao-covid", "dengue-2024")
    
    **Exemplos:**
    - `GET /api/questions/vacinacao-covid`
    - `GET /api/questions/dengue-2024`
    
    **Resposta:**
    ```json
    {
      "dataset_id": "vacinacao-covid",
      "theme_color": "",
      "theme_name": "Vacinação COVID-19",
      "description": "...",
      "question_count": 5,
      "questions": [...]
    }
    ```
    """
    
    if dataset_id not in PREBUILT_QUESTIONS:
        available = ", ".join(PREBUILT_QUESTIONS.keys())
        logger.warning(f"Dataset not found: {dataset_id}. Available: {available}")
        raise HTTPException(
            status_code=404,
            detail=f"Dataset '{dataset_id}' não encontrado. Disponíveis: {available}"
        )
    
    data = PREBUILT_QUESTIONS[dataset_id]
    questions = [Question(**q) for q in data["questions"]]
    
    return DatasetInfo(
        dataset_id=dataset_id,
        theme_color=data["theme_color"],
        theme_name=data["theme_name"],
        description=data["description"],
        question_count=len(questions),
        questions=questions
    )


@router.get("/questions/categories/{dataset_id}", tags=["questions"])
def get_categories_by_dataset(dataset_id: str):
    """
    Retorna categorias de perguntas disponíveis para um dataset.
    
    Útil para agrupar perguntas por tema/categoria.
    
    **Resposta:**
    ```json
    {
      "dataset_id": "vacinacao-covid",
      "categories": [
        {
          "name": "Quantidade Total",
          "icon": "📊",
          "question_count": 1,
          "questions": [...]
        }
      ]
    }
    ```
    """
    
    if dataset_id not in PREBUILT_QUESTIONS:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset '{dataset_id}' não encontrado"
        )
    
    data = PREBUILT_QUESTIONS[dataset_id]
    
    # Agrupar por tema
    themes_dict = {}
    for q in data["questions"]:
        theme = q["theme"]
        if theme not in themes_dict:
            themes_dict[theme] = []
        themes_dict[theme].append(Question(**q))
    
    categories = [
        {
            "name": theme,
            "question_count": len(questions),
            "questions": questions
        }
        for theme, questions in themes_dict.items()
    ]
    
    return {
        "dataset_id": dataset_id,
        "theme_color": data["theme_color"],
        "theme_name": data["theme_name"],
        "total_questions": len(data["questions"]),
        "categories": categories
    }


@router.post("/questions/detect-dataset", tags=["questions"])
def detect_dataset_for_question(question: str = Query(..., description="Pergunta em português")):
    """
    Detecta qual dataset seria mais apropriado para uma pergunta.
    
    Usa heurísticas simples de palavras-chave para rotear.
    
    **Query Parameters:**
    - `question`: Pergunta em português
    
    **Exemplos:**
    - `POST /api/questions/detect-dataset?question=Quantas vacinas em SP?`
      → Resultado: vacinacao-covid
    - `POST /api/questions/detect-dataset?question=Quantos casos de dengue?`
      → Resultado: dengue-2024
    
    **Resposta:**
    ```json
    {
      "detected_dataset": "vacinacao-covid",
      "confidence": 0.95,
      "keywords": ["vacina", "aplicadas", "SP"],
      "alternatives": [...]
    }
    ```
    """
    
    question_lower = question.lower()
    
    # Mapa de palavras-chave para datasets
    keywords_map = {
        "vacinacao-covid": [
            "vacina", "vacinação", "covid", "doses", "imunização", "aplicadas",
            "fabricante", "lote", "injeção", "imunivo", "pfizer", "astrazeneca"
        ],
        "dengue-2024": [
            "dengue", "aedes", "mosquito", "vetor", "epidemia", "surto",
            "sintomas", "febre", "casos", "óbitos", "confirmados", "arbovirose"
        ],
        "influenza-2025": [
            "influenza", "gripe", "h1n1", "h3n2", "iav", "tipo a", "tipo b",
            "tosse", "resfriado", "antiviral", "tamiflu"
        ]
    }
    
    # Calcular score para cada dataset
    scores = {}
    for dataset_id, keywords in keywords_map.items():
        score = sum(1 for kw in keywords if kw in question_lower)
        scores[dataset_id] = score
    
    # Detectar dataset com maior score
    best_dataset = max(scores, key=scores.get)
    best_score = scores[best_dataset]
    
    # Calcular confiança
    total_score = sum(scores.values())
    confidence = best_score / total_score if total_score > 0 else 0.0
    
    # Alternativas (datasets com score > 0)
    alternatives = [
        {"dataset": ds, "score": sc} 
        for ds, sc in scores.items() 
        if ds != best_dataset and sc > 0
    ]
    
    return {
        "question": question,
        "detected_dataset": best_dataset if best_score > 0 else None,
        "confidence": float(confidence),
        "score": int(best_score),
        "alternatives": sorted(alternatives, key=lambda x: x["score"], reverse=True),
        "message": "Dataset detectado" if best_score > 0 else "Dataset não detectado com confiança"
    }


# ============================================================================
# FUNÇÃO AUXILIAR: DESCOBERTA AUTOMÁTICA DE DATASETS
# ============================================================================

def discover_available_datasets() -> List[str]:
    """
    Descobre automaticamente datasets disponíveis verificando pastas.
    
    Útil para sincronizar perguntas pré-prontas com datasets reais.
    """
    try:
        metadata_path = Path(__file__).parent.parent / "metadata" / "datasets"
        if metadata_path.exists():
            return [d.name for d in metadata_path.iterdir() if d.is_dir()]
    except Exception as e:
        logger.warning(f"Erro ao descobrir datasets: {e}")
    
    return list(PREBUILT_QUESTIONS.keys())


@router.get("/datasets/available", tags=["datasets"])
def get_available_datasets():
    """
    Retorna lista de datasets disponíveis no sistema.
    
    Descoberta automática verificando pastas em metadata/datasets/.
    
    **Resposta:**
    ```json
    {
      "available_datasets": ["vacinacao-covid", "dengue-2024"],
      "count": 2,
      "with_prebuilt_questions": 2
    }
    ```
    """
    
    available = discover_available_datasets()
    with_questions = [d for d in available if d in PREBUILT_QUESTIONS]
    
    return {
        "available_datasets": available,
        "count": len(available),
        "with_prebuilt_questions": len(with_questions),
        "without_questions": [d for d in available if d not in PREBUILT_QUESTIONS]
    }
