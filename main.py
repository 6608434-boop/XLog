#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
XLog — автоматический логгер чатов DeepSeek в Яндекс.Диск
Версия: 0.4 (с поддержкой Telegram бота)
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Добавляем путь к source, чтобы импорты работали
sys.path.insert(0, str(Path(__file__).parent))

from source.logger import logger
from source.yadisk_client import YandexDiskClient
from source.deepseek_client import DeepSeekClient
from source.profile_manager import ProfileManager
from source.telegram_bot import TelegramBot


def load_environment():
    """Загружает переменные окружения из .env файла."""
    load_dotenv()

    required_vars = [
        "DEEPSEEK_API_KEY",
        "YANDEX_DISK_TOKEN",
        "TELEGRAM_BOT_TOKEN"
    ]

    config = {}
    for var in required_vars:
        value = os.getenv(var)
        if not value:
            logger.error(f"Missing required environment variable: {var}")
            sys.exit(1)
        config[var] = value

    # Опциональные переменные
    config["YANDEX_ROOT_FOLDER"] = os.getenv("YANDEX_ROOT_FOLDER", "XLog")

    return config


def main():
    """Главная функция программы."""
    logger.info("=" * 50)
    logger.info("XLog — DeepSeek Logger starting...")
    logger.info("=" * 50)

    # Загружаем конфигурацию
    config = load_environment()

    # Инициализируем клиенты
    try:
        disk = YandexDiskClient(
            token=config["YANDEX_DISK_TOKEN"],
            root_folder=config["YANDEX_ROOT_FOLDER"]
        )

        deepseek = DeepSeekClient(
            api_key=config["DEEPSEEK_API_KEY"]
        )

        profiles = ProfileManager(disk_client=disk)

        # Проверяем, есть ли профили в конфиге
        if not profiles.get_all_profiles():
            logger.error("No profiles found in config/profiles.json")
            return

        logger.info(f"Loaded {len(profiles.get_all_profiles())} profiles: "
                    f"{[p['name'] for p in profiles.get_all_profiles()]}")

    except Exception as e:
        logger.error(f"Failed to initialize: {e}", exc_info=True)
        return

    # Запускаем Telegram бота
    logger.info("Starting Telegram bot...")
    bot = TelegramBot(
        token=config["TELEGRAM_BOT_TOKEN"],
        profiles=profiles,
        deepseek=deepseek
    )

    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.error(f"Bot error: {e}", exc_info=True)


if __name__ == "__main__":
    main()