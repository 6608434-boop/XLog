import os
import yadisk
from pathlib import Path
from datetime import datetime
from typing import Optional
import tempfile

from .logger import logger


class YandexDiskClient:
    def __init__(self, token: str, root_folder: str = "XLog"):
        """
        Инициализация клиента Яндекс.Диска.

        Args:
            token: OAuth-токен для доступа к Диску
            root_folder: Корневая папка проекта на Диске
        """
        self.client = yadisk.Client(token=token)
        self.root_folder = root_folder

        # Проверяем, что токен рабочий
        if not self.client.check_token():
            logger.error("Invalid Yandex Disk token")
            raise ValueError("Invalid Yandex Disk token")

        logger.info("Connected to Yandex Disk")

    def ensure_path(self, path: str) -> bool:
        """
        Убеждается, что папка существует. Если нет — создаёт её.

        Args:
            path: Путь к папке на Яндекс.Диске

        Returns:
            True если папка существует или была создана
        """
        full_path = f"/{self.root_folder}/{path}"
        try:
            if not self.client.exists(full_path):
                self.client.mkdir(full_path)
                logger.debug(f"Created directory: {full_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to ensure path {full_path}: {e}")
            return False

    def get_daily_log_path(self, profile_name: str, date: datetime) -> str:
        """
        Формирует путь к файлу лога за указанную дату.

        Returns:
            Полный путь к файлу лога
        """
        # XLog/Profile/logs/YYYY/MM/DD/log.txt
        return f"{profile_name}/logs/{date.year}/{date.month:02d}/{date.day:02d}/log.txt"

    def write_to_file(self, remote_path: str, content: str) -> bool:
        """
        Дописывает содержимое в конец файла.

        Args:
            remote_path: Путь к файлу на Яндекс.Диске (относительно корня)
            content: Текст для добавления

        Returns:
            True если успешно
        """
        full_path = f"/{self.root_folder}/{remote_path}"
        temp_file = None

        try:
            # Создаём временный файл
            with tempfile.NamedTemporaryFile(mode='w+', encoding='utf-8', delete=False) as tf:
                temp_file = tf.name

                # Если файл существует на Диске — скачиваем
                if self.client.exists(full_path):
                    self.client.download(full_path, temp_file)

                # Дописываем новое содержимое
                with open(temp_file, 'a', encoding='utf-8') as f:
                    f.write(content)

                # Загружаем обратно на Диск
                self.client.upload(temp_file, full_path, overwrite=True)

            logger.debug(f"Written to {full_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to write to {full_path}: {e}")
            return False

        finally:
            # Удаляем временный файл
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)

    def read_file(self, remote_path: str) -> Optional[str]:
        """
        Читает содержимое файла с Яндекс.Диска.

        Args:
            remote_path: Путь к файлу на Яндекс.Диске (относительно корня)

        Returns:
            Содержимое файла или None
        """
        full_path = f"/{self.root_folder}/{remote_path}"
        temp_file = None

        try:
            if not self.client.exists(full_path):
                return None

            with tempfile.NamedTemporaryFile(mode='r', encoding='utf-8', delete=False) as tf:
                temp_file = tf.name
                self.client.download(full_path, temp_file)

            with open(temp_file, 'r', encoding='utf-8') as f:
                content = f.read()

            return content

        except Exception as e:
            logger.error(f"Failed to read {full_path}: {e}")
            return None

        finally:
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)

    def list_files(self, remote_path: str) -> list:
        """
        Возвращает список файлов в папке.

        Args:
            remote_path: Путь к папке на Яндекс.Диске (относительно корня)

        Returns:
            Список имён файлов
        """
        full_path = f"/{self.root_folder}/{remote_path}"
        try:
            if not self.client.exists(full_path):
                return []
            return [item.name for item in self.client.listdir(full_path)]
        except Exception as e:
            logger.error(f"Failed to list {full_path}: {e}")
            return []