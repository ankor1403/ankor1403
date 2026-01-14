#!/bin/bash
# Скрипт для развертывания диагностических скриптов на VPS сервер

echo "🚀 Развертывание диагностических скриптов"
echo "=========================================="
echo ""

# Параметры сервера
SERVER="${1:-root@ixhyswhgny}"
DEPLOY_DIR="/opt/avito-service"

if [ -z "$1" ]; then
    echo "ℹ️  Используется сервер по умолчанию: $SERVER"
    echo "   Для другого сервера: $0 root@your-server"
    echo ""
fi

echo "📦 Копирование скриптов на сервер..."
echo ""

# Копируем скрипты на сервер
scp -r \
    check-messenger-status.sh \
    fix-callback-user-id.sh \
    monitor-worker.sh \
    MESSENGER_DEPLOYMENT_STATUS.md \
    ${SERVER}:${DEPLOY_DIR}/

if [ $? -ne 0 ]; then
    echo "❌ Ошибка при копировании файлов"
    echo ""
    echo "Попробуйте скопировать вручную:"
    echo "  scp check-messenger-status.sh ${SERVER}:${DEPLOY_DIR}/"
    echo "  scp fix-callback-user-id.sh ${SERVER}:${DEPLOY_DIR}/"
    echo "  scp monitor-worker.sh ${SERVER}:${DEPLOY_DIR}/"
    echo "  scp MESSENGER_DEPLOYMENT_STATUS.md ${SERVER}:${DEPLOY_DIR}/"
    exit 1
fi

echo "✅ Скрипты скопированы на сервер"
echo ""

# Делаем скрипты исполняемыми
echo "🔧 Настройка прав доступа..."
ssh ${SERVER} "chmod +x ${DEPLOY_DIR}/*.sh"

if [ $? -eq 0 ]; then
    echo "✅ Права доступа настроены"
else
    echo "⚠️  Не удалось настроить права. Выполните на сервере:"
    echo "   chmod +x ${DEPLOY_DIR}/*.sh"
fi

echo ""
echo "=========================================="
echo "✅ РАЗВЕРТЫВАНИЕ ЗАВЕРШЕНО!"
echo "=========================================="
echo ""
echo "📋 Следующие шаги:"
echo ""
echo "1. Подключитесь к серверу:"
echo "   ssh ${SERVER}"
echo ""
echo "2. Перейдите в директорию:"
echo "   cd ${DEPLOY_DIR}"
echo ""
echo "3. Запустите диагностику:"
echo "   ./check-messenger-status.sh"
echo ""
echo "4. Если нужно - примените фикс:"
echo "   ./fix-callback-user-id.sh"
echo ""
echo "5. Переавторизуйте профиль в браузере"
echo ""
echo "6. Запустите мониторинг:"
echo "   ./monitor-worker.sh"
echo ""
echo "📖 Полная документация: ${DEPLOY_DIR}/MESSENGER_DEPLOYMENT_STATUS.md"
echo ""
