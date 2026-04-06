<div align="center">
<h1>EasyDataSUS</h1>
<p><strong>🚀 NLP System for Natural Language Queries on Public Health Data</strong></p>

[![Status](https://img.shields.io/badge/STATUS-MVP%20|%20IN%20VALIDATION-brightgreen?style=for-the-badge)](https://github.com/Jinkogule/EasyDataSUS)
[![License](https://img.shields.io/github/license/Jinkogule/EasyDataSUS?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python)](https://www.python.org)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue?style=for-the-badge&logo=docker)](https://www.docker.com)

[🇵🇧 Português](./README.pt-BR.md)

</div>

---

### 💻 About the Project

**EasyDataSUS** is an intelligent query system that allows you to ask questions in **natural Portuguese** about public health data from Brazil (DataSUS). The system automatically generates SQL queries, executes them in an analytical database (ClickHouse), and returns answers interpreted by local language models (Ollama).

**Goal:** Make public health data accessible to anyone, without the need for technical SQL knowledge.

### 📋 Documentation

- **[Complete Setup Guide](./docs/README_COMPLETO.md)** - Step-by-step instructions
- **[System Architecture](./docs/ARCHITECTURE.md)** - Diagrams and flows
- **[File Structure](./docs/ESTRUCTURA_ARQUIVOS_SISTEMA.md)** - Role of each component
- **[Multi-Dataset](./docs/ESCALABILIDADE_MULTI_TEMAS.md)** - How to add new themes

### 🧑‍💻 Development

- **[Source Code](https://github.com/Jinkogule/EasyDataSUS)**
- **[Issue Tracking](https://github.com/Jinkogule/EasyDataSUS/issues)**

### 🛠 Technologies

#### **Backend** (Python + FastAPI)
- **[Python 3.10+](https://www.python.org)**
- **[FastAPI 0.104.1](https://fastapi.tiangolo.com/)**

#### **Database**
- **[ClickHouse 24.3.3](https://clickhouse.com/)** - OLAP for TimeSeries

#### **Language Models**
- **[Ollama 0.2.0](https://ollama.ai/)** - Local Inference
  - DeepSeek Coder (SQL)
  - Mistral (Fast)
  - Neural Chat (Portuguese)
  - Orca Mini (Lightweight)

#### **Infrastructure**
- **[Docker & Docker Compose](https://www.docker.com/)** - Containerization

### 🎯 Quick Start

#### 1. **Clone & Setup**
```bash
git clone https://github.com/Jinkogule/EasyDataSUS.git
cd EasyDataSUS
docker-compose up -d
```

#### 2. **Python Environment**
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
pip install -r requirements.txt
```

#### 3. **Download Model**
```bash
docker exec easydatasus-ollama ollama pull deepseek-coder:6.7b-base-q4_K_M
```

#### 4. **Start System**
```bash
python main.py
```

#### 5. **Ask Question**
```bash
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many vaccines were applied in SP?"}'
```

**Response:**
```json
{
  "sql": "SELECT COUNT(*) FROM vacinacao WHERE paciente_endereco_uf = 'SP'",
  "insight": "In São Paulo 824,915 vaccine doses were applied."
}
```

### 📊 Supported Datasets

| Dataset | Status | Records |
|---------|--------|---------|
| 🩺 COVID-19 Vaccination | ✅ Active | 390K+ |
| 🦟 Dengue 2024 | 🏗️ Structure Ready | 0 |
| 🤒 Influenza 2025 | 🏗️ Structure Ready | 0 |

### ✨ Main Features

- ✅ **Automatic Routing** - Detects dataset from question
- ✅ **Multi-Model LLM** - Compare different models
- ✅ **Safe SQL** - Injection validation
- ✅ **Auto Retry** - 3x attempts with backoff
- ✅ **Data Upload** - API to add new datasets
- ✅ **Scalable Architecture** - Support for multiple themes

### 🔄 Roadmap

- 🚀 Web Frontend (React)
- 📊 Dashboard with Charts
- 🔐 Authentication
- 🧪 Automated Tests
- 📈 Multi-Dataset Analysis

### ✒️ Author

**Lucas Pimenta**
- [GitHub](https://github.com/Jinkogule)
- [LinkedIn](https://linkedin.com/in/lucas-pimenta)

### 📝 License

MIT License - Use freely in commercial projects

---

<div align="center">

**Made with ❤️ to make public health data accessible to everyone!**

[↑ Back to Top](#easydatasus)

</div>
