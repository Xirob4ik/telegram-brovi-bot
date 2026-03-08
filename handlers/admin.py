"""
Админ-панель
"""
from aiogram import Router, F, types, Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import get_db
from database.models import (
    get_all_slots_by_date, create_slot, delete_slot, delete_slots_by_date,
    get_all_services, add_service, update_service, delete_service,
    get_bookings_by_date
)
from keyboards.inline import (
    get_admin_menu_kb, get_admin_slots_kb, get_admin_services_kb,
    get_back_kb
)
from config import ADMIN_ID
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = Router()


class AdminFlow(StatesGroup):
    adding_slot_date = State()
    adding_slot_time = State()
    deleting_slot = State()
    closing_day = State()
    adding_service_name = State()
    adding_service_price = State()
    editing_service_price = State()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


@router.callback_query(F.data == "admin_menu")
async def show_admin_menu(callback: types.CallbackQuery):
    """Показать админ-меню"""
    if not is_admin(callback.from_user.id):
        await callback.answer("🔐 Доступ запрещён", show_alert=True)
        return
    
    await callback.message.edit_text(
        "🛠 <b>Админ-панель</b>",
        parse_mode="HTML",
        reply_markup=get_admin_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_slot")
async def admin_start_add_slot(callback: types.CallbackQuery, state: FSMContext):
    """Начало добавления слота"""
    if not is_admin(callback.from_user.id):
        await callback.answer("🔐 Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminFlow.adding_slot_date)
    await callback.message.edit_text(
        "➕ <b>Добавить слот</b>\n\n"
        "Введите дату (ГГГГ-ММ-ДД):",
        parse_mode="HTML",
        reply_markup=get_back_kb("admin_menu")
    )
    await callback.answer()


@router.message(AdminFlow.adding_slot_date, F.text)
async def admin_add_slot_date(message: types.Message, state: FSMContext):
    """Ввод даты для нового слота"""
    logger.info(f"Получена дата: {message.text}, состояние: {await state.get_state()}")
    
    date_str = message.text.strip()
    
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await message.answer("❗ Неверный формат даты. Используйте ГГГГ-ММ-ДД")
        return
    
    await state.update_data(new_slot_date=date_str)
    await state.set_state(AdminFlow.adding_slot_time)
    
    await message.answer(
        "🕐 Введите время (формат: ЧЧ:ММ, например 14:00):",
        reply_markup=get_back_kb("admin_menu")
    )


@router.message(AdminFlow.adding_slot_time, F.text)
async def admin_add_slot_time(message: types.Message, state: FSMContext):
    """Ввод времени для нового слота"""
    logger.info(f"Получено время: {message.text}, состояние: {await state.get_state()}")
    
    time_str = message.text.strip()
    
    try:
        datetime.strptime(time_str, "%H:%M")
    except ValueError:
        await message.answer("❗ Неверный формат времени. Используйте ЧЧ:ММ")
        return
    
    data = await state.get_data()
    date_str = data.get('new_slot_date')
    
    if not date_str:
        await message.answer("❌ Дата не найдена. Начните заново.")
        await state.clear()
        return
    
    logger.info(f"Добавление слота: {date_str} {time_str}")
    
    async with get_db() as db:
        try:
            slot_id = await create_slot(db, date_str, time_str)
            await db.commit()
            logger.info(f"Слот успешно добавлен с ID: {slot_id}")
        except Exception as e:
            logger.error(f"Ошибка при добавлении слота: {e}")
            await message.answer(f"❌ Ошибка при добавлении слота: {e}")
            await state.clear()
            return
    
    await message.answer(
        f"✅ Слот {date_str} {time_str} добавлен",
        reply_markup=get_back_kb("admin_menu")
    )
    await state.clear()


@router.message(AdminFlow.adding_slot_date)
@router.message(AdminFlow.adding_slot_time)
async def admin_handle_wrong_input(message: types.Message, state: FSMContext):
    """Обработка некорректного ввода"""
    current_state = await state.get_state()
    logger.info(f"Некорректный ввод в состоянии {current_state}: {message.text}")
    await message.answer("❌ Введите данные в нужном формате.")


@router.callback_query(F.data == "admin_schedule")
async def admin_schedule(callback: types.CallbackQuery, state: FSMContext):
    """Выбор даты для просмотра расписания"""
    if not is_admin(callback.from_user.id):
        await callback.answer("🔐 Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminFlow.adding_slot_date)
    await callback.message.edit_text(
        "📅 <b>Введите дату</b> (формат: ГГГГ-ММ-ДД):",
        parse_mode="HTML",
        reply_markup=get_back_kb("admin_menu")
    )
    await callback.answer()


@router.message(AdminFlow.adding_slot_date, F.text)
async def admin_date_selected(message: types.Message, state: FSMContext, bot: Bot):
    """Обработка выбранной даты"""
    logger.info(f"Получена дата для просмотра: {message.text}, состояние: {await state.get_state()}")
    
    date_str = message.text.strip()
    
    try:
        check_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        if check_date < datetime.now().date():
            raise ValueError()
    except ValueError:
        await message.answer("❗ Введите корректную будущую дату в формате ГГГГ-ММ-ДД")
        return
    
    await state.update_data(admin_date=date_str)
    
    async with get_db() as db:
        slots = await get_all_slots_by_date(db, date_str)
        bookings = await get_bookings_by_date(db, date_str)
    
    text = f"📋 <b>Расписание на {date_str}</b>\n\n"
    
    if not slots:
        text += "⚪ Нет созданных слотов\n"
    else:
        for slot in slots:
            status = "🟢 Свободно" if slot['is_available'] else "🔴 Занято"
            booking = next((b for b in bookings if b['time'] == slot['time']), None)
            if booking:
                status += f" — {booking['user_name']}: {booking['service_name']}"
            text += f"🕐 {slot['time']}: {status}\n"
    
    keyboard = get_admin_slots_kb(date_str, slots)
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
    await state.clear()


# Остальные функции остаются как есть...