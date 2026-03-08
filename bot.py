from aiogram import Dispatcher, Bot
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters import Text
import logging
import config
import models
from handlers.user_handlers import register_handlers

logging.basicConfig(level=logging.INFO)

storage = MemoryStorage()
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(bot, storage=storage)

# Initialize database
models.init_db()

# Register all handlers
register_handlers(dp)

async def on_startup(dispatcher):
    logging.info("Bot started successfully!")

async def on_shutdown(dispatcher):
    logging.info("Bot shutting down...")
    await bot.close()

if __name__ == '__main__':
    from aiogram import executor
    executor.start_polling(
        dp,
        skip_updates=True,
        on_startup=on_startup,
        on_shutdown=on_shutdown
    )
