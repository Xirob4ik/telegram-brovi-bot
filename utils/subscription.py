"""
Утилиты для проверки подписки на канал
"""
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from config import CHANNEL_ID
import logging

logger = logging.getLogger(__name__)


async def check_user_subscription(bot: Bot, user_id: int) -> bool:
    """
    Проверка подписки пользователя на канал
    Возвращает True если пользователь подписан
    """
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        status = member.status
        # Разрешённые статусы
        return status in ["member", "administrator", "creator"]
    except TelegramBadRequest as e:
        # Если бот не админ в канале - не можем проверить подписку
        logger.warning(f"Бот не является администратором канала {CHANNEL_ID}, проверка подписки невозможна: {e}")
        # Возвращаем True чтобы не блокировать работу бота
        return True
    except Exception as e:
        # Любые другие ошибки - тоже считаем что пользователь подписан
        logger.warning(f"Ошибка при проверке подписки: {e}. Считаем что пользователь подписан.")
        return True