#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Exemplo de teste do novo fluxo com roteamento por dataset.

Simula como um frontend integraria com os endpoints.
"""

import requests
import json
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000"

def test_flow():
    """
    Testa o fluxo completo:
    1. Listar perguntas disponíveis
    2. Usuário seleciona uma
    3. Envia para /ask com dataset
    """
    
    logger.info("\n" + "="*80)
    logger.info("TESTE: Fluxo Completo com Roteamento por Dataset")
    logger.info("="*80)
    
    # PASSO 1: Listar todas as perguntas disponíveis
    logger.info("\n[1️⃣  PASSO 1] Listar perguntas pré-prontas...")
    try:
        response = requests.get(f"{BASE_URL}/api/questions")
        questions_data = response.json()
        
        logger.info(f"✅ Total de datasets: {questions_data['total_datasets']}")
        
        for dataset_info in questions_data['datasets']:
            logger.info(f"\n  🎯 Dataset: {dataset_info['theme_color']} {dataset_info['theme_name']}")
            logger.info(f"     Descrição: {dataset_info['description']}")
            logger.info(f"     Perguntas disponíveis: {dataset_info['question_count']}")
            
            for q in dataset_info['questions'][:2]:  # Mostrar 2 primeiras
                logger.info(f"       • {q['question']}")
    
    except Exception as e:
        logger.error(f"❌ Erro ao listar perguntas: {e}")
        return
    
    # PASSO 2: Simular usuário selecionando uma pergunta
    logger.info("\n[2️⃣  PASSO 2] Usuário seleciona uma pergunta no frontend...")
    
    # Pergunta pré-pronta do dataset vacinacao-covid
    selected_question = {
        "id": "vac-002",
        "question": "Quantas vacinas foram aplicadas em SP?",
        "dataset": "vacinacao-covid",
        "theme": "Por Estado"
    }
    
    logger.info(f"  ✓ Pergunta selecionada: {selected_question['question']}")
    logger.info(f"  ✓ Dataset associado: {selected_question['dataset']}")
    
    # PASSO 3: Frontend envia para /ask
    logger.info("\n[3️⃣  PASSO 3] Frontend envia para /api/ask...")
    
    payload = {
        "question": selected_question['question'],
        "model": "deepseek-local",
        "dataset": selected_question['dataset']  # ← Dataset vem da pergunta selecionada!
    }
    
    logger.info(f"  Payload enviado: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/ask",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"\n✅ Resposta recebida:")
            logger.info(f"  📊 Dataset usado: {result.get('dataset')}")
            logger.info(f"  🔍 SQL gerado: {result.get('sql')}")
            logger.info(f"  💬 Interpretação: {result.get('insight')}")
            logger.info(f"  ✓ Sucesso: {result.get('success')}")
        else:
            logger.error(f"❌ Erro HTTP {response.status_code}")
            logger.error(response.text)
    
    except Exception as e:
        logger.error(f"❌ Erro ao chamar /ask: {e}")
        return
    
    # PASSO 4: Testar pergunta customizada (detecção automática)
    logger.info("\n[4️⃣  PASSO 4] Teste com pergunta customizada (detecção automática)...")
    
    # Pergunta que não é pré-pronta, mas relacionada a dengue
    custom_question = {
        "question": "Qual estado teve mais casos de dengue em 2024?",
        "model": "deepseek-local"
        # Sem dataset - será detectado automaticamente!
    }
    
    logger.info(f"  Pergunta: {custom_question['question']}")
    logger.info(f"  Dataset: (será detectado automaticamente)")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/ask",
            json=custom_question,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"\n✅ Resposta recebida:")
            logger.info(f"  📊 Dataset detectado: {result.get('dataset')}")
            logger.info(f"  💬 Interpretação: {result.get('insight')}")
        else:
            logger.error(f"❌ Erro HTTP {response.status_code}")
    
    except Exception as e:
        logger.error(f"❌ Erro ao chamar /ask: {e}")
    
    # PASSO 5: Testar detecção de dataset
    logger.info("\n[5️⃣  PASSO 5] Teste endpoint de detecção de dataset...")
    
    test_questions = [
        "Quantas vacinas em SP?",
        "Quantos casos de dengue?",
        "Qual a influenza mais comum?"
    ]
    
    for question in test_questions:
        try:
            response = requests.post(
                f"{BASE_URL}/api/questions/detect-dataset",
                params={"question": question},
                timeout=10
            )
            
            if response.status_code == 200:
                detection = response.json()
                logger.info(f"\n  Pergunta: {question}")
                logger.info(f"  📊 Dataset detectado: {detection.get('detected_dataset')}")
                logger.info(f"  📈 Confiança: {detection.get('confidence', 0):.2%}")
            else:
                logger.warning(f"  ⚠️  Status {response.status_code}")
        
        except Exception as e:
            logger.error(f"  ❌ Erro: {e}")


if __name__ == "__main__":
    logger.info("""
╔════════════════════════════════════════════════════════════════════════════╗
║              TESTE: Fluxo de Frontend com Roteamento por Dataset           ║
║                                                                            ║
║  Este script simula como um frontend (React, Vue, etc) integraria com      ║
║  os novos endpoints de roteamento por dataset                             ║
╚════════════════════════════════════════════════════════════════════════════╝
    """)
    
    test_flow()
    
    logger.info("\n" + "="*80)
    logger.info("✅ TESTES COMPLETADOS")
    logger.info("="*80)
