"""
Фабрика inline-клавиатур
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
from config import CHANNEL_LINK


def get_main_menu_kb() -> InlineKeyboardMarkup:
    """Главное меню"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Записаться", callback_data="book_start"))
    builder.row(InlineKeyboardButton(text="👤 Моя запись", callback_data="my_booking"))
    builder.row(
        InlineKeyboardButton(text="💰 Прайсы", callback_data="show_prices"),
        InlineKeyboardButton(text="🖼 Портфолио", callback_data="show_portfolio")
    )
    builder.row(InlineKeyboardButton(text="❌ Отменить запись", callback_data="cancel_booking"))
    return builder.as_markup()


def get_main_menu_kb_with_admin() -> InlineKeyboardMarkup:
    """Главное меню с админ-панелью"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Записаться", callback_data="book_start"))
    builder.row(InlineKeyboardButton(text="👤 Моя запись", callback_data="my_booking"))
    builder.row(
        InlineKeyboardButton(text="💰 Прайсы", callback_data="show_prices"),
        InlineKeyboardButton(text="🖼 Портфолио", callback_data="show_portfolio")
    )
    builder.row(InlineKeyboardButton(text="❌ Отменить запись", callback_data="cancel_booking"))
    builder.row(InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_menu"))
    return builder.as_markup()


def get_calendar_kb(year: int, month: int, available_dates: list) -> InlineKeyboardMarkup:
    """Календарь с доступными датами"""
    builder = InlineKeyboardBuilder()
    
    # Заголовок с месяцем
    month_names = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", 
                   "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]
    builder.row(InlineKeyboardButton(
        text=f"{month_names[month-1]} {year}",
        callback_data="calendar_header"
    ))
    
    # Кнопки навигации по месяцам
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    builder.row(
        InlineKeyboardButton(text="◀️", callback_data=f"cal_prev:{prev_year}:{prev_month}"),
        InlineKeyboardButton(text="📆 Сегодня", callback_data="cal_today"),
        InlineKeyboardButton(text="▶️", callback_data=f"cal_next:{next_year}:{next_month}")
    )
    
    # Дни недели
    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[InlineKeyboardButton(text=d, callback_data="day_header") for d in weekdays])
    
    # Дни месяца
    from calendar import monthrange
    _, days_in_month = monthrange(year, month)
    
    # Первый день месяца (0 = понедельник)
    first_day = datetime(year, month, 1).weekday()
    
    # Пустые ячейки перед первым днём
    week_row = []
    for _ in range(first_day):
        week_row.append(InlineKeyboardButton(text=" ", callback_data="empty"))
    
    # Дни месяца
    for day in range(1, days_in_month + 1):
        date_str = f"{year}-{month:02d}-{day:02d}"
        is_available = date_str in available_dates
        is_past = datetime(year, month, day).date() < datetime.now().date()
        
        if is_past or not is_available:
            text = f"{day}"
            cb = "empty"
        else:
            text = f"✅ {day}"
            cb = f"date_select:{date_str}"
        
        week_row.append(InlineKeyboardButton(text=text, callback_data=cb))
        
        if len(week_row) == 7:
            builder.row(*week_row)
            week_row = []
    
    # Оставшиеся дни в последней неделе
    if week_row:
        while len(week_row) < 7:
            week_row.append(InlineKeyboardButton(text=" ", callback_data="empty"))
        builder.row(*week_row)
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu"))
    return builder.as_markup()


def get_time_slots_kb(date: str, slots: list) -> InlineKeyboardMarkup:
    """Клавиатура с временными слотами"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=f"📅 Выбранная дата: {date}",
        callback_data="empty"
    ))
    
    if not slots:
        builder.row(InlineKeyboardButton(
            text="❌ Нет свободных слотов",
            callback_data="empty"
        ))
    else:
        for slot in slots:
            builder.row(InlineKeyboardButton(
                text=f"🕐 {slot['time']}",
                callback_data=f"time_select:{slot['id']}:{slot['time']}"
            ))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_calendar"))
    return builder.as_markup()


def get_services_kb(services: list) -> InlineKeyboardMarkup:
    """Клавиатура с услугами"""
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.row(InlineKeyboardButton(
            text=f"{service['name']} — {service['price']}₽",
            callback_data=f"service_select:{service['id']}:{service['name']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_time"))
    return builder.as_markup()


def get_confirm_booking_kb() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения записи"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm_booking"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_booking_flow")
    )
    return builder.as_markup()


def get_subscription_kb() -> InlineKeyboardMarkup:
    """Клавиатура проверки подписки"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text="🔗 Подписаться",
        url=CHANNEL_LINK
    ))
    builder.row(InlineKeyboardButton(
        text="✅ Проверить подписку",
        callback_data="check_subscription"
    ))
    return builder.as_markup()


def get_admin_menu_kb() -> InlineKeyboardMarkup:
    """Админ-панель"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Расписание", callback_data="admin_schedule"))
    builder.row(
        InlineKeyboardButton(text="➕ Добавить слот", callback_data="admin_add_slot"),
        InlineKeyboardButton(text="➖ Удалить слот", callback_data="admin_del_slot")
    )
    builder.row(InlineKeyboardButton(text="🚫 Закрыть день", callback_data="admin_close_day"))
    builder.row(
        InlineKeyboardButton(text="💼 Услуги: добавить", callback_data="admin_add_service"),
        InlineKeyboardButton(text="💼 Услуги: удалить", callback_data="admin_del_service")
    )
    builder.row(InlineKeyboardButton(text="✏️ Изменить цену", callback_data="admin_edit_price"))
    builder.row(InlineKeyboardButton(text="🔙 В меню", callback_data="main_menu"))
    return builder.as_markup()


def get_admin_slots_kb(date: str, slots: list) -> InlineKeyboardMarkup:
    """Управление слотами для админа"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(
        text=f"📅 {date}",
        callback_data="empty"
    ))
    
    for slot in slots:
        status = "🟢" if slot['is_available'] else "🔴"
        action = "free" if slot['is_available'] else "busy"
        builder.row(InlineKeyboardButton(
            text=f"{status} {slot['time']} ({action})",
            callback_data=f"admin_slot:{slot['id']}:{action}"
        ))
    
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_schedule"))
    return builder.as_markup()


def get_admin_services_kb(services: list) -> InlineKeyboardMarkup:
    """Управление услугами для админа"""
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.row(InlineKeyboardButton(
            text=f"{service['name']} — {service['price']}₽",
            callback_data=f"admin_service:{service['id']}"
        ))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu"))
    return builder.as_markup()


def get_cancel_booking_kb(booking_id: int) -> InlineKeyboardMarkup:
    """Клавиатура отмены записи"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Да, отменить",
            callback_data=f"confirm_cancel:{booking_id}"
        ),
        InlineKeyboardButton(text="❌ Нет", callback_data="main_menu")
    )
    return builder.as_markup()


def get_back_kb(callback: str) -> InlineKeyboardMarkup:
    """Простая кнопка «Назад»"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data=callback))
    return builder.as_markup()