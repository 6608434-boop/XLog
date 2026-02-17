import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Any
from datetime import datetime

from .logger import logger
from .yadisk_client import YandexDiskClient


class ProfileManager:
    def __init__(self, disk_client: YandexDiskClient, config_path: str = "config/profiles.json"):
        """
        Инициализация менеджера профилей.

        Args:
            disk_client: Клиент Яндекс.Диска
            config_path: Путь к файлу с конфигурацией профилей
        """
        self.disk = disk_client
        self.config = self._load_config(config_path)
        self.state = self._load_state()

    def _load_config(self, config_path: str) -> Dict:
        """Загружает конфигурацию профилей."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return {"profiles": []}

    def _load_state(self) -> Dict:
        """Загружает состояние (последние ID сообщений)."""
        state_file = Path("data/state.json")
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load state: {e}")
        return {}

    def _save_state(self):
        """Сохраняет состояние."""
        try:
            os.makedirs("data", exist_ok=True)
            with open("data/state.json", 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    def get_all_profiles(self) -> List[Dict]:
        """Возвращает список всех профилей."""
        return self.config.get("profiles", [])

    def get_last_message_id(self, profile_name: str) -> Optional[str]:
        """Возвращает последний обработанный ID для профиля."""
        return self.state.get(profile_name, {}).get("last_id")

    def set_last_message_id(self, profile_name: str, last_id: str):
        """Устанавливает последний обработанный ID для профиля."""
        if profile_name not in self.state:
            self.state[profile_name] = {}
        self.state[profile_name]["last_id"] = last_id
        self._save_state()

    def is_initialized(self, profile_name: str) -> bool:
        """Проверяет, была ли загружена история для профиля."""
        return self.state.get(profile_name, {}).get("initialized", False)

    def set_initialized(self, profile_name: str):
        """Отмечает, что история для профиля загружена."""
        if profile_name not in self.state:
            self.state[profile_name] = {}
        self.state[profile_name]["initialized"] = True
        self._save_state()

    def get_profile_files(self, profile_name: str) -> Dict[str, Optional[str]]:
        """
        Читает все файлы профиля с Яндекс.Диска.

        Returns:
            Словарь с содержимым файлов: key, king, rules, library
        """
        files = {}
        for file_name in ["key.txt", "king.txt", "rules.txt", "library.txt"]:
            path = f"{profile_name}/{file_name}"
            files[file_name.replace('.txt', '')] = self.disk.read_file(path)
        return files

    def append_to_library(self, profile_name: str, text: str) -> bool:
        """Добавляет текст в library.txt профиля."""
        path = f"{profile_name}/library.txt"
        content = self.disk.read_file(path) or ""
        content += f"\n[{datetime.now().strftime('%d.%m.%Y %H:%M')}] {text}"
        return self.disk.write_to_file(path, content)

    def load_full_history(self, profile_name: str, chat_id: str, deepseek_client):
        """
        Загружает полную историю чата и сохраняет в Яндекс.Диск.
        """
        if self.is_initialized(profile_name):
            logger.info(f"Profile {profile_name} already initialized")
            return

        logger.info(f"Loading full history for {profile_name}...")
        logger.info("DeepSeek API does not provide chat history")
        logger.info("Marking profile as initialized without loading history")

        self.set_initialized(profile_name)
        logger.info(f"Profile {profile_name} marked as initialized")

    def check_new_messages(self, profile_name: str, chat_id: str, deepseek_client):
        """
        Проверяет новые сообщения для профиля.
        DeepSeek API не хранит историю, поэтому просто логируем.
        """
        logger.info(f"Checking for new messages: {profile_name}")
        logger.info("DeepSeek API does not provide message history")
        logger.debug("Use send_message() to interact with the API")

        # В будущем здесь можно добавить логику отправки сообщений
        # через deepseek_client.send_message()

        return []

    def save_message(self, profile_name: str, role: str, content: str, timestamp: Optional[datetime] = None):
        """
        Сохраняет одно сообщение в Яндекс.Диск.

        Args:
            profile_name: Имя профиля
            role: 'user' или 'assistant'
            content: Текст сообщения
            timestamp: Время сообщения (по умолчанию сейчас)
        """
        if timestamp is None:
            timestamp = datetime.now()

        log_path = f"{profile_name}/logs/{timestamp.year}/{timestamp.month:02d}/{timestamp.day:02d}/log.txt"
        time_str = timestamp.strftime("%H:%M:%S")
        formatted = f"[{time_str}] {role}: {content}\n"

        success = self.disk.write_to_file(log_path, formatted)
        if success:
            logger.info(f"Saved {role} message to {log_path}")
        else:
            logger.error(f"Failed to save {role} message")

        return success