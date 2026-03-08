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
    except Exception as e:
        # Если бот не админ в канале или канал приватный - считаем что пользователь подписан
        # чтобы не блокировать работу бота
        import logging
        logging.warning(f"Не удалось проверить подписку: {e}. Считаем что пользователь подписан.")
        return True