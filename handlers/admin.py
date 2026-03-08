"""
Админ-панель
"""
from aiogram import Router, F, types, Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from database.db import get_db
from database.models import (
    get_all_slots_by_date, create_slot, delete_slot, delete_slots_by_date,
    get_all_services, add_service, update_service, delete_service, get_service,
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
    viewing_schedule_date = State()
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
    
    await state.set_state(AdminFlow.viewing_schedule_date)
    await callback.message.edit_text(
        "📅 <b>Введите дату</b> (формат: ГГГГ-ММ-ДД):",
        parse_mode="HTML",
        reply_markup=get_back_kb("admin_menu")
    )
    await callback.answer()


@router.message(AdminFlow.viewing_schedule_date, F.text)
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


# ==================== УСЛУГИ ====================

@router.callback_query(F.data == "admin_add_service")
async def admin_start_add_service(callback: types.CallbackQuery, state: FSMContext):
    """Начало добавления услуги"""
    if not is_admin(callback.from_user.id):
        await callback.answer("🔐 Доступ запрещён", show_alert=True)
        return
    
    await state.set_state(AdminFlow.adding_service_name)
    await callback.message.edit_text(
        "➕ <b>Добавить услугу</b>\n\n"
        "Введите название услуги:",
        parse_mode="HTML",
        reply_markup=get_back_kb("admin_menu")
    )
    await callback.answer()


@router.message(AdminFlow.adding_service_name, F.text)
async def admin_add_service_name(message: types.Message, state: FSMContext):
    """Ввод названия новой услуги"""
    service_name = message.text.strip()
    
    if len(service_name) < 2:
        await message.answer("❗ Название должно содержать минимум 2 символа")
        return
    
    await state.update_data(new_service_name=service_name)
    await state.set_state(AdminFlow.adding_service_price)
    
    await message.answer(
        "💰 Введите цену услуги (в рублях, числом):",
        reply_markup=get_back_kb("admin_menu")
    )


@router.message(AdminFlow.adding_service_price, F.text)
async def admin_add_service_price(message: types.Message, state: FSMContext):
    """Ввод цены новой услуги"""
    price_str = message.text.strip()
    
    try:
        price = int(price_str)
        if price <= 0:
            raise ValueError()
    except ValueError:
        await message.answer("❗ Введите корректное положительное число")
        return
    
    data = await state.get_data()
    service_name = data.get('new_service_name')
    
    if not service_name:
        await message.answer("❌ Название услуги не найдено. Начните заново.")
        await state.clear()
        return
    
    async with get_db() as db:
        try:
            # Проверяем, нет ли уже такой услуги
            existing_services = await get_all_services(db)
            for svc in existing_services:
                if svc['name'].lower() == service_name.lower():
                    await message.answer(f"❌ Услуга с названием '{service_name}' уже существует")
                    await state.clear()
                    return
            
            service_id = await add_service(db, service_name, price)
        except Exception as e:
            logger.error(f"Ошибка при добавлении услуги: {e}")
            await message.answer(f"❌ Ошибка при добавлении услуги: {e}")
            await state.clear()
            return
    
    await message.answer(
        f"✅ Услуга '{service_name}' добавлена с ценой {price}₽",
        reply_markup=get_back_kb("admin_menu")
    )
    await state.clear()


@router.callback_query(F.data == "admin_del_service")
async def admin_show_services_for_delete(callback: types.CallbackQuery):
    """Показать список услуг для удаления"""
    if not is_admin(callback.from_user.id):
        await callback.answer("🔐 Доступ запрещён", show_alert=True)
        return
    
    async with get_db() as db:
        services = await get_all_services(db)
    
    if not services:
        await callback.answer("❌ Нет услуг для удаления", show_alert=True)
        return
    
    text = "💼 <b>Выберите услугу для удаления</b>:\n\n"
    for svc in services:
        text += f"• {svc['name']} — {svc['price']}₽\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_services_kb(services)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_service:"))
async def admin_delete_service(callback: types.CallbackQuery):
    """Удаление выбранной услуги"""
    if not is_admin(callback.from_user.id):
        await callback.answer("🔐 Доступ запрещён", show_alert=True)
        return
    
    parts = callback.data.split(":")
    service_id = int(parts[1])
    
    async with get_db() as db:
        service = await get_service(db, service_id)
        if not service:
            await callback.answer("❌ Услуга не найдена", show_alert=True)
            return
        
        await delete_service(db, service_id)
        await db.commit()
    
    await callback.message.edit_text(
        f"✅ Услуга '{service['name']}' удалена",
        reply_markup=get_back_kb("admin_menu")
    )
    await callback.answer()


@router.callback_query(F.data == "admin_edit_price")
async def admin_show_services_for_edit(callback: types.CallbackQuery):
    """Показать список услуг для редактирования цены"""
    if not is_admin(callback.from_user.id):
        await callback.answer("🔐 Доступ запрещён", show_alert=True)
        return
    
    async with get_db() as db:
        services = await get_all_services(db)
    
    if not services:
        await callback.answer("❌ Нет услуг для редактирования", show_alert=True)
        return
    
    text = "💼 <b>Выберите услугу для изменения цены</b>:\n\n"
    for svc in services:
        text += f"• {svc['name']} — {svc['price']}₽\n"
    
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_admin_services_kb(services)
    )
    await callback.answer()


# Остальные функции остаются как есть...