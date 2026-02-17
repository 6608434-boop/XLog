import os
import yadisk
from pathlib import Path
from datetime import datetime
from typing import Optional
import tempfile

from .logger import logger

# Пытаемся импортировать определение кодировки
try:
    from charset_normalizer import from_bytes

    CHARSET_DETECT_AVAILABLE = True
    logger.info("charset-normalizer loaded successfully")
except ImportError:
    CHARSET_DETECT_AVAILABLE = False
    logger.warning("charset-normalizer not installed, using fallback encoding detection")


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

    def ensure_folder_exists(self, remote_path: str) -> bool:
        """
        Убеждается, что папка существует. Если нет — создаёт все промежуточные папки.

        Args:
            remote_path: Путь к папке на Яндекс.Диске (относительно корня)

        Returns:
            True если папка существует или была создана
        """
        full_path = f"/{self.root_folder}/{remote_path}"
        try:
            # Разбиваем путь на части и создаём каждую папку по очереди
            current_path = f"/{self.root_folder}"
            parts = remote_path.split('/')

            for part in parts:
                if not part:  # Пропускаем пустые части
                    continue
                current_path += f"/{part}"
                if not self.client.exists(current_path):
                    self.client.mkdir(current_path)
                    logger.debug(f"Created directory: {current_path}")

            return True

        except Exception as e:
            logger.error(f"Failed to ensure folder {full_path}: {e}")
            return False

    def ensure_path(self, path: str) -> bool:
        """
        Убеждается, что папка существует. Если нет — создаёт её.
        Оставлено для обратной совместимости.

        Args:
            path: Путь к папке на Яндекс.Диске

        Returns:
            True если папка существует или была создана
        """
        return self.ensure_folder_exists(path)

    def get_daily_log_path(self, profile_name: str, date: datetime) -> str:
        """
        Формирует путь к файлу лога за указанную дату.

        Returns:
            Полный путь к файлу лога
        """
        # XLog/Profile/logs/YYYY/MM/DD/log.txt
        return f"{profile_name}/logs/{date.year}/{date.month:02d}/{date.day:02d}/log.txt"

    def append_to_file(self, remote_path: str, content: str) -> bool:
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
            # Убеждаемся, что папка для файла существует
            folder_path = '/'.join(remote_path.split('/')[:-1])
            if folder_path:
                self.ensure_folder_exists(folder_path)

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

            logger.debug(f"Appended to {full_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to append to {full_path}: {e}")
            return False

        finally:
            # Удаляем временный файл
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)

    def write_to_file(self, remote_path: str, content: str) -> bool:
        """
        Записывает содержимое в файл (перезаписывает).

        Args:
            remote_path: Путь к файлу на Яндекс.Диске (относительно корня)
            content: Текст для записи

        Returns:
            True если успешно
        """
        full_path = f"/{self.root_folder}/{remote_path}"
        temp_file = None

        try:
            # Убеждаемся, что папка для файла существует
            folder_path = '/'.join(remote_path.split('/')[:-1])
            if folder_path:
                self.ensure_folder_exists(folder_path)

            # Создаём временный файл
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', delete=False) as tf:
                temp_file = tf.name
                tf.write(content)
                tf.flush()

            # Загружаем на Диск
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
        АВТОМАТИЧЕСКИ определяет кодировку через charset-normalizer.

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

            # Скачиваем файл как БАЙТЫ (не пытаемся декодировать)
            with tempfile.NamedTemporaryFile(mode='rb', delete=False) as tf:
                temp_file = tf.name
                self.client.download(full_path, temp_file)

            # Читаем байты из временного файла
            with open(temp_file, 'rb') as f:
                raw_data = f.read()

            # Пробуем определить кодировку
            if CHARSET_DETECT_AVAILABLE and raw_data:
                try:
                    result = from_bytes(raw_data).best()

                    if result:
                        encoding = result.encoding
                        content = str(result)
                        logger.info(
                            f"✅ Auto-detected encoding for {remote_path}: {encoding} (confidence: {result.quality})")

                        # Убираем BOM если есть (на всякий случай)
                        if content and content.startswith('\ufeff'):
                            content = content[1:]

                        return content
                    else:
                        logger.warning(f"Charset detection failed for {remote_path}, trying fallback")
                        return self._fallback_decode(raw_data, remote_path)
                except Exception as e:
                    logger.warning(f"Error in charset detection: {e}, using fallback")
                    return self._fallback_decode(raw_data, remote_path)
            else:
                # Если библиотека не установлена — используем старый метод
                logger.debug(f"Using fallback decoder for {remote_path}")
                return self._fallback_decode(raw_data, remote_path)

        except Exception as e:
            logger.error(f"Failed to read {full_path}: {e}")
            return None

        finally:
            if temp_file and os.path.exists(temp_file):
                os.unlink(temp_file)

    def _fallback_decode(self, raw_data: bytes, remote_path: str) -> Optional[str]:
        """
        Запасной метод с перебором кодировок (если нет charset-normalizer)
        """
        encodings = ['utf-8', 'windows-1251', 'koi8-r', 'cp866', 'iso-8859-5']

        for encoding in encodings:
            try:
                content = raw_data.decode(encoding)
                # Проверяем, что результат похож на текст
                if self._looks_like_text(content):
                    logger.info(f"Fallback: {remote_path} decoded as {encoding}")

                    # Убираем BOM если есть
                    if content and content.startswith('\ufeff'):
                        content = content[1:]

                    return content
            except UnicodeDecodeError:
                continue

        # Если ничего не помогло — пробуем с игнорированием ошибок
        try:
            content = raw_data.decode('utf-8', errors='ignore')
            logger.warning(f"Fallback: {remote_path} decoded with errors='ignore'")
            return content
        except:
            logger.error(f"Failed to decode {remote_path} with any method")
            return None

    def _looks_like_text(self, text: str) -> bool:
        """
        Простая эвристика: проверяем, что текст похож на нормальный русский/английский
        """
        if not text or len(text) < 10:
            return True

        # Считаем долю нормальных символов
        good_chars = 0
        total_chars = 0

        for ch in text[:1000]:  # Проверяем только первые 1000 символов
            total_chars += 1
            # Буквы, цифры, пробелы, знаки препинания
            if ch.isalpha() or ch.isdigit() or ch.isspace() or ch in ',.!?-;:"()[]{}':
                good_chars += 1
            # Русские буквы в UTF-8 (диапазон)
            elif '\u0400' <= ch <= '\u04FF':  # Кириллица
                good_chars += 1

        if total_chars == 0:
            return True

        ratio = good_chars / total_chars
        return ratio > 0.6  # Допускаем до 40% "странных" символов

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