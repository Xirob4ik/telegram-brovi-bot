"""
Клавиатуры для бота
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_keyboard() -> InlineKeyboardMarkup:
    """Главное меню пользователя"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📅 Записаться", callback_data="book"))
    builder.row(InlineKeyboardButton(text="💰 Прайс", callback_data="price"))
    builder.row(InlineKeyboardButton(text="👤 Профиль", callback_data="profile"))
    return builder.as_markup()


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Админ-панель"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Услуги: добавить", callback_data="admin_add_service"))
    builder.row(InlineKeyboardButton(text="Добавить слот", callback_data="admin_add_slot"))
    builder.row(InlineKeyboardButton(text="Все записи", callback_data="admin_bookings"))
    return builder.as_markup()


def get_services_inline_keyboard(services: list) -> InlineKeyboardMarkup:
    """Клавиатура с услугами"""
    builder = InlineKeyboardBuilder()
    for service in services:
        builder.row(InlineKeyboardButton(
            text=f"{service['name']} - {service['price']}₽",
            callback_data=f"service_{service['id']}"
        ))
    builder.row(InlineKeyboardButton(text="❌ Отмена", callback_data="cancel"))
    return builder.as_markup()


def get_confirm_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура подтверждения"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm"),
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    )
    return builder.as_markup()
