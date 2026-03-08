import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
import config
from database.db import init_db
from handlers.user_handlers import register_handlers
from middlewares.subscription import SubscriptionMiddleware

logging.basicConfig(level=logging.INFO)

async def main():
    # Initialize bot and dispatcher
    storage = MemoryStorage()
    bot = Bot(
        token=config.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=storage)
    
    # Initialize database
    await init_db()
    
    # Setup middleware for subscription check
    dp.message.middleware(SubscriptionMiddleware())
    dp.callback_query.middleware(SubscriptionMiddleware())
    
    # Register all handlers
    register_handlers(dp)
    
    # Start polling
    logging.info("Bot started successfully!")
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot stopped by user")
