#!/usr/bin/env python3
import json
import requests

payload = {
    'question': 'Quantas vacinas foram aplicadas em SP?',
    'model': 'deepseek-local',
    'dataset': 'covid-19-vacinacao'
}

print("Enviando request para /api/ask...")
response = requests.post('http://localhost:8000/api/ask', json=payload)
print(f"Status: {response.status_code}")

result = response.json()
print(f"\nSQL gerado: {result.get('sql')}")
print(f"Sucesso: {result.get('success')}")

if result.get('data'):
    data = result.get('data')
    if isinstance(data, list):
        print(f"Número de linhas: {len(data)}")
        if len(data) > 0:
            print(f"Primeira linha: {data[0]}")
    else:
        print(f"Dados: {data}")

print(f"\nInsight: {result.get('insight')}")
