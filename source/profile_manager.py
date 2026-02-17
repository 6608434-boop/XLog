"""
Менеджер профилей XLog — работа с файлами профилей на Яндекс.Диске
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from .yadisk_client import YandexDiskClient
from .logger import logger

# Типы для удобства
ProfileDict = Dict[str, Any]
FilesDict = Dict[str, Optional[str]]


class ProfileManager:
    """Управляет профилями и их файлами на Яндекс.Диске"""

    # Список файлов, которые должны быть в каждом профиле
    PROFILE_FILES = ["key.txt", "king.txt", "rules.txt", "library.txt", "welcome.txt"]

    def __init__(self, disk_client: YandexDiskClient, config: Dict[str, Any]):
        """
        Инициализация менеджера профилей.

        Args:
            disk_client: Клиент для работы с Яндекс.Диском
            config: Конфигурация с информацией о профилях
        """
        self.disk = disk_client
        self.config = config
        self.profiles = config.get("profiles", [])
        logger.info(f"ProfileManager initialized with {len(self.profiles)} profiles")

    def get_all_profiles(self) -> List[ProfileDict]:
        """Возвращает список всех доступных профилей"""
        return self.profiles

    def get_profile_files(self, profile_name: str) -> FilesDict:
        """
        Читает ВСЕ файлы профиля с Яндекс.Диска с защитой от ошибок.

        Если какой-то файл не читается (бинарный, кривая кодировка) —
        возвращается пустая строка, но остальные файлы загружаются.

        Returns:
            Словарь с содержимым файлов: key, king, rules, library, welcome
        """
        files = {}

        for file_name in self.PROFILE_FILES:
            key = file_name.replace('.txt', '')
            try:
                path = f"{profile_name}/{file_name}"
                content = self.disk.read_file(path)

                if content:
                    files[key] = content
                    logger.debug(f"Loaded {file_name}: {len(content)} chars")
                else:
                    files[key] = ""
                    logger.warning(f"File {file_name} is empty")

            except UnicodeDecodeError as e:
                # Критично: файл не в UTF-8 (скорее всего бинарный)
                logger.error(f"Failed to read {file_name}: encoding error - {e}")
                files[key] = ""  # Пустая строка вместо падения

            except Exception as e:
                # Любая другая ошибка
                logger.error(f"Failed to read {file_name}: {e}")
                files[key] = ""

        # Логируем итог
        loaded = [k for k, v in files.items() if v]
        empty = [k for k, v in files.items() if not v]
        logger.info(f"Profile {profile_name}: loaded {loaded}, empty {empty}")

        return files

    def build_context(self, profile_name: str, limit: int = 10) -> str:
        """
        Собирает полный контекст для DeepSeek:
        - king.txt (личность)
        - rules.txt (правила)
        - library.txt (опыт/знания)
        - последние N сообщений из логов

        Args:
            profile_name: Имя профиля
            limit: Сколько последних сообщений брать

        Returns:
            Полный текст контекста
        """
        files = self.get_profile_files(profile_name)

        parts = []

        # Личность
        if files.get('king'):
            parts.append(f"ТЫ — ЛИЧНОСТЬ:\n{files['king']}\n")

        # Правила
        if files.get('rules'):
            parts.append(f"ПРАВИЛА ОБЩЕНИЯ:\n{files['rules']}\n")

        # Опыт/знания
        if files.get('library'):
            parts.append(f"ТВОИ ЗНАНИЯ И ОПЫТ:\n{files['library']}\n")

        # Последние сообщения
        recent = self.get_recent_messages(profile_name, limit)
        if recent:
            parts.append(f"ПОСЛЕДНИЕ СООБЩЕНИЯ В ЧАТЕ:\n{recent}\n")

        return "\n".join(parts)

    def save_message(self, profile_name: str, role: str, text: str, timestamp: datetime):
        """
        Сохраняет сообщение в лог профиля.

        Формат файла: /profiles/{profile_name}/logs/YYYY/MM/DD/log.txt
        Формат записи: [timestamp] role: текст

        Args:
            profile_name: Имя профиля
            role: Роль (user, assistant, system)
            text: Текст сообщения
            timestamp: Время сообщения
        """
        try:
            # Путь вида: Logan/logs/2026/02/17/log.txt
            date_path = timestamp.strftime("%Y/%m/%d")
            log_path = f"{profile_name}/logs/{date_path}/log.txt"

            # ⭐ СОЗДАЁМ ПАПКИ, ЕСЛИ ИХ НЕТ
            folder_path = f"{profile_name}/logs/{date_path}"
            self.disk.ensure_folder_exists(folder_path)

            # Форматируем запись
            time_str = timestamp.strftime("%H:%M:%S")
            log_entry = f"[{time_str}] {role}: {text}\n"

            # Пишем в файл (дозаписываем в конец)
            success = self.disk.append_to_file(log_path, log_entry)

            if success:
                logger.debug(f"Message saved to {log_path}")
            else:
                logger.error(f"Failed to save message to {log_path}")

        except Exception as e:
            logger.error(f"Failed to save message: {e}")

    def get_recent_messages(self, profile_name: str, limit: int = 10) -> str:
        """
        Читает последние сообщения из лога профиля.

        Сначала пытается читать сегодняшний лог,
        если его нет — вчерашний.

        Args:
            profile_name: Имя профиля
            limit: Сколько последних сообщений вернуть

        Returns:
            Строка с последними сообщениями
        """
        today = datetime.now()
        yesterday = datetime.now().replace(day=today.day - 1)

        # Пробуем сегодня
        date_path = today.strftime("%Y/%m/%d")
        log_path = f"{profile_name}/logs/{date_path}/log.txt"
        content = self.disk.read_file(log_path)

        # Если сегодня нет — пробуем вчера
        if not content:
            date_path = yesterday.strftime("%Y/%m/%d")
            log_path = f"{profile_name}/logs/{date_path}/log.txt"
            content = self.disk.read_file(log_path)

        if not content:
            return ""

        # Берём последние limit строк
        lines = content.strip().split('\n')
        last_lines = lines[-limit:] if len(lines) > limit else lines

        return '\n'.join(last_lines)

    def add_to_library(self, profile_name: str, text: str) -> bool:
        """
        Добавляет текст в library.txt профиля.

        Args:
            profile_name: Имя профиля
            text: Текст для добавления

        Returns:
            True если успешно, False если ошибка
        """
        try:
            path = f"{profile_name}/library.txt"

            # Добавляем с временной меткой
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            entry = f"\n\n[{timestamp}] ДОБАВЛЕНО:\n{text}"

            success = self.disk.append_to_file(path, entry)

            if success:
                logger.info(f"Added to library for {profile_name}")
                return True
            else:
                logger.error(f"Failed to add to library for {profile_name}")
                return False

        except Exception as e:
            logger.error(f"Error adding to library: {e}")
            return False