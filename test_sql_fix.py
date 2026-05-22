#!/usr/bin/env python3
"""
Test script to validate SQL generation improvements without depending on slow Ollama
"""
import sys
sys.path.insert(0, '.')

from backend.services.sql_service import fallback_sql, validate_sql_syntax

def test_count_queries():
    """Test that 'quantas/quantos' questions generate COUNT(*) SQL"""
    print("=" * 60)
    print("TESTE: Validação de Queries de Contagem")
    print("=" * 60)
    
    test_cases = [
        {
            "question": "Quantas vacinas foram aplicadas em SP?",
            "dataset": "covid-19-vacinacao",
            "expected_pattern": "COUNT(*)",
            "should_not_contain": "SELECT *"
        },
        {
            "question": "Quantos leitos de UTI existem no Brasil?",
            "dataset": "leitos",
            "expected_pattern": "COUNT(*)",
            "should_not_contain": "SELECT *"
        },
        {
            "question": "Qual é o total de casos de SRAG?",
            "dataset": "surtos-srag",
            "expected_pattern": "COUNT(*)",
            "should_not_contain": "SELECT *"
        },
    ]
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n[Teste {i}] {test['question']}")
        print(f"Dataset: {test['dataset']}")
        
        sql = fallback_sql(test['question'], test['dataset'])
        print(f"SQL Gerado: {sql}")
        
        # Validar
        if test['expected_pattern'] in sql:
            print(f"✅ PASS: Contém '{test['expected_pattern']}'")
        else:
            print(f"❌ FAIL: Não contém '{test['expected_pattern']}'")
            failed += 1
            continue
            
        if test['should_not_contain'] not in sql:
            print(f"✅ PASS: Não contém '{test['should_not_contain']}'")
        else:
            print(f"❌ FAIL: Contém '{test['should_not_contain']}' (não deveria)")
            failed += 1
            continue
        
        passed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTADO: {passed} passou(aram), {failed} falhou(aram)")
    print("=" * 60)
    
    return failed == 0

def test_sql_validation():
    """Test that SQL validation rejects SELECT * for 'quantas' questions"""
    print("\n" + "=" * 60)
    print("TESTE: Validação de SQL Rejection")
    print("=" * 60)
    
    test_cases = [
        {
            "sql": "SELECT * FROM vacinacao WHERE paciente_endereco_uf = 'SP' LIMIT 10000",
            "question": "Quantas vacinas em SP?",
            "dataset": "covid-19-vacinacao",
            "should_fail": True,
            "reason": "SELECT * should be rejected for 'quantas' questions"
        },
        {
            "sql": "SELECT COUNT(*) FROM vacinacao WHERE paciente_endereco_uf = 'SP'",
            "question": "Quantas vacinas em SP?",
            "dataset": "covid-19-vacinacao",
            "should_fail": False,
            "reason": "COUNT(*) should be accepted"
        },
        {
            "sql": "SELECT * FROM vacinacao LIMIT 100",
            "question": "Quais pessoas foram vacinadas?",
            "dataset": "covid-19-vacinacao",
            "should_fail": False,
            "reason": "SELECT * is ok for 'quais' questions (not counting)"
        },
    ]
    
    passed = 0
    failed = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n[Teste {i}] {test['question']}")
        print(f"SQL: {test['sql'][:60]}...")
        print(f"Razão: {test['reason']}")
        
        is_valid = validate_sql_syntax(test['sql'], test['dataset'], test['question'])
        
        if test['should_fail']:
            if not is_valid:
                print(f"✅ PASS: SQL corretamente rejeitado")
                passed += 1
            else:
                print(f"❌ FAIL: SQL deveria ter sido rejeitado mas foi aceito")
                failed += 1
        else:
            if is_valid:
                print(f"✅ PASS: SQL corretamente aceito")
                passed += 1
            else:
                print(f"❌ FAIL: SQL deveria ter sido aceito mas foi rejeitado")
                failed += 1
    
    print("\n" + "=" * 60)
    print(f"RESULTADO: {passed} passou(aram), {failed} falhou(aram)")
    print("=" * 60)
    
    return failed == 0

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("SUITE DE TESTES: SQL Generation Fix")
    print("=" * 60)
    
    test1_pass = test_count_queries()
    test2_pass = test_sql_validation()
    
    print("\n" + "=" * 60)
    if test1_pass and test2_pass:
        print("✅ TODOS OS TESTES PASSARAM!")
    else:
        print("❌ ALGUNS TESTES FALHARAM")
    print("=" * 60)
