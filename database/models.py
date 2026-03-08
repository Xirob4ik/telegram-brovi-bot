"""
Модели базы данных и функции работы с ними
"""
import aiosqlite
from datetime import datetime, timedelta
from typing import Optional, List
import logging


async def create_tables(db: aiosqlite.Connection):
    """Создание всех таблиц"""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            name TEXT,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            price INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            is_available INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(date, time)
        )
    """)
    
    await db.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            service_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            reminder_job_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (telegram_id),
            FOREIGN KEY (service_id) REFERENCES services (id)
        )
    """)
    
    await db.execute("CREATE INDEX IF NOT EXISTS idx_slots_date ON slots(date)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(date, time)")


async def add_default_services(db: aiosqlite.Connection):
    """Добавление услуг по умолчанию если их нет"""
    default_services = [
        ("Коррекция бровей", 700),
        ("Окрашивание бровей", 900),
        ("Ламинирование бровей", 1500),
    ]
    
    for name, price in default_services:
        await db.execute(
            "INSERT OR IGNORE INTO services (name, price) VALUES (?, ?)",
            (name, price)
        )


# ==================== USERS ====================

async def get_user(db: aiosqlite.Connection, telegram_id: int) -> Optional[dict]:
    """Получить пользователя по telegram_id"""
    cursor = await db.execute(
        "SELECT * FROM users WHERE telegram_id = ?",
        (telegram_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def create_user(db: aiosqlite.Connection, telegram_id: int, name: str = None, phone: str = None):
    """Создать или обновить пользователя"""
    await db.execute(
        """
        INSERT INTO users (telegram_id, name, phone) 
        VALUES (?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET 
            name = COALESCE(excluded.name, users.name),
            phone = COALESCE(excluded.phone, users.phone)
        """,
        (telegram_id, name, phone)
    )


async def update_user_phone(db: aiosqlite.Connection, telegram_id: int, phone: str):
    """Обновить телефон пользователя"""
    await db.execute(
        "UPDATE users SET phone = ? WHERE telegram_id = ?",
        (phone, telegram_id)
    )


# ==================== SERVICES ====================

async def get_all_services(db: aiosqlite.Connection) -> List[dict]:
    """Получить все услуги"""
    cursor = await db.execute("SELECT * FROM services ORDER BY name")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_service(db: aiosqlite.Connection, service_id: int) -> Optional[dict]:
    """Получить услугу по ID"""
    cursor = await db.execute(
        "SELECT * FROM services WHERE id = ?",
        (service_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def add_service(db: aiosqlite.Connection, name: str, price: int) -> int:
    """Добавить новую услугу, вернуть ID"""
    cursor = await db.execute(
        "INSERT INTO services (name, price) VALUES (?, ?)",
        (name, price)
    )
    await db.commit()
    return cursor.lastrowid


async def update_service(db: aiosqlite.Connection, service_id: int, name: str = None, price: int = None):
    """Обновить услугу"""
    if name and price:
        await db.execute(
            "UPDATE services SET name = ?, price = ? WHERE id = ?",
            (name, price, service_id)
        )
    elif name:
        await db.execute(
            "UPDATE services SET name = ? WHERE id = ?",
            (name, service_id)
        )
    elif price:
        await db.execute(
            "UPDATE services SET price = ? WHERE id = ?",
            (price, service_id)
        )


async def delete_service(db: aiosqlite.Connection, service_id: int):
    """Удалить услугу"""
    await db.execute("DELETE FROM services WHERE id = ?", (service_id,))


# ==================== SLOTS ====================

async def create_slot(db: aiosqlite.Connection, date: str, time: str) -> int:
    """Создать временной слот"""
    logging.info(f"Создание слота в БД: {date} {time}")
    try:
        cursor = await db.execute(
            "INSERT INTO slots (date, time, is_available) VALUES (?, ?, 1)",
            (date, time)
        )
        await db.commit()
        slot_id = cursor.lastrowid
        logging.info(f"Слот успешно создан с ID: {slot_id}")
        return slot_id
    except Exception as e:
        logging.error(f"Ошибка при создании слота: {e}")
        raise e


async def get_slot(db: aiosqlite.Connection, date: str, time: str) -> Optional[dict]:
    """Получить слот по дате и времени"""
    cursor = await db.execute(
        "SELECT * FROM slots WHERE date = ? AND time = ?",
        (date, time)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_available_slots(db: aiosqlite.Connection, date: str) -> List[dict]:
    """Получить все доступные слоты на дату"""
    cursor = await db.execute(
        "SELECT * FROM slots WHERE date = ? AND is_available = 1 ORDER BY time",
        (date,)
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def get_all_slots_by_date(db: aiosqlite.Connection, date: str) -> List[dict]:
    """Получить все слоты на дату (включая занятые)"""
    cursor = await db.execute(
        "SELECT * FROM slots WHERE date = ? ORDER BY time",
        (date,)
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def mark_slot_unavailable(db: aiosqlite.Connection, slot_id: int):
    """Пометить слот как занятый"""
    await db.execute(
        "UPDATE slots SET is_available = 0 WHERE id = ?",
        (slot_id,)
    )


async def mark_slot_available(db: aiosqlite.Connection, slot_id: int):
    """Пометить слот как свободный"""
    await db.execute(
        "UPDATE slots SET is_available = 1 WHERE id = ?",
        (slot_id,)
    )


async def delete_slot(db: aiosqlite.Connection, slot_id: int):
    """Удалить слот"""
    await db.execute("DELETE FROM slots WHERE id = ?", (slot_id,))


async def delete_slots_by_date(db: aiosqlite.Connection, date: str):
    """Удалить все слоты на дату"""
    await db.execute("DELETE FROM slots WHERE date = ?", (date,))


async def get_dates_with_available_slots(db: aiosqlite.Connection, start_date: str, end_date: str) -> List[str]:
    """Получить даты, на которые есть доступные слоты"""
    cursor = await db.execute(
        """
        SELECT DISTINCT date FROM slots 
        WHERE date >= ? AND date <= ? AND is_available = 1
        ORDER BY date
        """,
        (start_date, end_date)
    )
    rows = await cursor.fetchall()
    return [row[0] for row in rows]


# ==================== BOOKINGS ====================

async def create_booking(
    db: aiosqlite.Connection,
    user_id: int,
    service_id: int,
    date: str,
    time: str,
    reminder_job_id: str = None
) -> int:
    """Создать запись"""
    cursor = await db.execute(
        """
        INSERT INTO bookings (user_id, service_id, date, time, reminder_job_id)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, service_id, date, time, reminder_job_id)
    )
    await db.commit()
    return cursor.lastrowid


async def get_user_booking(db: aiosqlite.Connection, telegram_id: int) -> Optional[dict]:
    """Получить активную запись пользователя"""
    cursor = await db.execute(
        """
        SELECT b.*, s.name as service_name, s.price as service_price
        FROM bookings b
        JOIN services s ON b.service_id = s.id
        WHERE b.user_id = ?
        ORDER BY b.date, b.time
        LIMIT 1
        """,
        (telegram_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_booking_by_id(db: aiosqlite.Connection, booking_id: int) -> Optional[dict]:
    """Получить запись по ID"""
    cursor = await db.execute(
        """
        SELECT b.*, u.name as user_name, u.phone as user_phone, 
               s.name as service_name, s.price as service_price
        FROM bookings b
        JOIN users u ON b.user_id = u.telegram_id
        JOIN services s ON b.service_id = s.id
        WHERE b.id = ?
        """,
        (booking_id,)
    )
    row = await cursor.fetchone()
    return dict(row) if row else None


async def get_bookings_by_date(db: aiosqlite.Connection, date: str) -> List[dict]:
    """Получить все записи на дату"""
    cursor = await db.execute(
        """
        SELECT b.*, u.name as user_name, u.phone as user_phone,
               s.name as service_name, s.price as service_price
        FROM bookings b
        JOIN users u ON b.user_id = u.telegram_id
        JOIN services s ON b.service_id = s.id
        WHERE b.date = ?
        ORDER BY b.time
        """,
        (date,)
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


async def cancel_booking(db: aiosqlite.Connection, booking_id: int) -> Optional[dict]:
    """Отменить запись и вернуть информацию о ней"""
    booking = await get_booking_by_id(db, booking_id)
    if not booking:
        return None
    
    slot = await get_slot(db, booking['date'], booking['time'])
    if slot:
        await mark_slot_available(db, slot['id'])
    
    await db.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    await db.commit()
    
    return booking


async def delete_booking(db: aiosqlite.Connection, booking_id: int):
    """Удалить запись без освобождения слота"""
    await db.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
    await db.commit()


async def update_booking_reminder(db: aiosqlite.Connection, booking_id: int, reminder_job_id: str):
    """Обновить ID задачи напоминания"""
    await db.execute(
        "UPDATE bookings SET reminder_job_id = ? WHERE id = ?",
        (reminder_job_id, booking_id)
    )


async def get_bookings_for_reminders(db: aiosqlite.Connection, target_datetime: datetime) -> List[dict]:
    """Получить записи для отправки напоминаний"""
    target_date = target_datetime.date().isoformat()
    
    cursor = await db.execute(
        """
        SELECT b.*, u.telegram_id, u.name as user_name, u.phone as user_phone,
               s.name as service_name, s.price as service_price
        FROM bookings b
        JOIN users u ON b.user_id = u.telegram_id
        JOIN services s ON b.service_id = s.id
        WHERE b.date = ? AND b.reminder_job_id IS NOT NULL
        """,
        (target_date,)
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]