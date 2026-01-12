@echo off
chcp 65001 >nul
REM ############################################################################
REM # МАСТЕР-СКРИПТ ДЛЯ WINDOWS
REM # Автоматическая установка и диагностика Telegram Service
REM ############################################################################

setlocal enabledelayedexpansion

echo ╔══════════════════════════════════════════════════════════════╗
echo ║  АВТОМАТИЧЕСКАЯ УСТАНОВКА И ДИАГНОСТИКА TELEGRAM SERVICE     ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Проверка наличия curl
curl --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] curl не установлен!
    echo Пожалуйста, установите curl с https://curl.se/windows/
    pause
    exit /b 1
)

REM Проверка наличия ssh
ssh -V >nul 2>&1
if %errorlevel% neq 0 (
    echo [ОШИБКА] ssh не установлен!
    echo Пожалуйста, установите OpenSSH или используйте Git Bash
    pause
    exit /b 1
)

echo [OK] Все необходимые программы установлены
echo.

REM Создание рабочей директории
set "WORK_DIR=%USERPROFILE%\telegram_service_fix"
echo [INFO] Создание рабочей директории: %WORK_DIR%
if not exist "%WORK_DIR%" mkdir "%WORK_DIR%"
cd /d "%WORK_DIR%"
echo [OK] Рабочая директория создана
echo.

REM URL репозитория
set "REPO_URL=https://raw.githubusercontent.com/ankor1403/ankor1403/claude/audit-dependencies-mkbp0op9n8ha6qpk-Gt2Dm"

REM Скачивание файлов
echo [INFO] Скачивание файлов из GitHub репозитория...
echo.

echo   Скачивание telegram_diagnostic.sh...
curl -sSL "%REPO_URL%/telegram_diagnostic.sh" -o telegram_diagnostic.sh
if %errorlevel% neq 0 (
    echo [ОШИБКА] Не удалось скачать telegram_diagnostic.sh
    pause
    exit /b 1
)
echo   [OK] telegram_diagnostic.sh

echo   Скачивание test_telegram_auth.py...
curl -sSL "%REPO_URL%/test_telegram_auth.py" -o test_telegram_auth.py
if %errorlevel% neq 0 (
    echo [ОШИБКА] Не удалось скачать test_telegram_auth.py
    pause
    exit /b 1
)
echo   [OK] test_telegram_auth.py

echo   Скачивание fix_telegram_service.sh...
curl -sSL "%REPO_URL%/fix_telegram_service.sh" -o fix_telegram_service.sh
if %errorlevel% neq 0 (
    echo [ОШИБКА] Не удалось скачать fix_telegram_service.sh
    pause
    exit /b 1
)
echo   [OK] fix_telegram_service.sh

echo   Скачивание test_api_endpoints.sh...
curl -sSL "%REPO_URL%/test_api_endpoints.sh" -o test_api_endpoints.sh
if %errorlevel% neq 0 (
    echo [ОШИБКА] Не удалось скачать test_api_endpoints.sh
    pause
    exit /b 1
)
echo   [OK] test_api_endpoints.sh

echo   Скачивание TELEGRAM_SERVICE_GUIDE.md...
curl -sSL "%REPO_URL%/TELEGRAM_SERVICE_GUIDE.md" -o TELEGRAM_SERVICE_GUIDE.md
if %errorlevel% neq 0 (
    echo [ОШИБКА] Не удалось скачать TELEGRAM_SERVICE_GUIDE.md
    pause
    exit /b 1
)
echo   [OK] TELEGRAM_SERVICE_GUIDE.md

echo.
echo [OK] Все файлы успешно скачаны
echo.

REM Показываем скачанные файлы
echo [INFO] Скачанные файлы:
dir /b
echo.

REM Запуск диагностики
echo ═══════════════════════════════════════════════════════
echo   ЗАПУСК ДИАГНОСТИКИ TELEGRAM SERVICE
echo ═══════════════════════════════════════════════════════
echo.

REM Используем bash для запуска скрипта (если доступен)
where bash >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] Запуск диагностики через bash...
    bash telegram_diagnostic.sh > diagnostic_report.txt 2>&1
    type diagnostic_report.txt
    echo.
    echo [OK] Диагностика завершена. Отчёт сохранён в: diagnostic_report.txt
) else (
    echo [INFO] bash не найден. Запуск диагностики через ssh...
    ssh root@83.222.25.94 "bash -s" < telegram_diagnostic.sh > diagnostic_report.txt 2>&1
    type diagnostic_report.txt
    echo.
    echo [OK] Диагностика завершена. Отчёт сохранён в: diagnostic_report.txt
)

echo.
echo ╔══════════════════════════════════════════════════════════════╗
echo ║                  ДИАГНОСТИКА ЗАВЕРШЕНА                       ║
echo ╚══════════════════════════════════════════════════════════════╝
echo.

REM Предложение запустить исправление
set /p "REPLY=Хотите запустить автоматическое исправление проблем? (y/n): "
if /i "%REPLY%"=="y" goto run_fix
if /i "%REPLY%"=="д" goto run_fix
goto show_commands

:run_fix
echo.
echo ═══════════════════════════════════════════════════════
echo   ЗАПУСК АВТОМАТИЧЕСКОГО ИСПРАВЛЕНИЯ
echo ═══════════════════════════════════════════════════════
echo.

where bash >nul 2>&1
if %errorlevel% equ 0 (
    bash fix_telegram_service.sh > fix_report.txt 2>&1
    type fix_report.txt
    echo.
    echo [OK] Исправление завершено. Отчёт сохранён в: fix_report.txt
) else (
    ssh root@83.222.25.94 "bash -s" < fix_telegram_service.sh > fix_report.txt 2>&1
    type fix_report.txt
    echo.
    echo [OK] Исправление завершено. Отчёт сохранён в: fix_report.txt
)

:show_commands
echo.
echo ═══════════════════════════════════════════════════════
echo   ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ
echo ═══════════════════════════════════════════════════════
echo.
echo Для тестирования API endpoints:
echo   cd %WORK_DIR%
echo   bash test_api_endpoints.sh
echo.
echo Для тестирования авторизации Telegram:
echo   scp test_telegram_auth.py root@83.222.25.94:/tmp/
echo   ssh root@83.222.25.94 "docker cp /tmp/test_telegram_auth.py telegram-multi-service:/tmp/"
echo   ssh root@83.222.25.94 "docker exec -it telegram-multi-service python3 /tmp/test_telegram_auth.py"
echo.
echo Для просмотра полного руководства:
echo   notepad TELEGRAM_SERVICE_GUIDE.md
echo.
echo [OK] Установка и диагностика завершены успешно!
echo.
echo [INFO] Все файлы находятся в: %WORK_DIR%
echo.

pause
