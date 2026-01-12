#!/usr/bin/env python3
"""
Скрипт для тестирования авторизации Telegram
Запустить на сервере: docker exec telegram-multi-service python3 /tmp/test_telegram_auth.py
"""

import asyncio
import sys
from telethon import TelegramClient
from telethon.errors import ApiIdInvalidError, PhoneNumberInvalidError, FloodWaitError

# Конфигурация из переменных окружения
API_ID = 28561380
API_HASH = 'c07bd084d44bb8f3d377aa6e1ea859ff'
PHONE = '+79277416299'  # Замените на ваш номер

async def test_send_code():
    """Тест отправки кода авторизации"""
    print("=== Тест отправки кода авторизации ===")

    client = TelegramClient('test_session', API_ID, API_HASH)

    try:
        await client.connect()
        print("✓ Подключение к Telegram установлено")

        # Проверка авторизации
        if await client.is_user_authorized():
            print("✓ Пользователь уже авторизован!")
            me = await client.get_me()
            print(f"  Имя: {me.first_name}")
            print(f"  ID: {me.id}")
            print(f"  Телефон: {me.phone}")
            return True

        print(f"Отправка кода на номер: {PHONE}")
        result = await client.send_code_request(PHONE)

        print("✓ Код успешно отправлен!")
        print(f"  Phone code hash: {result.phone_code_hash}")
        print(f"  Type: {type(result).__name__}")

        # Ожидание ввода кода
        code = input("Введите код из Telegram: ")

        # Попытка войти с кодом
        await client.sign_in(PHONE, code, phone_code_hash=result.phone_code_hash)
        print("✓ Авторизация успешна!")

        return True

    except ApiIdInvalidError as e:
        print(f"✗ Ошибка: Неверный API ID или Hash - {e}")
        return False
    except PhoneNumberInvalidError as e:
        print(f"✗ Ошибка: Неверный формат номера телефона - {e}")
        return False
    except FloodWaitError as e:
        print(f"✗ Ошибка: Слишком много запросов. Подождите {e.seconds} секунд")
        return False
    except Exception as e:
        print(f"✗ Неизвестная ошибка: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.disconnect()
        print("Отключение от Telegram")


async def test_qr_login():
    """Тест авторизации через QR код"""
    print("\n=== Тест авторизации через QR код ===")

    client = TelegramClient('test_qr_session', API_ID, API_HASH)

    try:
        await client.connect()
        print("✓ Подключение к Telegram установлено")

        if await client.is_user_authorized():
            print("✓ Пользователь уже авторизован!")
            return True

        print("Генерация QR кода для авторизации...")

        # QR логин требует telethon >= 1.24
        qr_login = await client.qr_login()

        # Отображение QR кода в терминале (опционально)
        import qrcode
        qr = qrcode.QRCode()
        qr.add_data(qr_login.url)
        qr.print_ascii()

        print(f"\nОткройте Telegram и отсканируйте QR код")
        print(f"Или перейдите по ссылке: {qr_login.url}")

        # Ожидание авторизации
        await qr_login.wait(timeout=300)  # 5 минут

        print("✓ Авторизация через QR код успешна!")
        return True

    except ImportError:
        print("✗ Модуль qrcode не установлен. Установите: pip install qrcode")
        print(f"  Но вы можете использовать URL для QR кода напрямую")
        return False
    except TimeoutError:
        print("✗ Время ожидания авторизации истекло")
        return False
    except Exception as e:
        print(f"✗ Ошибка: {type(e).__name__} - {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.disconnect()


async def main():
    """Главная функция"""
    print("Выберите метод тестирования:")
    print("1. Авторизация по коду (SMS)")
    print("2. Авторизация по QR коду")
    print("3. Оба метода")

    choice = input("Ваш выбор (1/2/3): ").strip()

    if choice == '1':
        await test_send_code()
    elif choice == '2':
        await test_qr_login()
    elif choice == '3':
        await test_send_code()
        await test_qr_login()
    else:
        print("Неверный выбор")
        sys.exit(1)


if __name__ == '__main__':
    asyncio.run(main())
