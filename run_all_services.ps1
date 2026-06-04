# Script PowerShell para iniciar todos os serviços EasyDataSUS
# 
# Uso:
#   .\run_all_services.ps1                # Inicia todos os serviços
#   .\run_all_services.ps1 -Test          # Inicia + executa testes
#   .\run_all_services.ps1 -TestVerbose   # Inicia + testes detalhado
#   .\run_all_services.ps1 -Stop          # Para todos os serviços

param(
    [switch]$Test,
    [switch]$TestVerbose,
    [switch]$Stop
)

# Configuração
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommandPath
$BackendDir = Join-Path $ProjectRoot "backend"

function Write-Header {
    param([string]$Message)
    Write-Host "`n" -ForegroundColor Gray
    Write-Host ("=" * 80) -ForegroundColor Cyan
    Write-Host $Message.PadLeft(40 + $Message.Length / 2) -ForegroundColor Cyan -BackgroundColor Black
    Write-Host ("=" * 80) -ForegroundColor Cyan
    Write-Host "`n" -ForegroundColor Gray
}

function Write-Success {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor Green
}

function Write-Info {
    param([string]$Message)
    Write-Host "ℹ️  $Message" -ForegroundColor Cyan
}

function Write-Warning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor Yellow
}

function Write-Error-Custom {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor Red
}

function Check-Docker {
    Write-Info "Verificando Docker..."
    try {
        $result = docker ps 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Docker está rodando"
            return $true
        } else {
            Write-Error-Custom "Docker não está rodando"
            return $false
        }
    } catch {
        Write-Error-Custom "Docker não encontrado"
        return $false
    }
}

function Check-ClickHouse {
    Write-Info "Verificando ClickHouse..."
    try {
        $result = docker exec easydatasus-clickhouse-1 clickhouse-client --query "SELECT 1" 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "ClickHouse está rodando"
            return $true
        } else {
            Write-Warning "ClickHouse não respondeu"
            return $false
        }
    } catch {
        Write-Warning "ClickHouse não acessível"
        return $false
    }
}

function Start-ClickHouse {
    Write-Info "Iniciando ClickHouse..."
    try {
        Push-Location $ProjectRoot
        docker-compose up -d clickhouse 2>$null
        Pop-Location
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "ClickHouse iniciado"
            Start-Sleep -Seconds 3
            return $true
        } else {
            Write-Error-Custom "Erro ao iniciar ClickHouse"
            return $false
        }
    } catch {
        Write-Error-Custom "Erro ao iniciar ClickHouse: $_"
        return $false
    }
}

function Check-Ollama {
    Write-Info "Verificando Ollama..."
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Success "Ollama está acessível em http://localhost:11434"
            return $true
        } else {
            Write-Warning "Ollama não respondeu"
            return $false
        }
    } catch {
        Write-Warning "Ollama não encontrado"
        return $false
    }
}

function Start-Ollama {
    Write-Info "Iniciando Ollama..."
    try {
        $ollamaPath = Get-Command ollama -ErrorAction SilentlyContinue
        if (-not $ollamaPath) {
            Write-Error-Custom "Ollama não encontrado no PATH"
            return $false
        }
        
        # Start Ollama in new console window
        Start-Process -FilePath "ollama" -ArgumentList "serve" -NoNewWindow
        
        Write-Info "Aguardando Ollama inicializar..."
        Start-Sleep -Seconds 5
        
        # Verify Ollama
        for ($i = 0; $i -lt 10; $i++) {
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:11434/api/tags" -TimeoutSec 2 -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    Write-Success "Ollama iniciado em http://localhost:11434"
                    return $true
                }
            } catch {
                Start-Sleep -Seconds 1
            }
        }
        
        Write-Warning "Ollama pode estar iniciando ainda..."
        return $true
    } catch {
        Write-Error-Custom "Erro ao iniciar Ollama: $_"
        return $false
    }
}

function Start-FastAPI {
    Write-Info "Iniciando FastAPI Backend..."
    try {
        $process = Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000" -WorkingDirectory $BackendDir -PassThru
        
        Write-Info "Aguardando FastAPI inicializar..."
        Start-Sleep -Seconds 5
        
        # Verify FastAPI
        for ($i = 0; $i -lt 10; $i++) {
            try {
                $response = Invoke-WebRequest -Uri "http://localhost:8000/docs" -TimeoutSec 2 -ErrorAction SilentlyContinue
                if ($response.StatusCode -eq 200) {
                    Write-Success "FastAPI iniciado em http://localhost:8000"
                    Write-Info "Documentação em http://localhost:8000/docs"
                    return $process
                }
            } catch {
                Start-Sleep -Seconds 1
            }
        }
        
        Write-Warning "FastAPI pode estar iniciando ainda..."
        return $process
    } catch {
        Write-Error-Custom "Erro ao iniciar FastAPI: $_"
        return $null
    }
}

function Run-Tests {
    param([bool]$Verbose = $false)
    
    Write-Header "🧪 EXECUTANDO TESTES DAS 68 QUESTÕES"
    
    try {
        $args = @("test_68_questoes_seidig.py")
        if ($Verbose) {
            $args += "--verbose"
        }
        
        Push-Location $ProjectRoot
        python @args
        Pop-Location
        
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Testes completados com sucesso!"
            
            # Try to display results
            $resultsFile = Join-Path $ProjectRoot "test_results_68_questoes.json"
            if (Test-Path $resultsFile) {
                $results = Get-Content $resultsFile -Raw | ConvertFrom-Json
                Write-Info "Total: $($results.total_questions) questões"
                Write-Success "Passaram: $($results.passed) ($([math]::Round($results.success_rate * 100, 1))%)"
                Write-Info "Tempo total: $([math]::Round($results.total_time, 1))s"
            }
            
            return $true
        } else {
            Write-Error-Custom "Testes falharam"
            return $false
        }
    } catch {
        Write-Error-Custom "Erro ao executar testes: $_"
        return $false
    }
}

function Stop-Services {
    Write-Header "⛔ PARANDO SERVIÇOS"
    
    Write-Info "Parando ClickHouse..."
    try {
        docker-compose down
        Write-Success "ClickHouse parado"
    } catch {
        Write-Warning "Erro ao parar ClickHouse"
    }
    
    Write-Success "Serviços parados"
}

# Main execution
Write-Header "🚀 AUTOMAÇÃO EASYDATASUS - INICIANDO SERVIÇOS"

if ($Stop) {
    Stop-Services
    exit
}

# Check prerequisites
Write-Host "`n" -ForegroundColor Gray
Write-Host ("─" * 80) -ForegroundColor Gray
Write-Host "1️⃣  VERIFICANDO PREREQUISITES" -ForegroundColor Cyan
Write-Host ("─" * 80) -ForegroundColor Gray
Write-Host "`n" -ForegroundColor Gray

if (-not (Check-Docker)) {
    Write-Error-Custom "Docker é necessário. Instale e tente novamente."
    exit 1
}

# Start ClickHouse
Write-Host "`n" -ForegroundColor Gray
Write-Host ("─" * 80) -ForegroundColor Gray
Write-Host "2️⃣  INICIANDO BANCO DE DADOS (ClickHouse)" -ForegroundColor Cyan
Write-Host ("─" * 80) -ForegroundColor Gray
Write-Host "`n" -ForegroundColor Gray

if (-not (Check-ClickHouse)) {
    if (-not (Start-ClickHouse)) {
        Write-Error-Custom "Falha ao iniciar ClickHouse"
        exit 1
    }
}

# Start Ollama
Write-Host "`n" -ForegroundColor Gray
Write-Host ("─" * 80) -ForegroundColor Gray
Write-Host "3️⃣  INICIANDO LLM LOCAL (Ollama)" -ForegroundColor Cyan
Write-Host ("─" * 80) -ForegroundColor Gray
Write-Host "`n" -ForegroundColor Gray

if (-not (Check-Ollama)) {
    if (-not (Start-Ollama)) {
        Write-Warning "Ollama não foi iniciado - alguns testes podem falhar"
    }
}

# Start FastAPI
Write-Host "`n" -ForegroundColor Gray
Write-Host ("─" * 80) -ForegroundColor Gray
Write-Host "4️⃣  INICIANDO API REST (FastAPI)" -ForegroundColor Cyan
Write-Host ("─" * 80) -ForegroundColor Gray
Write-Host "`n" -ForegroundColor Gray

$fastAPIProcess = Start-FastAPI

# Summary
Write-Header "✅ TODOS OS SERVIÇOS INICIADOS"

Write-Host "Serviços Disponíveis:" -ForegroundColor Green -BackgroundColor Black
Write-Host "  🗄️  ClickHouse:  http://localhost:9000 (admin:admin)" -ForegroundColor Green
Write-Host "  🧠 Ollama:      http://localhost:11434" -ForegroundColor Green
Write-Host "  🔌 FastAPI:     http://localhost:8000" -ForegroundColor Green
Write-Host "  📚 Documentação: http://localhost:8000/docs" -ForegroundColor Green
Write-Host ""

# Run tests if requested
if ($Test -or $TestVerbose) {
    Start-Sleep -Seconds 2
    Run-Tests -Verbose $TestVerbose
}

# Keep running
Write-Host "`n" -ForegroundColor Gray
Write-Host ("─" * 80) -ForegroundColor Gray
Write-Host "Pressione Ctrl+C para parar os serviços" -ForegroundColor Yellow
Write-Host ("─" * 80) -ForegroundColor Gray
Write-Host "`n" -ForegroundColor Gray

try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} catch [System.OperationCanceledException] {
    Write-Host "`n`nParando serviços..." -ForegroundColor Yellow
    if ($fastAPIProcess) {
        Stop-Process -Id $fastAPIProcess.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Success "Serviços parados"
}
