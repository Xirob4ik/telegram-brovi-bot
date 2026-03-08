"""
Middleware для проверки подписки на канал
"""
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable, Union
import logging
import config

logger = logging.getLogger(__name__)


class SubscriptionMiddleware(BaseMiddleware):
    """Middleware для проверки обязательной подписки"""
    
    def __init__(self):
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[Union[Message, CallbackQuery], Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery],
        data: Dict[str, Any]
    ) -> Any:
        # Если канал не настроен, пропускаем все запросы
        if not config.CHANNEL_ID or config.CHANNEL_ID == "YOUR_CHANNEL_ID":
            return await handler(event, data)
        
        user_id = event.from_user.id
        
        # Проверяем подписку
        is_subscribed = await self.check_subscription(user_id)
        
        if not is_subscribed:
            # Если это не команда /start и не сообщение о подписке, блокируем
            if isinstance(event, Message):
                if event.text and (event.text.startswith('/start') or event.text == '✅ Я подписался'):
                    return await handler(event, data)
                try:
                    await event.answer(
                        f"❌ Для использования бота необходимо подписаться на наш канал:\n\n"
                        f"https://t.me/{config.CHANNEL_USERNAME}\n\n"
                        f"После подписки нажмите /start",
                        show_alert=True
                    )
                except:
                    pass
                return
            elif isinstance(event, CallbackQuery):
                if event.data != "check_subscription":
                    try:
                        await event.answer(
                            "❌ Сначала подпишитесь на канал!",
                            show_alert=True
                        )
                    except:
                        pass
                    return
        
        return await handler(event, data)
    
    async def check_subscription(self, user_id: int) -> bool:
        """Проверка подписки пользователя на канал"""
        from aiogram import Bot
        from aiogram.exceptions import TelegramForbiddenError
        
        bot = Bot(token=config.BOT_TOKEN)
        
        try:
            member = await bot.get_chat_member(config.CHANNEL_ID, user_id)
            # Проверяем статус участника
            return member.status in ['member', 'administrator', 'creator']
        except TelegramForbiddenError:
            logger.warning(f"Бот заблокирован пользователем {user_id}")
            return False
        except Exception as e:
            # Если бот не админ канала или другая ошибка - считаем что пользователь подписан
            # чтобы не блокировать работу бота
            logger.error(f"Ошибка проверки подписки: {e}")
            return True
        finally:
            await bot.session.close()
