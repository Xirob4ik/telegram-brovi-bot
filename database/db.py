"""
Управление подключением к базе данных SQLite
"""
import aiosqlite
from pathlib import Path
from contextlib import asynccontextmanager
from config import DATABASE_PATH


@asynccontextmanager
async def get_db():
    """Получить подключение к базе данных (контекстный менеджер)"""
    Path(DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    """Инициализация базы данных: создание таблиц и дефолтных данных"""
    from .models import create_tables, add_default_services
    
    async with get_db() as db:
        await create_tables(db)
        await add_default_services(db)
        await db.commit()