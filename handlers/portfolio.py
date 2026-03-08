"""
Обработчик кнопки «Портфолио»
"""
from aiogram import Router, F, types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()


@router.callback_query(F.data == "show_portfolio")
async def show_portfolio(callback: types.CallbackQuery):
    """Показать портфолио"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="🖼 Смотреть портфолио",
            url="https://ru.pinterest.com/crystalwithluv/_created/"
        )
    ], [
        InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
    ]])
    
    await callback.message.edit_text(
        "🎨 <b>Моё портфолио</b>\n\n"
        "Посмотрите примеры работ в Pinterest:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()