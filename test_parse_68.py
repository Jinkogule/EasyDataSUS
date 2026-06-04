#!/usr/bin/env python3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

# Import do script de teste
import importlib.util
spec = importlib.util.spec_from_file_location("test_68", Path(__file__).parent / "test_68_questoes_seidig.py")
test_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(test_module)

# Parse e exibir
try:
    questions = test_module.parse_68_questions()
    total = sum(len(q) for q in questions.values())
    print(f"✅ Total: {total} questões\n")
    
    for dataset, qs in sorted(questions.items()):
        print(f"  {dataset}: {len(qs)} questões")
        if qs:
            print(f"    - Q{qs[0]['id']}: {qs[0]['question'][:60]}...")
    
    print(f"\n✅ Parsing bem-sucedido!")
except Exception as e:
    print(f"❌ Erro: {e}")
    import traceback
    traceback.print_exc()
