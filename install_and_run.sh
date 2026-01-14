#!/bin/bash
###############################################################################
# МАСТЕР-СКРИПТ ДЛЯ АВТОМАТИЧЕСКОЙ УСТАНОВКИ И ДИАГНОСТИКИ TELEGRAM SERVICE
###############################################################################
# Этот скрипт автоматически:
# 1. Скачивает все необходимые файлы из GitHub
# 2. Делает их исполняемыми
# 3. Запускает диагностику
# 4. Предлагает исправить проблемы
###############################################################################

set -e  # Остановка при ошибке

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║  АВТОМАТИЧЕСКАЯ УСТАНОВКА И ДИАГНОСТИКА TELEGRAM SERVICE     ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функция для вывода с цветом
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Проверка наличия необходимых команд
print_info "Проверка установленных программ..."
for cmd in curl ssh; do
    if ! command -v $cmd &> /dev/null; then
        print_error "Программа '$cmd' не найдена. Пожалуйста, установите её."
        exit 1
    fi
done
print_status "Все необходимые программы установлены"
echo ""

# Создание рабочей директории
WORK_DIR="$HOME/telegram_service_fix"
print_info "Создание рабочей директории: $WORK_DIR"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"
print_status "Рабочая директория создана"
echo ""

# URL репозитория
REPO_URL="https://raw.githubusercontent.com/ankor1403/ankor1403/claude/audit-dependencies-mkbp0op9n8ha6qpk-Gt2Dm"

# Список файлов для скачивания
FILES=(
    "telegram_diagnostic.sh"
    "test_telegram_auth.py"
    "fix_telegram_service.sh"
    "test_api_endpoints.sh"
    "TELEGRAM_SERVICE_GUIDE.md"
)

# Скачивание файлов
print_info "Скачивание файлов из GitHub репозитория..."
echo ""
for file in "${FILES[@]}"; do
    echo -n "  Скачивание $file... "
    if curl -sSL "$REPO_URL/$file" -o "$file" 2>/dev/null; then
        print_status "OK"
    else
        print_error "ОШИБКА"
        print_error "Не удалось скачать $file"
        exit 1
    fi
done
echo ""
print_status "Все файлы успешно скачаны"
echo ""

# Делаем скрипты исполняемыми
print_info "Настройка прав доступа..."
chmod +x telegram_diagnostic.sh
chmod +x fix_telegram_service.sh
chmod +x test_api_endpoints.sh
print_status "Права доступа настроены"
echo ""

# Показываем скачанные файлы
print_info "Скачанные файлы:"
ls -lh
echo ""

# Запуск диагностики
print_info "═══════════════════════════════════════════════════════"
print_info "  ЗАПУСК ДИАГНОСТИКИ TELEGRAM SERVICE"
print_info "═══════════════════════════════════════════════════════"
echo ""

if [ -f "./telegram_diagnostic.sh" ]; then
    bash ./telegram_diagnostic.sh | tee diagnostic_report.txt
    echo ""
    print_status "Диагностика завершена. Отчёт сохранён в: diagnostic_report.txt"
else
    print_error "Файл telegram_diagnostic.sh не найден!"
    exit 1
fi

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                  ДИАГНОСТИКА ЗАВЕРШЕНА                       ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Предложение запустить исправление
print_warning "Хотите запустить автоматическое исправление проблем?"
print_info "Это перезапустит сервис и попытается исправить найденные проблемы."
echo ""
read -p "Запустить исправление? (y/n): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[YyДд]$ ]]; then
    echo ""
    print_info "═══════════════════════════════════════════════════════"
    print_info "  ЗАПУСК АВТОМАТИЧЕСКОГО ИСПРАВЛЕНИЯ"
    print_info "═══════════════════════════════════════════════════════"
    echo ""

    if [ -f "./fix_telegram_service.sh" ]; then
        bash ./fix_telegram_service.sh | tee fix_report.txt
        echo ""
        print_status "Исправление завершено. Отчёт сохранён в: fix_report.txt"
    else
        print_error "Файл fix_telegram_service.sh не найден!"
        exit 1
    fi
fi

echo ""
print_info "═══════════════════════════════════════════════════════"
print_info "  ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ"
print_info "═══════════════════════════════════════════════════════"
echo ""
echo "Для тестирования API endpoints:"
echo "  cd $WORK_DIR"
echo "  bash test_api_endpoints.sh"
echo ""
echo "Для тестирования авторизации Telegram:"
echo "  scp test_telegram_auth.py root@83.222.25.94:/tmp/"
echo "  ssh root@83.222.25.94 \"docker cp /tmp/test_telegram_auth.py telegram-multi-service:/tmp/\""
echo "  ssh root@83.222.25.94 \"docker exec -it telegram-multi-service python3 /tmp/test_telegram_auth.py\""
echo ""
echo "Для просмотра полного руководства:"
echo "  cat TELEGRAM_SERVICE_GUIDE.md"
echo ""
print_status "Установка и диагностика завершены успешно!"
echo ""
print_info "Все файлы находятся в: $WORK_DIR"
echo ""
