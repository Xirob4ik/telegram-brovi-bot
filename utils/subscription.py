"""
Утилиты для проверки подписки на канал
"""
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from config import CHANNEL_ID


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
    except TelegramBadRequest:
        # Канал приватный или бот не админ
        return False
    except Exception:
        return False