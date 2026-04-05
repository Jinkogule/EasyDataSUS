#!/bin/bash

# Test script for EasyDataSUS API
# Testa os endpoints principais

set -e

echo "🧪 EasyDataSUS Test Suite"
echo "=========================="
echo ""

BASE_URL="http://localhost:8000"

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Helper function to test endpoint
test_endpoint() {
    local name=$1
    local method=$2
    local endpoint=$3
    local data=$4
    
    echo -e "${YELLOW}[TEST]${NC} $name"
    echo "  URL: $method $endpoint"
    
    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    else
        response=$(curl -s -w "\n%{http_code}" -X "$method" \
            -H "Content-Type: application/json" \
            -d "$data" \
            "$BASE_URL$endpoint")
    fi
    
    http_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" -eq 200 ]; then
        echo -e "  ${GREEN}✅ Status: $http_code${NC}"
        echo "  Response: $(echo $body | head -c 100)..."
    else
        echo -e "  ${RED}❌ Status: $http_code${NC}"
        echo "  Error: $body"
        return 1
    fi
    echo ""
}

# Test 1: Health check
echo -e "${YELLOW}=== Test Suite 1: Health Checks ===${NC}"
echo ""

test_endpoint "Health Check" "GET" "/health"
test_endpoint "Root Endpoint" "GET" "/"

# Test 2: Questions
echo -e "${YELLOW}=== Test Suite 2: Questions ===${NC}"
echo ""

test_endpoint "Get Predefined Questions" "GET" "/api/questions"

# Test 3: SQL Generation (various models)
echo -e "${YELLOW}=== Test Suite 3: SQL Generation ===${NC}"
echo ""

# Test with DeepSeek Local (default)
echo -e "${YELLOW}Testing with deepseek-local...${NC}"
test_endpoint "Query: Quantas vacinas em SP?" "POST" "/api/ask" \
    '{"question": "Quantas vacinas foram aplicadas em SP?", "model": "deepseek-local"}'

# Test with OpenAI (if available)
echo -e "${YELLOW}Testing with openai...${NC}"
test_endpoint "Query: Quantas vacinas em RJ?" "POST" "/api/ask" \
    '{"question": "Quantas vacinas em RJ?", "model": "openai"}' || echo -e "${YELLOW}⚠️  OpenAI não disponível (provável: OPENAI_API_KEY não configurada)${NC}"

# Test 4: Complex queries
echo -e "${YELLOW}=== Test Suite 4: Complex Queries ===${NC}"
echo ""

test_endpoint "Query: Doses por vacina" "POST" "/api/ask" \
    '{"question": "Quantas doses foram aplicadas de cada vacina?", "model": "deepseek-local"}'

test_endpoint "Query: Municípios" "POST" "/api/ask" \
    '{"question": "Quantas aplicações em Florianópolis?", "model": "deepseek-local"}'

# Test 5: Error handling
echo -e "${YELLOW}=== Test Suite 5: Error Handling ===${NC}"
echo ""

echo -e "${YELLOW}[TEST]${NC} Invalid model"
response=$(curl -s -w "%{http_code}" -X POST \
    -H "Content-Type: application/json" \
    -d '{"question": "test", "model": "invalid-model"}' \
    "$BASE_URL/api/ask")
http_code=$(echo "$response" | tail -c 4)

if [ "$http_code" -ne 200 ]; then
    echo -e "  ${GREEN}✅ Correctly rejected invalid model (Status: $http_code)${NC}"
else
    echo -e "  ${RED}❌ Should reject invalid model${NC}"
fi
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 Test suite completed!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Cheque os logs para mais detalhes: docker-compose logs -f"
echo "  2. Teste no browser: http://localhost:8000"
echo "  3. Veja a documentação: README.md"
echo ""
