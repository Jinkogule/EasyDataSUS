<div align="center">
<h1>EasyDataSUS</h1>
<p><strong>🚀 Sistema NLP para Consultas em Linguagem Natural sobre Dados de Saúde Pública</strong></p>

[![Status](https://img.shields.io/badge/STATUS-MVP%20|%20EM%20VALIDAÇÃO-brightgreen?style=for-the-badge)](https://github.com/Jinkogule/EasyDataSUS)
[![License](https://img.shields.io/github/license/Jinkogule/EasyDataSUS?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://www.python.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?style=for-the-badge&logo=docker)](https://www.docker.com)

[🇺🇸 English](./README.md)

</div>

---

### 💻 Sobre o Projeto

**EasyDataSUS** é um sistema inteligente de consultas que permite fazer perguntas em **português natural** sobre dados de saúde pública do Brasil (DataSUS). O sistema gera automaticamente consultas SQL, executa em um banco de dados analítico (ClickHouse) e retorna respostas interpretadas por modelos de linguagem locais (Ollama).

**Objetivo:** Tornar dados públicos de saúde acessíveis a qualquer pessoa, sem necessidade de conhecimento técnico em SQL.

### 📋 Documentação

- **[Setup Guia Completo](./docs/README_COMPLETO.md)** - Instruções passo-a-passo
- **[Arquitetura do Sistema](./docs/ARCHITECTURE.md)** - Diagramas e fluxos
- **[Estrutura de Arquivos](./docs/ESTRUCTURA_ARQUIVOS_SISTEMA.md)** - Papel de cada componente
- **[Multi-Dataset](./docs/ESCALABILIDADE_MULTI_TEMAS.md)** - Como adicionar novos temas

### 🧑‍💻 Desenvolvimento

- **[Código Fonte](https://github.com/Jinkogule/EasyDataSUS)**
- **[Rastreamento de Issues](https://github.com/Jinkogule/EasyDataSUS/issues)**

### 🛠 Tecnologias

#### **Backend** (Python + FastAPI)
- **[Python 3.10+](https://www.python.org)**
- **[FastAPI 0.104.1](https://fastapi.tiangolo.com/)**

#### **Banco de Dados**
- **[ClickHouse 24.3.3](https://clickhouse.com/)** - OLAP para TimeSeries

#### **Modelos de Linguagem**
- **[Ollama 0.2.0](https://ollama.ai/)** - Inferência Local
  - DeepSeek Coder (SQL)
  - Mistral (Rápido)
  - Neural Chat (Português)
  - Orca Mini (Leve)

#### **Infraestrutura**
- **[Docker & Docker Compose](https://www.docker.com/)** - Containerização

### 🎯 Quick Start

#### 1. **Clonar & Setup**
```bash
git clone https://github.com/Jinkogule/EasyDataSUS.git
cd EasyDataSUS
docker-compose up -d
```

#### 2. **Ambiente Python**
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
```

#### 3. **Baixar Modelo**
```bash
docker exec easydatasus-ollama ollama pull deepseek-coder:6.7b-base-q4_K_M
```

#### 4. **Iniciar Sistema**
```bash
python main.py
```

#### 5. **Fazer Pergunta**
```bash
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Quantas vacinas foram aplicadas em SP?"}'
```

**Resposta:**
```json
{
  "sql": "SELECT COUNT(*) FROM vacinacao WHERE paciente_endereco_uf = 'SP'",
  "insight": "Em São Paulo foram aplicadas 824.915 doses de vacina."
}
```

### 📊 Datasets Suportados

| Dataset | Status | Registros |
|---------|--------|-----------|
| 🩺 Vacinação COVID-19 | ✅ Ativo | 390K+ |
| 🦟 Dengue 2024 | 🏗️ Estrutura Pronta | 0 |
| 🤒 Influenza 2025 | 🏗️ Estrutura Pronta | 0 |

### ✨ Recursos Principais

- ✅ **Roteamento Automático** - Detecta dataset pela pergunta
- ✅ **Multi-Modelo LLM** - Compare diferentes modelos
- ✅ **SQL Seguro** - Validação contra injeção
- ✅ **Retry Automático** - 3x tentativas com backoff
- ✅ **Upload de Dados** - API para adicionar novos datasets
- ✅ **Arquitetura Escalável** - Suporte a múltiplos temas

### 🔄 Roadmap

- 🚀 Frontend Web (React)
- 📊 Dashboard com Gráficos
- 🔐 Autenticação
- 🧪 Testes Automatizados
- 📈 Análises Multi-Dataset

### ✒️ Autor

**Lucas Pimenta**
- [GitHub](https://github.com/Jinkogule)
- [LinkedIn](https://linkedin.com/in/lucas-pimenta)

### 📝 Licença

MIT License - Use livremente em projetos comerciais

---

<div align="center">

**Feito com ❤️ para tornar dados públicos de saúde acessíveis a todos!**

[↑ Voltar ao Topo](#easydatasus)

</div>