# Test script for EasyDataSUS API (Windows)
# Run with: powershell -ExecutionPolicy Bypass -File test.ps1

$ErrorActionPreference = "Continue"

Write-Host "🧪 EasyDataSUS Test Suite (Windows)" -ForegroundColor Green
Write-Host "===================================" -ForegroundColor Green
Write-Host ""

$BASE_URL = "http://localhost:8000"

function Test-Endpoint {
    param(
        [string]$Name,
        [string]$Method,
        [string]$Endpoint,
        [string]$Data
    )
    
    Write-Host "[TEST] $Name" -ForegroundColor Yellow
    Write-Host "  URL: $Method $Endpoint"
    
    try {
        if ($Method -eq "GET") {
            $response = Invoke-WebRequest -Uri "$BASE_URL$Endpoint" -Method Get -ErrorAction Continue
        } else {
            $response = Invoke-WebRequest -Uri "$BASE_URL$Endpoint" -Method Post `
                -Headers @{"Content-Type"="application/json"} `
                -Body $Data `
                -ErrorAction Continue
        }
        
        $statusCode = $response.StatusCode
        $body = $response.Content
        
        if ($statusCode -eq 200) {
            Write-Host "  ✅ Status: $statusCode" -ForegroundColor Green
            $preview = $body.Substring(0, [Math]::Min(100, $body.Length))
            Write-Host "  Response: $preview..."
        } else {
            Write-Host "  ❌ Status: $statusCode" -ForegroundColor Red
            Write-Host "  Error: $body"
        }
    } catch {
        Write-Host "  ❌ Error: $($_Exception.Message)" -ForegroundColor Red
    }
    Write-Host ""
}

# Test Suite 1: Health Checks
Write-Host "=== Test Suite 1: Health Checks ===" -ForegroundColor Yellow
Write-Host ""

Test-Endpoint "Health Check" "GET" "/health"
Test-Endpoint "Root Endpoint" "GET" "/"

# Test Suite 2: Questions
Write-Host "=== Test Suite 2: Questions ===" -ForegroundColor Yellow
Write-Host ""

Test-Endpoint "Get Predefined Questions" "GET" "/api/questions"

# Test Suite 3: SQL Generation
Write-Host "=== Test Suite 3: SQL Generation ===" -ForegroundColor Yellow
Write-Host ""

Write-Host "Testing with deepseek-local..." -ForegroundColor Yellow
$query1 = @{
    question = "Quantas vacinas foram aplicadas em SP?"
    model = "deepseek-local"
} | ConvertTo-Json

Test-Endpoint "Query: Quantas vacinas em SP?" "POST" "/api/ask" $query1

Write-Host "Testing with openai..." -ForegroundColor Yellow
$query2 = @{
    question = "Quantas vacinas em RJ?"
    model = "openai"
} | ConvertTo-Json

Test-Endpoint "Query: Quantas vacinas em RJ?" "POST" "/api/ask" $query2

# Test Suite 4: Complex Queries
Write-Host "=== Test Suite 4: Complex Queries ===" -ForegroundColor Yellow
Write-Host ""

$query3 = @{
    question = "Quantas doses foram aplicadas de cada vacina?"
    model = "deepseek-local"
} | ConvertTo-Json

Test-Endpoint "Query: Doses por vacina" "POST" "/api/ask" $query3

$query4 = @{
    question = "Quantas aplicações em Florianópolis?"
    model = "deepseek-local"
} | ConvertTo-Json

Test-Endpoint "Query: Municípios" "POST" "/api/ask" $query4

# Test Suite 5: Error Handling
Write-Host "=== Test Suite 5: Error Handling ===" -ForegroundColor Yellow
Write-Host ""

Write-Host "[TEST] Invalid model" -ForegroundColor Yellow
try {
    $invalidQuery = @{
        question = "test"
        model = "invalid-model"
    } | ConvertTo-Json
    
    $response = Invoke-WebRequest -Uri "$BASE_URL/api/ask" -Method Post `
        -Headers @{"Content-Type"="application/json"} `
        -Body $invalidQuery `
        -ErrorAction Continue
    
    if ($response.StatusCode -ne 200) {
        Write-Host "  ✅ Correctly rejected invalid model (Status: $($response.StatusCode))" -ForegroundColor Green
    } else {
        Write-Host "  ❌ Should reject invalid model" -ForegroundColor Red
    }
} catch {
    Write-Host "  ✅ Correctly rejected (Error: $($_Exception.Message))" -ForegroundColor Green
}
Write-Host ""

# Summary
Write-Host "========================================" -ForegroundColor Green
Write-Host "🎉 Test suite completed!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Cheque os logs: docker-compose logs -f"
Write-Host "  2. Teste no browser: http://localhost:8000"
Write-Host "  3. Veja a documentação: README.md"
Write-Host ""
