#!/bin/bash

# Setup script for EasyDataSUS
# Usage: bash setup.sh

set -e

echo "🚀 EasyDataSUS Setup Script"
echo "============================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Check prerequisites
echo -e "${YELLOW}1. Verificando pré-requisitos...${NC}"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker não encontrado${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}❌ Docker Compose não encontrado${NC}"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 não encontrado${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Todos os pré-requisitos encontrados${NC}"
echo ""

# 2. Setup Backend
echo -e "${YELLOW}2. Configurando backend...${NC}"

cd backend

if [ ! -f ".env" ]; then
    echo "  📋 Copiando .env.example para .env..."
    cp .env.example .env
    echo -e "${GREEN}  ✅ Arquivo .env criado${NC}"
else
    echo -e "${GREEN}  ✅ Arquivo .env já existe${NC}"
fi

# 3. Create virtual environment
echo ""
echo -e "${YELLOW}3. Criando ambiente virtual Python...${NC}"

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}  ✅ Ambiente virtual criado${NC}"
else
    echo -e "${GREEN}  ✅ Ambiente virtual já existe${NC}"
fi

# 4. Activate and install dependencies
echo ""
echo -e "${YELLOW}4. Instalando dependências...${NC}"

source venv/bin/activate  # For Linux/Mac

pip install -q -r requirements.txt

echo -e "${GREEN}✅ Dependências instaladas${NC}"

# 5. Start ClickHouse
cd ..

echo ""
echo -e "${YELLOW}5. Iniciando ClickHouse...${NC}"

if docker-compose ps clickhouse | grep -q "Up"; then
    echo -e "${GREEN}  ✅ ClickHouse já está rodando${NC}"
else
    echo "  ⏳ Aguarde 30 segundos para ClickHouse iniciar..."
    docker-compose up -d clickhouse
    sleep 30
    echo -e "${GREEN}  ✅ ClickHouse iniciado${NC}"
fi

# 6. Load data
echo ""
echo -e "${YELLOW}6. Carregando dados do CSV...${NC}"

cd backend

source venv/bin/activate

if python etl/load_csv.py 2>&1 | tail -5; then
    echo -e "${GREEN}✅ Dados carregados com sucesso${NC}"
else
    echo -e "${YELLOW}⚠️  Erro ao carregar dados (pode ser normal se já carregados)${NC}"
fi

# 7. Summary
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}✅ Setup concluído com sucesso!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Próximos passos:"
echo ""
echo "  1. Ativar ambiente virtual:"
echo "     ${YELLOW}cd backend && source venv/bin/activate${NC}"
echo ""
echo "  2. Configurar .env (se necessário):"
echo "     ${YELLOW}nano ../backend/.env${NC}"
echo ""
echo "  3. Iniciar servidor:"
echo "     ${YELLOW}python main.py${NC}"
echo ""
echo "  4. Testar em outro terminal:"
echo "     ${YELLOW}curl http://localhost:8000/health${NC}"
echo ""
