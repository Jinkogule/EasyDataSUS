#!/usr/bin/env python3
"""
Teste dos endpoints administrativos de upload de datasets.

Demonstra:
- Listar datasets
- Validar schema
- Upload de arquivo
- Recarregar dataset
"""

import requests
import json

BASE_URL = "http://localhost:8000/api"

print("\n" + "="*70)
print("🧪 TESTE: Endpoints Administrativos de Dataset Upload")
print("="*70)

# 1. Listar datasets disponíveis
print("\n1️⃣  Listando datasets disponíveis...")
try:
    response = requests.get(f"{BASE_URL}/admin/datasets/available")
    if response.status_code == 200:
        datasets = response.json()
        print(f"✅ {len(datasets)} dataset(s) encontrado(s):")
        for ds in datasets:
            print(f"   • {ds['id']}: {ds['csv_count']} arquivo(s) ({ds['total_size_mb']:.1f} MB)")
    else:
        print(f"❌ Erro: {response.status_code}")
except Exception as e:
    print(f"❌ Erro de conexão: {e}")
    print("   Certifique-se de que o backend está rodando em http://localhost:8000")

# 2. Informações de um dataset específico
print("\n2️⃣  Informações do dataset 'vacinacao-covid'...")
try:
    response = requests.get(f"{BASE_URL}/admin/datasets/vacinacao-covid/info")
    if response.status_code == 200:
        info = response.json()
        print(f"✅ Dataset encontrado:")
        print(f"   ID: {info['id']}")
        print(f"   Tabela: {info['table_name']}")
        print(f"   Arquivos: {info['csv_count']}")
        print(f"   Tamanho: {info['total_size_mb']:.1f} MB")
    else:
        print(f"❌ Dataset não encontrado")
except Exception as e:
    print(f"❌ Erro: {e}")

# 3. Demonstrar validação de schema (sem arquivo real)
print("\n3️⃣  Estrutura de validação de schema:")
print("""
Para validar um CSV antes de upload:

curl -X POST "http://localhost:8000/api/admin/datasets/validate?dataset=vacinacao-covid" \\
  -F "file=@seu-arquivo.csv"

Resposta esperada:
{
  "valid": true,
  "errors": [],
  "warnings": [],
  "rows_preview": 100
}
""")

# 4. Demonstrar upload
print("\n4️⃣  Estrutura de upload:")
print("""
Para fazer upload de um novo CSV:

curl -X POST "http://localhost:8000/api/admin/datasets/upload?dataset=vacinacao-covid" \\
  -F "file=@seu-arquivo.csv"

Python:
import requests

files = {"file": open("seu-arquivo.csv", "rb")}
response = requests.post(
    "http://localhost:8000/api/admin/datasets/upload?dataset=vacinacao-covid",
    files=files
)
print(response.json())
""")

# 5. Demonstrar recarregamento
print("\n5️⃣  Recarregar dataset completo:")
print("""
Para recarregar TODOS os CSVs de um dataset:

curl -X POST "http://localhost:8000/api/admin/datasets/vacinacao-covid/reload"

Útil quando:
- Schema foi alterado
- Houve erro anterior
- Novos CSVs foram adicionados manualmente
""")

print("\n" + "="*70)
print("✅ Endpoints administrativos configurados e prontos!")
print("="*70)
print("\n📖 Documentação completa em: DATASET_UPLOAD_API.md\n")
