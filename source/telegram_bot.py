"""
Telegram бот для XLog — общение с множеством профилей (Логан, Марк, Вера и др.)
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

from .logger import logger
from .profile_manager import ProfileManager
from .deepseek_client import DeepSeekClient
from .yadisk_client import YandexDiskClient

# Словарь для хранения активного профиля каждого пользователя
# В продакшене лучше использовать Redis или БД, но для начала сойдёт
user_profiles = {}


class TelegramBot:
    def __init__(self, token: str, profiles: ProfileManager, deepseek: DeepSeekClient):
        """
        Инициализация Telegram бота.

        Args:
            token: Токен от BotFather
            profiles: Менеджер профилей
            deepseek: Клиент DeepSeek API
        """
        self.token = token
        self.profiles = profiles
        self.deepseek = deepseek
        self.application = None

        # Список доступных профилей (из конфига)
        self.available_profiles = [p["name"] for p in profiles.get_all_profiles()]

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        user_name = update.effective_user.first_name

        logger.info(f"User {user_id} ({user_name}) started the bot")

        welcome_text = (
            f"👋 Привет, {user_name}! Я бот Xscope.\n\n"
            f"Я могу общаться от имени разных профилей: {', '.join(self.available_profiles)}.\n\n"
            f"Используй /profile чтобы выбрать профиль, или просто начни печатать."
        )

        # Создаём клавиатуру для быстрого выбора профиля
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f"profile_{name}")]
            for name in self.available_profiles
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /profile - выбор профиля"""
        keyboard = [
            [InlineKeyboardButton(name, callback_data=f"profile_{name}")]
            for name in self.available_profiles
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "Выбери профиль для общения:",
            reply_markup=reply_markup
        )

    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /list - список профилей"""
        profiles_list = "\n".join([f"• {name}" for name in self.available_profiles])
        await update.message.reply_text(
            f"📋 Доступные профили:\n{profiles_list}\n\n"
            f"Используй /profile чтобы выбрать."
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = (
            "🤖 **Xscope Bot Help**\n\n"
            "**Команды:**\n"
            "/start - Запуск бота\n"
            "/profile - Выбрать профиль\n"
            "/list - Список профилей\n"
            "/help - Эта справка\n\n"
            "**Как общаться:**\n"
            "1. Выбери профиль через /profile\n"
            "2. Просто пиши сообщения\n"
            "3. Бот ответит от имени выбранного профиля\n\n"
            "**Доступные профили:**\n"
            f"{', '.join(self.available_profiles)}"
        )
        await update.message.reply_text(help_text, parse_mode='Markdown')

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатий на кнопки"""
        query = update.callback_query
        await query.answer()

        user_id = update.effective_user.id
        data = query.data

        if data.startswith("profile_"):
            profile_name = data.replace("profile_", "")

            # Сохраняем выбранный профиль для пользователя
            user_profiles[user_id] = profile_name

            logger.info(f"User {user_id} selected profile: {profile_name}")

            # Загружаем приветствие из welcome.txt, если есть
            files = self.profiles.get_profile_files(profile_name)
            welcome_text = files.get('welcome')

            if not welcome_text:
                welcome_text = f"✅ Выбран профиль **{profile_name}**. Теперь общаюсь от его имени."

            await query.edit_message_text(
                f"✅ Активен профиль: **{profile_name}**\n\n{welcome_text}",
                parse_mode='Markdown'
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик обычных текстовых сообщений"""
        user_id = update.effective_user.id
        user_message = update.message.text

        # Проверяем, выбран ли профиль
        if user_id not in user_profiles:
            await update.message.reply_text(
                "❓ Сначала выбери профиль с помощью команды /profile"
            )
            return

        profile_name = user_profiles[user_id]

        logger.info(f"User {user_id} ({profile_name}): {user_message[:50]}...")

        # Показываем, что бот печатает
        await update.message.chat.send_action(action="typing")

        try:
            # Загружаем историю для контекста (последние сообщения из Яндекс.Диска)
            # TODO: загрузить последние N сообщений из логов профиля

            # Отправляем в DeepSeek
            response_data = self.deepseek.send_message(
                chat_id=profile_name,  # используем имя профиля как chat_id
                message=user_message,
                history=[]  # пока без истории
            )

            if response_data and response_data.get("content"):
                assistant_message = response_data["content"]

                # Сохраняем сообщения в Яндекс.Диск
                from datetime import datetime
                self.profiles.save_message(profile_name, "user", user_message, datetime.now())
                self.profiles.save_message(profile_name, "assistant", assistant_message, datetime.now())

                # Отправляем ответ
                await update.message.reply_text(assistant_message)

                logger.info(f"Response sent to user {user_id}")
            else:
                await update.message.reply_text("❌ Ошибка при получении ответа от DeepSeek")

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")

    def run(self):
        """Запуск бота"""
        # Создаём приложение
        self.application = Application.builder().token(self.token).build()

        # Добавляем обработчики команд
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("profile", self.profile_command))
        self.application.add_handler(CommandHandler("list", self.list_command))
        self.application.add_handler(CommandHandler("help", self.help_command))

        # Обработчик кнопок
        self.application.add_handler(CallbackQueryHandler(self.button_callback))

        # Обработчик текстовых сообщений
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))

        logger.info("Telegram bot started. Press Ctrl+C to stop.")

        # Запускаем бота
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)