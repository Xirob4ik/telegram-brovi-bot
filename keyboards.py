from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_main_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📅 Записаться"))
    keyboard.add(KeyboardButton("💰 Прайс-лист"))
    keyboard.add(KeyboardButton("👤 Мой профиль"))
    keyboard.add(KeyboardButton("ℹ️ Информация"))
    return keyboard

def get_admin_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📊 Статистика"))
    keyboard.add(KeyboardButton("📝 Услуги: добавить"), KeyboardButton("📝 Услуги: список"))
    keyboard.add(KeyboardButton("⏰ Добавить слот"), KeyboardButton("⏰ Слоты: список"))
    keyboard.add(KeyboardButton("🔙 В главное меню"))
    return keyboard

def get_services_inline_keyboard(services) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    for service in services:
        keyboard.add(InlineKeyboardButton(
            f"{service.name} - {service.price}₽",
            callback_data=f"select_service_{service.id}"
        ))
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    return keyboard

def get_slots_inline_keyboard(slots) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    for slot in slots:
        time_str = slot.start_time.strftime("%d.%m %H:%M")
        keyboard.add(InlineKeyboardButton(
            f"{time_str}",
            callback_data=f"select_slot_{slot.id}"
        ))
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    return keyboard

def get_confirm_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("✅ Подтвердить", callback_data="confirm_booking"))
    keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    return keyboard

def get_back_keyboard() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("🔙 Назад"))
    return keyboard

def get_cancel_keyboard() -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(InlineKeyboardButton("❌ Отменить запись", callback_data="cancel_appointment"))
    return keyboard
