<div align="center">
<h1>EasyDataSUS</h1>
<p><strong>🚀 NLP System for Natural Language Queries on Public Health Data</strong></p>

[![Release](https://img.shields.io/github/v/release/Jinkogule/EasyDataSUS?style=for-the-badge)](https://github.com/Jinkogule/EasyDataSUS/releases)
[![License](https://img.shields.io/github/license/Jinkogule/EasyDataSUS?style=for-the-badge)](LICENSE)
![Status](https://img.shields.io/badge/STATUS-MVP%20|%20IN%20VALIDATION-brightgreen?style=for-the-badge)
</div>

<p align="center">
  <a href="#-about-the-project">About</a> •
  <a href="#-documentation">Documentation</a> •
  <a href="#-development">Development</a> •
  <a href="#-technologies">Technologies</a> •
  <a href="#-run-the-project-locally">Run the project locally</a> •
  <a href="#-authors">Authors</a> •
  <a href="#-license">License</a>
  <br>
  <a href="./README.pt-BR.md">Português (BR)</a> •
  <a href="./README.md">English</a>
</p>

---

## 💻 About the Project

**EasyDataSUS** is a query system developed to facilitate access to and utilization of public health data in Brazil, especially for managers and professionals who do not have technical training in data analysis.

The system allows questions to be asked in natural language, automatically translating them into SQL queries, executing them against an analytical database, and presenting the results in an interpreted format. This reduces the need for technical knowledge about database structures or query languages. The solution was designed with a scalable architecture and support for multiple health-related datasets.

This project was developed to evaluate a tool that reduces technical barriers to the use of public health data, enabling managers, researchers, and citizens to obtain relevant information from DataSUS data. Additionally, the project investigates the impact of different language models and metadata structures on the quality and accuracy of generated responses.

## 📋 Documentation

-   **[Complete Setup Guide](./docs/README_COMPLETO.md)** - Step-by-step installation and configuration
-   **[System Architecture](./docs/ARCHITECTURE.md)** - Technical design and system flows
-   **[File Structure](./docs/ESTRUCTURA_ARQUIVOS_SISTEMA.md)** - Detailed component documentation
-   **[Multi-Dataset Setup](./docs/ESCALABILIDADE_MULTI_TEMAS.md)** - How to add new health themes

## 🧑‍💻 Development

-   **[Source Code](https://github.com/Jinkogule/EasyDataSUS)**
-   **[Issue Tracking](https://github.com/Jinkogule/EasyDataSUS/issues)**

## 🛠 Technologies

### **Backend (API)**

-   **[Python 3.10+](https://www.python.org)**
-   **[FastAPI 0.104.1](https://fastapi.tiangolo.com/)**

### **Database**

-   **[ClickHouse 24.3.3](https://clickhouse.com/)** - OLAP TimeSeries Database

### **Language Models**

-   **[Ollama 0.2.0](https://ollama.ai/)** - Local LLM Inference
    - DeepSeek Coder 6.7B (SQL generation)
    - Mistral 7B (Fast inference)
    - Neural Chat (Portuguese optimized)
    - Orca Mini (Lightweight)

### **Infrastructure**

-   **[Docker & Docker Compose](https://www.docker.com/)** - Containerization and orchestration

## ⚙ Run the Project Locally

### **Prerequisites**

Before you begin, make sure to:

-   Install **[Git](https://git-scm.com/)**.
-   Install **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** (includes Docker Compose).
-   Install **[Python 3.10+](https://www.python.org/)**.
-   Have **15 GB of free disk space** (for LLM models + database).
-   Verify installations:
    ```bash
    docker --version
    docker-compose --version
    python --version
    ```

### **Running the Application**

1. **Clone this repository**
```bash
git clone https://github.com/Jinkogule/EasyDataSUS.git
cd EasyDataSUS
```

2. **Start Docker containers**
```bash
docker-compose up -d
```

Verify status:
```bash
docker-compose ps
```

3. **Setup Python environment**
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
```

Create `.env`:
```env
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
CLICKHOUSE_USER=admin
CLICKHOUSE_PASSWORD=admin
CLICKHOUSE_DATABASE=default

OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=deepseek-coder:6.7b-base-q4_K_M
OLLAMA_TIMEOUT=180

FASTAPI_HOST=localhost
FASTAPI_PORT=8000
```

4. **Download LLM model**
```bash
docker exec easydatasus-ollama ollama pull deepseek-coder:6.7b-base-q4_K_M
```

Warmup (REQUIRED):
```bash
docker exec easydatasus-ollama ollama run deepseek-coder:6.7b-base-q4_K_M "Hello"
```

5. **Load dataset and start**
```bash
python etl/load_csv.py
python main.py
```

✅ System ready at: `http://localhost:8000`

6. **Test the system**
```bash
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many vaccines were applied in SP?"}'
```

Expected response:
```json
{
  "sql": "SELECT COUNT(*) FROM vacinacao WHERE paciente_endereco_uf = 'SP'",
  "insight": "In São Paulo, 824,915 vaccine doses were applied."
}
```

---

## ✒ Authors

<table>
  <tr>
    <td align="center">
      Lucas Pimenta
      <br>
      <a href="https://github.com/Jinkogule">
        <img src="https://avatars.githubusercontent.com/u/52849575?v=4" width="100px;" alt="Lucas Pimenta"/>
      </a>
      <br>
      <a href="https://github.com/Jinkogule">
        <img src="https://img.shields.io/badge/-Github-black?style=flat-square&logo=Github&logoColor=white">
      </a>
    </td>
  </tr>
</table>

## 📝 License

This project is licensed under the **[MIT](./LICENSE)** license.