#!/bin/bash
# Скрипт для тестирования API endpoints Telegram Multi-Service
# Использование: bash test_api_endpoints.sh

BASE_URL="https://telegram.afonin-lisa.ru"
API_URL="https://tg.api.afonin-lisa.ru"

echo "=== Тестирование API Endpoints ==="
echo ""

# Цвета для вывода
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для тестирования endpoint
test_endpoint() {
    local method=$1
    local url=$2
    local data=$3
    local description=$4

    echo -e "${YELLOW}Тест:${NC} $description"
    echo "URL: $url"

    if [ -z "$data" ]; then
        response=$(curl -sk -X $method -w "\nHTTP_STATUS:%{http_code}" "$url")
    else
        response=$(curl -sk -X $method -H "Content-Type: application/json" -d "$data" -w "\nHTTP_STATUS:%{http_code}" "$url")
    fi

    http_code=$(echo "$response" | grep HTTP_STATUS | cut -d: -f2)
    body=$(echo "$response" | grep -v HTTP_STATUS)

    if [ $http_code -ge 200 ] && [ $http_code -lt 300 ]; then
        echo -e "${GREEN}✓ Успех${NC} (HTTP $http_code)"
    elif [ $http_code -ge 400 ] && [ $http_code -lt 500 ]; then
        echo -e "${YELLOW}⚠ Клиентская ошибка${NC} (HTTP $http_code)"
    else
        echo -e "${RED}✗ Ошибка${NC} (HTTP $http_code)"
    fi

    echo "Ответ:"
    echo "$body" | head -20
    echo ""
    echo "---"
    echo ""
}

# 1. Проверка главной страницы
test_endpoint "GET" "$BASE_URL/" "" "Главная страница"

# 2. Проверка health endpoint
test_endpoint "GET" "$BASE_URL/health" "" "Health check (Multi-Service)"

# 3. Проверка старого сервиса
test_endpoint "GET" "$API_URL/health" "" "Health check (Old Service)"

# 4. Проверка регистрации
test_endpoint "GET" "$BASE_URL/register" "" "Страница регистрации"

# 5. Попытка регистрации нового пользователя
USERNAME="testuser_$(date +%s)"
PASSWORD="TestPass123!"
test_endpoint "POST" "$BASE_URL/register" "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}" "Регистрация пользователя"

# 6. Попытка входа
test_endpoint "POST" "$BASE_URL/login" "username=$USERNAME&password=$PASSWORD" "Вход пользователя"

# 7. Проверка dashboard без авторизации
test_endpoint "GET" "$BASE_URL/dashboard" "" "Dashboard (без токена)"

# 8. Проверка OpenAPI спецификации
test_endpoint "GET" "$BASE_URL/openapi.json" "" "OpenAPI спецификация"

# 9. Проверка docs
test_endpoint "GET" "$BASE_URL/docs" "" "API документация (Swagger)"

# 10. Тест авторизации через старый сервис
test_endpoint "POST" "$API_URL/api/authorize" "{\"phone\":\"+79277416299\"}" "Авторизация в Telegram (старый API)"

echo "=== Тестирование завершено ==="
echo ""
echo "Примечания:"
echo "- Сохраните USERNAME и PASSWORD для дальнейшего тестирования"
echo "- Для полноценного тестирования нужен сессионный токен"
echo "- Используйте браузер для интерактивной авторизации"
