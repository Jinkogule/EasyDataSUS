@echo off
REM Script Batch para iniciar todos os serviços EasyDataSUS
REM
REM Uso:
REM   run_all_services.bat                   # Inicia todos os serviços
REM   run_all_services.bat test              # Inicia + executa testes
REM   run_all_services.bat test-verbose      # Inicia + testes detalhado
REM   run_all_services.bat stop              # Para todos os serviços

setlocal enabledelayedexpansion

REM Cores (não funciona em cmd, será usando emojis)
set "OK=✓"
set "FAIL=✗"
set "INFO=>"

REM Configuração
set "PROJECT_ROOT=%~dp0"
set "BACKEND_DIR=%PROJECT_ROOT%backend"

REM Parsing de argumentos
set "ACTION=start"
if "%1"=="test" set "ACTION=test"
if "%1"=="test-verbose" set "ACTION=test-verbose"
if "%1"=="stop" set "ACTION=stop"

echo.
echo ================================================================================
echo     🚀 AUTOMACAO EASYDATASUS - INICIANDO SERVICOS
echo ================================================================================
echo.

REM Ações
if "%ACTION%"=="stop" goto stop_services
if "%ACTION%"=="test" goto start_with_test
if "%ACTION%"=="test-verbose" goto start_with_test_verbose

REM Start normal
:start_services
echo [1/4] Verificando Docker...
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo %FAIL% Docker nao esta rodando
    echo.
    echo Inicie com: docker-compose up -d
    exit /b 1
)
echo %OK% Docker esta rodando
echo.

echo [2/4] Verificando ClickHouse...
docker exec easydatasus-clickhouse-1 clickhouse-client --query "SELECT 1" >nul 2>&1
if %errorlevel% equ 0 (
    echo %OK% ClickHouse esta rodando
) else (
    echo %INFO% Iniciando ClickHouse...
    cd /d "%PROJECT_ROOT%"
    docker-compose up -d clickhouse
    timeout /t 3 /nobreak
    echo %OK% ClickHouse iniciado
)
echo.

echo [3/4] Verificando Ollama...
curl -s http://localhost:11434/api/tags >nul 2>&1
if %errorlevel% equ 0 (
    echo %OK% Ollama esta acessivel
) else (
    echo %INFO% Iniciando Ollama...
    start /separate ollama serve
    timeout /t 5 /nobreak
    echo %OK% Ollama iniciado
)
echo.

echo [4/4] Iniciando FastAPI Backend...
cd /d "%BACKEND_DIR%"
start cmd /k "python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000"
timeout /t 3 /nobreak
echo %OK% FastAPI iniciado
echo.

echo ================================================================================
echo     ✅ TODOS OS SERVICOS INICIADOS
echo ================================================================================
echo.
echo Servicos Disponiveis:
echo   🗄️  ClickHouse:  http://localhost:9000 (admin:admin)
echo   🧠 Ollama:      http://localhost:11434
echo   🔌 FastAPI:     http://localhost:8000
echo   📚 Documentacao: http://localhost:8000/docs
echo.
echo Pressione qualquer tecla para abrir a documentacao no navegador...
pause >nul

start "" http://localhost:8000/docs

echo.
echo Servicos rodando em background. Pressione Ctrl+C para parar.
pause
goto end

:start_with_test
cd /d "%PROJECT_ROOT%"
call run_all_services.bat
timeout /t 5 /nobreak
echo.
echo ================================================================================
echo     🧪 EXECUTANDO TESTES DAS 68 QUESTOES
echo ================================================================================
echo.
python test_68_questoes_seidig.py
goto end

:start_with_test_verbose
cd /d "%PROJECT_ROOT%"
call run_all_services.bat
timeout /t 5 /nobreak
echo.
echo ================================================================================
echo     🧪 EXECUTANDO TESTES DAS 68 QUESTOES (VERBOSE)
echo ================================================================================
echo.
python test_68_questoes_seidig.py --verbose
goto end

:stop_services
echo Parando ClickHouse...
cd /d "%PROJECT_ROOT%"
docker-compose down
echo %OK% Servicos parados
goto end

:end
endlocal
