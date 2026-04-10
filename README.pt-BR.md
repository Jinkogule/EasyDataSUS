<div align="center">
<h1>EasyDataSUS</h1>
<p><strong>🚀 Sistema NLP para Consultas em Linguagem Natural sobre Dados de Saúde Pública</strong></p>

[![Release](https://img.shields.io/github/v/release/Jinkogule/EasyDataSUS?style=for-the-badge)](https://github.com/Jinkogule/EasyDataSUS/releases)
[![License](https://img.shields.io/github/license/Jinkogule/EasyDataSUS?style=for-the-badge)](LICENSE)
![Status](https://img.shields.io/badge/STATUS-MVP%20|%20EM%20VALIDAÇÃO-brightgreen?style=for-the-badge)
</div>

<p align="center">
  <a href="#-sobre-o-projeto">Sobre</a> •
  <a href="#-documentação">Documentação</a> •
  <a href="#-desenvolvimento">Desenvolvimento</a> •
  <a href="#-tecnologias">Tecnologias</a> •
  <a href="#-executar-o-projeto-localmente">Executar localmente</a> •
  <a href="#-autores">Autores</a> •
  <a href="#-licença">Licença</a>
  <br>
  <a href="./README.md">English</a> •
  <a href="./README.pt-BR.md">Português (BR)</a>
</p>

---

## 💻 Sobre o Projeto

**EasyDataSUS** é um sistema inteligente de consultas desenvolvido para democratizar o acesso a dados de saúde pública do Brasil (DataSUS). O sistema permite que usuários façam perguntas em **português natural** sobre dados de saúde, gerando automaticamente consultas SQL, executando-as em um banco de dados analítico (ClickHouse) e retornando respostas inteligentes interpretadas por modelos de linguagem locais (Ollama).

O projeto implementa conceitos como desenvolvimento de APIs com FastAPI, suporte a arquitetura multi-dataset, processamento de linguagem natural e design de sistemas escaláveis. O sistema suporta múltiplos temas de dados de saúde (vacinação, dengue, influenza) e permite integração perfeita de novos datasets através de um sistema de configuração centralizado.

**Objetivo**: Tornar dados públicos de saúde acessíveis a qualquer pessoa sem exigir conhecimento técnico em SQL, democratizando o acesso a informações críticas de saúde.

## 📋 Documentação

-   **[Wiki](https://github.com/Jinkogule/EasyDataSUS/wiki)**

## 🧑‍💻 Desenvolvimento

-   **[Código Fonte](https://github.com/Jinkogule/EasyDataSUS)**
-   **[Rastreamento de Issues](https://github.com/Jinkogule/EasyDataSUS/issues)**

## 🛠 Tecnologias

### **Backend (API)**

-   **[Python 3.10+](https://www.python.org)**
-   **[FastAPI 0.104.1](https://fastapi.tiangolo.com/)**

### **Banco de Dados**

-   **[ClickHouse 24.3.3](https://clickhouse.com/)** - Banco de Dados OLAP TimeSeries

### **Modelos de Linguagem**

-   **[Ollama 0.2.0](https://ollama.ai/)** - Inferência Local de LLM
    - DeepSeek Coder 6.7B (geração de SQL)
    - Mistral 7B (inferência rápida)
    - Neural Chat (otimizado para português)
    - Orca Mini (leve)

### **Infraestrutura**

-   **[Docker & Docker Compose](https://www.docker.com/)** - Containerização e orquestração

## ⚙ Executar o Projeto Localmente

### **Pré-requisitos**

Antes de começar, certifique-se de:

-   Instalar **[Git](https://git-scm.com/)**.
-   Instalar **[Docker Desktop](https://www.docker.com/products/docker-desktop/)** (inclui Docker Compose).
-   Instalar **[Python 3.10+](https://www.python.org/)**.
-   Ter **15 GB de espaço livre em disco** (para modelos LLM + banco de dados).
-   Verificar as instalações:
    ```bash
    docker --version
    docker-compose --version
    python --version
    ```

### **Rodando a Aplicação**

1. **Clone este repositório**
```bash
git clone https://github.com/Jinkogule/EasyDataSUS.git
cd EasyDataSUS
```

2. **Inicie os containers Docker**
```bash
docker-compose up -d
```

Verificar status:
```bash
docker-compose ps
```

3. **Configure o ambiente Python**
```bash
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
```

Crie o arquivo `.env`:
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

4. **Baixe o modelo LLM**
```bash
docker exec easydatasus-ollama ollama pull deepseek-coder:6.7b-base-q4_K_M
```

Warmup (OBRIGATÓRIO):
```bash
docker exec easydatasus-ollama ollama run deepseek-coder:6.7b-base-q4_K_M "Hello"
```

5. **Carregue dados e inicie**
```bash
python etl/load_csv.py
python main.py
```

✅ Sistema pronto em: `http://localhost:8000/docs`

6. **Teste o sistema**
```bash
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question": "Quantas vacinas foram aplicadas em SP?"}'
```

Resposta esperada:
```json
{
  "sql": "SELECT COUNT(*) FROM vacinacao WHERE paciente_endereco_uf = 'SP'",
  "insight": "Em São Paulo foram aplicadas 824.915 doses de vacina."
}
```

## ✒ Autores

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

## 📝 Licença

Este projeto está sob a licença **[MIT](./LICENSE)**.