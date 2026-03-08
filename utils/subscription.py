from aiogram import types
from config import CHANNEL_ID
import logging

logger = logging.getLogger(__name__)

async def check_subscription(user_id: int, bot) -> bool:
    """
    Проверка подписки пользователя на канал.
    Если бот не админ в канале или произошла ошибка - возвращаем True,
    чтобы не блокировать работу бота.
    """
    try:
        if not CHANNEL_ID or CHANNEL_ID == "your_channel_id":
            # Канал не настроен, пропускаем проверку
            return True
            
        member = await bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        
        # Проверяем статус участника
        if member.status in ['member', 'administrator', 'creator']:
            return True
        
        return False
        
    except Exception as e:
        # Если произошла ошибка (бот не админ, канал не найден и т.д.)
        #_logгируем ошибку и возвращаем True, чтобы не блокировать пользователя
        logger.warning(f"Ошибка проверки подписки для пользователя {user_id}: {e}")
        logger.warning("Проверка подписки пропущена. Убедитесь что бот является администратором канала.")
        return True

async def get_subscription_status(user_id: int, bot) -> str:
    """Возвращает статус подписки для отображения пользователю"""
    is_subscribed = await check_subscription(user_id, bot)
    if is_subscribed:
        return "✅ Вы подписаны на наш канал"
    else:
        return "❌ Вы не подписаны на наш канал"
