"""
Утилиты для работы с календарём
"""
from datetime import datetime, timedelta
from config import WORK_DAYS, WORK_HOURS, SLOT_DURATION


def generate_month_dates(year: int, month: int) -> list:
    """Генерация всех дат месяца"""
    from calendar import monthrange
    _, days_in_month = monthrange(year, month)
    
    dates = []
    for day in range(1, days_in_month + 1):
        date_obj = datetime(year, month, day)
        if date_obj.weekday() in WORK_DAYS:
            dates.append(date_obj.strftime("%Y-%m-%d"))
    return dates


def is_date_available(date_str: str) -> bool:
    """Проверка, что дата не в прошлом и в рабочем диапазоне"""
    try:
        date = datetime.strptime(date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        max_date = today + timedelta(days=31)
        return today <= date <= max_date
    except ValueError:
        return False


def generate_time_slots() -> list:
    """Генерация временных слотов на день"""
    slots = []
    for hour in WORK_HOURS:
        time_str = f"{hour:02d}:00"
        slots.append(time_str)
    return slots


def parse_callback_date(callback_data: str) -> tuple:
    """Парсинг даты из callback_data"""
    parts = callback_data.split(":")
    if len(parts) >= 3:
        return int(parts[1]), int(parts[2])
    return None, None