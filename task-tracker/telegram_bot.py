#!/usr/bin/env python3
"""
EngSpring Telegram Bot
Handles user notifications and account binding
"""
import os
import logging
import requests
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Configuration
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
API_BASE_URL = os.environ.get('API_BASE_URL', 'http://localhost:5000')

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is required")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /start command
    Usage: /start [binding_code]
    """
    user = update.effective_user
    chat_id = update.effective_chat.id

    # Check if binding code was provided
    if context.args:
        binding_code = context.args[0].strip().upper()
        await bind_account(update, context, binding_code)
    else:
        # No code provided - send welcome message
        await update.message.reply_text(
            f"👋 Привет, {user.first_name}!\n\n"
            f"Я бот EngSpring для управления занятиями и уведомлений.\n\n"
            f"**Как привязать аккаунт:**\n"
            f"1. Зайдите на сайт EngSpring\n"
            f"2. Откройте Настройки → Telegram\n"
            f"3. Нажмите 'Сгенерировать код'\n"
            f"4. Отправьте мне команду: `/start КОД`\n\n"
            f"**Доступные команды:**\n"
            f"/help - Помощь\n"
            f"/status - Статус привязки",
            parse_mode='Markdown'
        )


async def bind_account(update: Update, context: ContextTypes.DEFAULT_TYPE, code: str):
    """
    Bind Telegram account to EngSpring account using the code
    """
    user = update.effective_user
    telegram_id = str(user.id)
    telegram_username = user.username or ""

    await update.message.reply_text("⏳ Привязываю аккаунт...")

    try:
        # Call Flask API to bind the account
        response = requests.post(
            f"{API_BASE_URL}/api/telegram/bind",
            json={
                "code": code,
                "telegram_id": telegram_id,
                "telegram_username": telegram_username
            },
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                user_info = data.get('user', {})
                await update.message.reply_text(
                    f"✅ Аккаунт успешно привязан!\n\n"
                    f"**Пользователь:** {user_info.get('display_name', 'N/A')}\n"
                    f"**Логин:** {user_info.get('username', 'N/A')}\n\n"
                    f"Теперь вы будете получать уведомления о занятиях и домашних заданиях.",
                    parse_mode='Markdown'
                )
                logger.info(f"Account bound: telegram_id={telegram_id}, user_id={user_info.get('id')}")
            else:
                await update.message.reply_text(
                    f"❌ Ошибка привязки: {data.get('error', 'Unknown error')}"
                )
        else:
            error_data = response.json()
            await update.message.reply_text(
                f"❌ Ошибка привязки: {error_data.get('error', 'Unknown error')}"
            )
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {e}")
        await update.message.reply_text(
            "❌ Ошибка соединения с сервером. Попробуйте позже."
        )
    except Exception as e:
        logger.error(f"Binding failed: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка. Попробуйте позже."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /help command
    """
    await update.message.reply_text(
        "**EngSpring Bot - Помощь**\n\n"
        "**Команды:**\n"
        "/start [КОД] - Привязать аккаунт\n"
        "/status - Проверить статус привязки\n"
        "/help - Показать эту справку\n\n"
        "**Привязка аккаунта:**\n"
        "1. Зайдите на сайт EngSpring\n"
        "2. Настройки → Telegram\n"
        "3. Сгенерируйте код\n"
        "4. Отправьте: `/start КОД`\n\n"
        "**Поддержка:** @your_support_username",
        parse_mode='Markdown'
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /status command - check if user is bound
    """
    user = update.effective_user
    telegram_id = str(user.id)

    # TODO: Add API endpoint to check binding status by telegram_id
    # For now, just show a placeholder message
    await update.message.reply_text(
        f"**Ваш Telegram ID:** `{telegram_id}`\n\n"
        f"Для проверки статуса привязки зайдите на сайт EngSpring в раздел Настройки → Telegram",
        parse_mode='Markdown'
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Log errors caused by updates
    """
    logger.error(f"Update {update} caused error {context.error}")


def main():
    """
    Start the bot
    """
    logger.info("Starting EngSpring Telegram Bot...")

    # Create application
    application = Application.builder().token(BOT_TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))

    # Register error handler
    application.add_error_handler(error_handler)

    # Start the bot
    logger.info("Bot started. Polling for updates...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
