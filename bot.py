#!/usr/bin/env python3
"""
Telegram-бот для записи к бровисту
aiogram 3.x + SQLite + APScheduler
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN, ADMIN_ID
from database import init_db
from scheduler import init_scheduler, restore_reminders
from handlers import (
    start_router,
    booking_router,
    admin_router,
    prices_router,
    portfolio_router,
    cancel_router
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    logger.info("🚀 Бот запускается...")
    
    await init_db()
    logger.info("✅ База данных инициализирована")
    
    init_scheduler()
    
    await restore_reminders(bot)
    logger.info("✅ Напоминания восстановлены")
    
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text="🟢 <b>Бот запущен</b>",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.warning(f"⚠️ Не удалось отправить уведомление о запуске: {e}")


async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    logger.info("🛑 Бот останавливается...")
    
    from scheduler import scheduler
    if scheduler.running:
        scheduler.shutdown()
        logger.info("✅ APScheduler остановлен")
    
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text="🔴 <b>Бот остановлен</b>",
            parse_mode="HTML"
        )
    except Exception:
        pass


async def main():
    """Точка входа"""
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрируем роутеры в диспетчере
    dp.include_router(start_router)
    dp.include_router(booking_router)
    dp.include_router(admin_router)
    dp.include_router(prices_router)
    dp.include_router(portfolio_router)
    dp.include_router(cancel_router)
    
    # Регистрируем хуки запуска/остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Запускаем polling
    logger.info("🎯 Запускаем polling...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Остановка по Ctrl+C")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}", exc_info=True)