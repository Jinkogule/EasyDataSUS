import logging
import os
from fastapi import FastAPI
from routes import query, questions, admin
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Carregar .env
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=os.getenv("FASTAPI_LOG_LEVEL", "info").upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Criar app
app = FastAPI(
    title="EasyDataSUS",
    description="Sistema de consultas em linguagem natural sobre dados de saúde pública (DataSUS) com suporte a múltiplos temas e modelos LLM locais",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rotas
app.include_router(query.router, prefix="/api", tags=["query"])
app.include_router(questions.router, prefix="/api", tags=["questions"])
app.include_router(admin.router, prefix="/api", tags=["admin"])

# Health check
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "EasyDataSUS"}

@app.get("/")
def root():
    return {
        "service": "EasyDataSUS",
        "version": "1.0.0",
        "status": "running",
        "description": "Sistema de consultas em linguagem natural sobre dados de saúde (DataSUS)",
        "documentation": "/docs",
        "openapi_schema": "/openapi.json",
        "endpoints": {
            "health": {
                "method": "GET",
                "url": "/health",
                "description": "Verificar saúde do servidor"
            },
            "questions": {
                "method": "GET",
                "url": "/api/questions",
                "description": "Listar perguntas pré-prontas por dataset"
            },
            "ask": {
                "method": "POST",
                "url": "/api/ask",
                "description": "Fazer pergunta em português e receber resposta interpretada"
            },
            "admin_upload": {
                "method": "POST",
                "url": "/api/admin/datasets/upload",
                "description": "Upload de CSV para um dataset"
            },
            "admin_available": {
                "method": "GET",
                "url": "/api/admin/datasets/available",
                "description": "Listar datasets disponíveis"
            },
            "admin_info": {
                "method": "GET",
                "url": "/api/admin/datasets/{dataset_id}/info",
                "description": "Informações detalhadas de um dataset"
            }
        },
        "quick_start": {
            "1_learn": "Veja a documentação em /docs",
            "2_get_questions": "GET /api/questions",
            "3_ask_question": "POST /api/ask com {\"question\": \"...\", \"dataset\": \"covid-19-vacinacao\"}",
            "4_upload_data": "POST /api/admin/datasets/upload (requer arquivo CSV)"
        }
    }

if __name__ == "__main__":
    import uvicorn
    host = os.getenv("FASTAPI_HOST", "0.0.0.0")
    port = int(os.getenv("FASTAPI_PORT", "8000"))
    
    logger.info(f"Iniciando EasyDataSUS em {host}:{port}")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level=os.getenv("FASTAPI_LOG_LEVEL", "info").lower()
    )