#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
================================================================================
ФАЙЛ: deepseek_client.py
НАЗНАЧЕНИЕ: Клиент для DeepSeek API
АВТОР: Логан
ДАТА: 2026-02-17
ВЕРСИЯ: 2.0 (с поддержкой истории)
================================================================================
"""

import requests
import time
from typing import List, Dict, Optional, Any

from .logger import logger


class DeepSeekClient:
    def __init__(self, api_key: str):
        """
        Инициализация клиента DeepSeek API.

        Args:
            api_key: API ключ с platform.deepseek.com
        """
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        logger.info("DeepSeek client initialized")

    def send_message(self, chat_id: str, message: str, history: List[Dict] = None) -> Optional[Dict[str, Any]]:
        """
        Отправляет сообщение в чат и получает ответ.

        Args:
            chat_id: ID чата (используется для логирования)
            message: Текст сообщения
            history: История предыдущих сообщений (если есть)

        Returns:
            Ответ от API или None в случае ошибки
        """
        # Подготавливаем messages
        messages = []

        # Сначала добавляем историю (системные сообщения, контекст)
        if history:
            messages.extend(history)

        # Добавляем текущее сообщение пользователя
        messages.append({"role": "user", "content": message})

        payload = {
            "model": "deepseek-chat",
            "messages": messages,
            "stream": False
        }

        logger.info(f"Sending message to chat {chat_id}")
        logger.debug(f"Messages count: {len(messages)}")

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=30
            )

            logger.info(f"Response status code: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                logger.info("Message sent successfully")

                # Извлекаем ответ ассистента
                assistant_message = data.get("choices", [{}])[0].get("message", {})
                return {
                    "id": data.get("id"),
                    "role": "assistant",
                    "content": assistant_message.get("content", ""),
                    "created": data.get("created")
                }
            else:
                logger.error(f"Failed to send message: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            if hasattr(e, 'response') and e.response:
                logger.error(f"Response body: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return None

    def get_new_messages(self, chat_id: str, last_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Заглушка для совместимости."""
        logger.warning("get_new_messages is deprecated")
        return []

    def get_chat_history(self, chat_id: str, last_id: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        """Заглушка для совместимости."""
        logger.warning("get_chat_history is deprecated")
        return []

    def get_all_history(self, chat_id: str) -> List[Dict[str, Any]]:
        """Заглушка для совместимости."""
        logger.warning("get_all_history is deprecated")
        return []