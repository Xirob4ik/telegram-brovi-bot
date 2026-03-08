"""
Обработчики отмены записи
"""
from aiogram import Router, F, types, Bot, Dispatcher
from database.db import get_db
from database.models import get_user_booking, cancel_booking
from keyboards.inline import get_cancel_booking_kb, get_back_kb
from scheduler import cancel_reminder
from config import ADMIN_ID, CHANNEL_ID
import logging

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "cancel_booking")
async def start_cancel(callback: types.CallbackQuery):
    """Начало процесса отмены"""
    async with get_db() as db:
        booking = await get_user_booking(db, callback.from_user.id)
    
    if not booking:
        await callback.answer("❗ У вас нет активных записей", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"❌ <b>Отмена записи</b>\n\n"
        f"📅 {booking['date']} в {booking['time']}\n"
        f"💆 {booking['service_name']}\n\n"
        f"Вы уверены?",
        parse_mode="HTML",
        reply_markup=get_cancel_booking_kb(booking['id'])
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_cancel:"))
async def confirm_cancel(callback: types.CallbackQuery, bot: Bot):
    """Подтверждение отмены"""
    booking_id = int(callback.data.split(":")[1])
    
    async with get_db() as db:
        booking = await cancel_booking(db, booking_id)
        await db.commit()
    
    if not booking:
        await callback.answer("❌ Запись не найдена", show_alert=True)
        return
    
    cancel_reminder(booking_id)
    
    await callback.message.edit_text(
        "✅ <b>Запись отменена</b>\n\n"
        "Будем рады видеть вас в другое время! ❤️",
        parse_mode="HTML",
        reply_markup=get_back_kb("main_menu")
    )
    
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🗑 <b>Запись отменена</b>\n\n"
                 f"👤 {booking['user_name']}\n"
                 f"📅 {booking['date']} в {booking['time']}\n"
                 f"💆 {booking['service_name']}",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка уведомления админа: {e}")
    
    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"❌ <b>Отмена: {booking['date']} {booking['time']}</b>\n"
                 f"Слот освободился для записи",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка уведомления канала: {e}")
    
    await callback.answer()