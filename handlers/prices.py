"""
Обработчик кнопки «Прайсы»
"""
from aiogram import Router, F, types, Dispatcher

router = Router()


@router.callback_query(F.data == "show_prices")
async def show_prices(callback: types.CallbackQuery):
    """Показать прайс-лист"""
    await callback.message.edit_text(
        "💰 <b>Прайс</b>\n\n"
        "Коррекция бровей — 700₽\n"
        "Окрашивание бровей — 900₽\n"
        "Ламинирование бровей — 1500₽",
        parse_mode="HTML",
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[[
            types.InlineKeyboardButton(text="🔙 Назад", callback_data="main_menu")
        ]])
    )
    await callback.answer()


def register_prices_handlers(dp: Dispatcher):
    """Регистрация хендлеров прайсов"""
    dp.include_router(router)