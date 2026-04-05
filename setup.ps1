# Setup script for EasyDataSUS (Windows)
# Run with: powershell -ExecutionPolicy Bypass -File setup.ps1

$ErrorActionPreference = "Stop"

Write-Host "🚀 EasyDataSUS Setup Script (Windows)" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""

# 1. Check prerequisites
Write-Host "1. Verificando pré-requisitos..." -ForegroundColor Yellow

try {
    docker --version | Out-Null
} catch {
    Write-Host "❌ Docker não encontrado" -ForegroundColor Red
    exit 1
}

try {
    docker-compose --version | Out-Null
} catch {
    Write-Host "❌ Docker Compose não encontrado" -ForegroundColor Red
    exit 1
}

try {
    python --version | Out-Null
} catch {
    Write-Host "❌ Python não encontrado" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Todos os pré-requisitos encontrados" -ForegroundColor Green
Write-Host ""

# 2. Setup Backend
Write-Host "2. Configurando backend..." -ForegroundColor Yellow

Push-Location backend

if (-not (Test-Path ".env")) {
    Write-Host "  📋 Copiando .env.example para .env..."
    Copy-Item ".env.example" ".env"
    Write-Host "  ✅ Arquivo .env criado" -ForegroundColor Green
} else {
    Write-Host "  ✅ Arquivo .env já existe" -ForegroundColor Green
}

# 3. Create virtual environment
Write-Host ""
Write-Host "3. Criando ambiente virtual Python..." -ForegroundColor Yellow

if (-not (Test-Path "venv")) {
    python -m venv venv
    Write-Host "  ✅ Ambiente virtual criado" -ForegroundColor Green
} else {
    Write-Host "  ✅ Ambiente virtual já existe" -ForegroundColor Green
}

# 4. Activate and install dependencies
Write-Host ""
Write-Host "4. Instalando dependências..." -ForegroundColor Yellow

& .\venv\Scripts\Activate.ps1

pip install -q -r requirements.txt

Write-Host "✅ Dependências instaladas" -ForegroundColor Green

# 5. Start ClickHouse
Pop-Location

Write-Host ""
Write-Host "5. Iniciando ClickHouse..." -ForegroundColor Yellow

$clickhouseRunning = docker-compose ps clickhouse | Select-String "Up"

if ($clickhouseRunning) {
    Write-Host "  ✅ ClickHouse já está rodando" -ForegroundColor Green
} else {
    Write-Host "  ⏳ Aguarde 30 segundos para ClickHouse iniciar..."
    docker-compose up -d clickhouse
    Start-Sleep -Seconds 30
    Write-Host "  ✅ ClickHouse iniciado" -ForegroundColor Green
}

# 6. Load data
Write-Host ""
Write-Host "6. Carregando dados do CSV..." -ForegroundColor Yellow

Push-Location backend
& .\venv\Scripts\Activate.ps1

python etl/load_csv.py
Write-Host "✅ Dados carregados com sucesso" -ForegroundColor Green

# 7. Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ Setup concluído com sucesso!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Próximos passos:"
Write-Host ""
Write-Host "  1. Ambiente virtual já esta ativado"
Write-Host ""
Write-Host "  2. Configurar .env (se necessário):"
Write-Host "     notepad .env" -ForegroundColor Yellow
Write-Host ""
Write-Host "  3. Iniciar servidor:"
Write-Host "     python main.py" -ForegroundColor Yellow
Write-Host ""
Write-Host "  4. Testar em outro PowerShell:"
Write-Host "     curl http://localhost:8000/health" -ForegroundColor Yellow
Write-Host ""
