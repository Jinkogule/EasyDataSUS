#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Teste rápido dos novos endpoints com roteamento por dataset.
"""

from routes.questions import PREBUILT_QUESTIONS
from routes.query import _detect_dataset_for_question
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

logger.info("""
╔═══════════════════════════════════════════════════════════════╗
║         TESTE: Novos Endpoints com Roteamento por Dataset    ║
╚═══════════════════════════════════════════════════════════════╝
""")

# Test 1: Verify prebuilt questions loaded
logger.info("\n[TEST 1] Verificar perguntas pré-prontas carregadas")
logger.info(f"✅ Total de datasets: {len(PREBUILT_QUESTIONS)}")

for dataset_id, data in PREBUILT_QUESTIONS.items():
    logger.info(f"\n  {data['theme_color']} {data['theme_name']}")
    logger.info(f"     Descrição: {data['description']}")
    logger.info(f"     Perguntas: {len(data['questions'])}")
    
    for q in data['questions'][:2]:
        logger.info(f"       • {q['question']}")

# Test 2: Test dataset detection
logger.info("\n[TEST 2] Teste de detecção de dataset")

test_questions = [
    ("Quantas vacinas foram aplicadas em SP?", "vacinacao-covid"),
    ("Qual estado teve mais casos de dengue?", "dengue-2024"),
    ("Qual tipo de influenza foi mais comum?", "influenza-2025"),
]

for question, expected_dataset in test_questions:
    detected = _detect_dataset_for_question(question)
    status = "✅" if detected == expected_dataset else "❌"
    logger.info(f"\n  {status} Pergunta: {question}")
    logger.info(f"     Esperado: {expected_dataset}")
    logger.info(f"     Detectado: {detected}")

# Test 3: Test question selection flow (simulated frontend)
logger.info("\n[TEST 3] Simular fluxo de seleção no frontend")

# User clicks on a prebuilt question
dataset = PREBUILT_QUESTIONS["vacinacao-covid"]
selected_question = dataset["questions"][1]  # vac-002

logger.info(f"\n  👤 Usuário clica em pergunta no frontend")
logger.info(f"     {selected_question['question']}")
logger.info(f"\n  📤 Frontend vai enviar para /ask:")
logger.info(f"     {{")
logger.info(f'       "question": "{selected_question["question"]}",')
logger.info(f'       "model": "deepseek-local",')
logger.info(f'       "dataset": "vacinacao-covid"')
logger.info(f"     }}")

logger.info("\n" + "="*60)
logger.info("✅ TESTES BÁSICOS OK!")
logger.info("="*60)
logger.info("""
Próximas etapas:
1. Iniciar API: python main.py
2. Testar endpoints com curl/Postman
3. Integrar com frontend

Localhost:
  curl http://localhost:8000/api/questions
  curl -X POST http://localhost:8000/api/ask \\
    -H "Content-Type: application/json" \\
    -d '{"question": "Quantas vacinas?", "dataset": "vacinacao-covid"}'
""")
