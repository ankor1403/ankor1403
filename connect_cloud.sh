#!/bin/bash
# Автоматическое подключение к облачному серверу через mTLS
# Использование: ./connect_cloud.sh [command]

set -e

CERT_DIR="/tmp/cloud_certs"
mkdir -p "$CERT_DIR"

# Проверка переменных окружения
check_env() {
    local missing=0
    for var in API_KEY CLIENT_CERT_PEM CLIENT_KEY_PEM CA_CERT_PEM AGENT_URL; do
        if [ -z "${!var}" ]; then
            echo "❌ Отсутствует: $var"
            missing=1
        else
            echo "✅ $var настроен"
        fi
    done
    return $missing
}

# Настройка сертификатов
setup_certs() {
    echo "$CLIENT_CERT_PEM" > "$CERT_DIR/client.crt"
    echo "$CLIENT_KEY_PEM" > "$CERT_DIR/client.key"
    echo "$CA_CERT_PEM" > "$CERT_DIR/ca.crt"
    chmod 600 "$CERT_DIR"/*
    echo "✅ Сертификаты настроены в $CERT_DIR"
}

# Тест подключения
test_connection() {
    echo "🔄 Тестирую подключение к $AGENT_URL..."

    response=$(curl -s -w "\n%{http_code}" \
        --cert "$CERT_DIR/client.crt" \
        --key "$CERT_DIR/client.key" \
        --cacert "$CERT_DIR/ca.crt" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        --max-time 10 \
        "$AGENT_URL/api/health" 2>/dev/null || echo "error")

    http_code=$(echo "$response" | tail -1)
    body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ]; then
        echo "✅ Подключение успешно!"
        echo "Response: $body"
        return 0
    else
        echo "❌ Ошибка подключения (HTTP: $http_code)"
        echo "Response: $body"
        return 1
    fi
}

# API запрос
api_request() {
    local endpoint="$1"
    local method="${2:-GET}"
    local data="$3"

    curl -s \
        --cert "$CERT_DIR/client.crt" \
        --key "$CERT_DIR/client.key" \
        --cacert "$CERT_DIR/ca.crt" \
        -H "Authorization: Bearer $API_KEY" \
        -H "Content-Type: application/json" \
        -X "$method" \
        ${data:+-d "$data"} \
        "$AGENT_URL$endpoint"
}

# Главное меню
main() {
    echo "========================================"
    echo "   Cloud Server Connection Manager"
    echo "   Server: $AGENT_URL"
    echo "========================================"
    echo ""

    case "${1:-status}" in
        status|check)
            echo "📋 Проверка конфигурации..."
            check_env
            ;;
        setup)
            echo "🔧 Настройка сертификатов..."
            check_env && setup_certs
            ;;
        test)
            echo "🧪 Тест подключения..."
            check_env && setup_certs && test_connection
            ;;
        api)
            setup_certs
            api_request "$2" "$3" "$4"
            ;;
        *)
            echo "Использование: $0 {status|setup|test|api <endpoint> [method] [data]}"
            echo ""
            echo "Команды:"
            echo "  status  - Проверить переменные окружения"
            echo "  setup   - Настроить сертификаты"
            echo "  test    - Тест подключения к серверу"
            echo "  api     - Выполнить API запрос"
            ;;
    esac
}

main "$@"
