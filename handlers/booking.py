"""
Обработчики процесса записи (FSM)
"""
from aiogram import Router, F, types, Bot, Dispatcher
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from keyboards.inline import (
    get_calendar_kb, get_time_slots_kb, get_services_kb,
    get_confirm_booking_kb, get_back_kb
)
from utils.calendar import is_date_available
from database.db import get_db
from database.models import (
    get_available_slots, get_slot, get_all_services,
    create_booking, mark_slot_unavailable, get_user_booking,
    create_user, update_booking_reminder
)
from scheduler import schedule_reminder
from config import ADMIN_ID, CHANNEL_ID
import logging

logger = logging.getLogger(__name__)
router = Router()


class BookingFlow(StatesGroup):
    selecting_date = State()
    selecting_time = State()
    selecting_service = State()
    entering_name = State()
    entering_phone = State()
    confirming = State()


@router.callback_query(F.data == "book_start")
async def start_booking(callback: types.CallbackQuery, state: FSMContext):
    """Начало процесса записи"""
    async with get_db() as db:
        existing = await get_user_booking(db, callback.from_user.id)
        if existing:
            await callback.answer(
                "❗ У вас уже есть запись. Отмените её перед новой записью.",
                show_alert=True
            )
            return
    
    await state.set_state(BookingFlow.selecting_date)
    await show_calendar(callback, state)


async def show_calendar(callback, state: FSMContext):
    """Показать календарь с доступными датами"""
    now = datetime.now()
    current_year, current_month = now.year, now.month
    
    async with get_db() as db:
        available_dates = []
        for offset in range(31):
            check_date = (now + timedelta(days=offset)).date()
            date_str = check_date.isoformat()
            slots = await get_available_slots(db, date_str)
            if slots:
                available_dates.append(date_str)
    
    keyboard = get_calendar_kb(current_year, current_month, available_dates)
    
    if isinstance(callback, types.CallbackQuery):
        await callback.message.edit_text(
            "📅 <b>Выберите дату записи</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
        await callback.answer()
    else:
        await callback.answer(
            "📅 <b>Выберите дату записи</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )


@router.callback_query(F.data.startswith("cal_prev:"))
@router.callback_query(F.data.startswith("cal_next:"))
async def navigate_calendar(callback: types.CallbackQuery, state: FSMContext):
    """Навигация по месяцам в календаре"""
    action, year, month = callback.data.split(":")
    year, month = int(year), int(month)
    
    now = datetime.now()
    if year < now.year or (year == now.year and month < now.month):
        year, month = now.year, now.month
    
    async with get_db() as db:
        available_dates = []
        for offset in range(31):
            check_date = (now + timedelta(days=offset)).date()
            date_str = check_date.isoformat()
            slots = await get_available_slots(db, date_str)
            if slots:
                available_dates.append(date_str)
    
    keyboard = get_calendar_kb(year, month, available_dates)
    
    try:
        await callback.message.edit_reply_markup(reply_markup=keyboard)
    except Exception:
        pass
    
    await callback.answer()


@router.callback_query(F.data == "cal_today")
async def select_today(callback: types.CallbackQuery, state: FSMContext):
    """Выбор сегодняшней даты"""
    today = datetime.now().date().isoformat()
    await state.update_data(selected_date=today)
    await state.set_state(BookingFlow.selecting_time)
    await show_time_slots(callback, today)


@router.callback_query(F.data.startswith("date_select:"))
async def handle_date_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора даты"""
    date_str = callback.data.split(":")[1]
    
    # Валидация даты
    if not is_date_available(date_str):
        await callback.answer("❌ Эта дата недоступна", show_alert=True)
        return
    
    await state.update_data(selected_date=date_str)
    await state.set_state(BookingFlow.selecting_time)
    await show_time_slots(callback, date_str)


async def show_time_slots(callback, date_str: str):
    """Показать доступные слоты на дату"""
    async with get_db() as db:
        # Получаем только доступные слоты
        available_slots = await get_available_slots(db, date_str)
    
    if isinstance(callback, types.CallbackQuery):
        keyboard = get_time_slots_kb(date_str, available_slots)
        if available_slots:
            await callback.message.edit_text(
                f"🕐 <b>Выберите время на {date_str}</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            await callback.message.edit_text(
                f"❌ <b>На {date_str} нет свободных слотов</b>",
                parse_mode="HTML",
                reply_markup=get_back_kb("back_to_calendar")
            )
        await callback.answer()
    else:
        keyboard = get_time_slots_kb(date_str, available_slots)
        if available_slots:
            await callback.edit_text(
                f"🕐 <b>Выберите время на {date_str}</b>",
                parse_mode="HTML",
                reply_markup=keyboard
            )
        else:
            await callback.edit_text(
                f"❌ <b>На {date_str} нет свободных слотов</b>",
                parse_mode="HTML",
                reply_markup=get_back_kb("back_to_calendar")
            )


async def show_time_slots_refreshed(callback: types.CallbackQuery, date_str: str):
    """Обновление списка слотов без ошибки 'message not modified'"""
    async with get_db() as db:
        available_slots = await get_available_slots(db, date_str)
    
    keyboard = get_time_slots_kb(date_str, available_slots)
    
    # Чтобы избежать ошибки, изменим текст сообщения
    if available_slots:
        await callback.message.edit_text(
            f"🕐 <b>Выберите время на {date_str}</b>\n🔄 Обновлено",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            f"❌ <b>На {date_str} нет свободных слотов</b>",
            parse_mode="HTML",
            reply_markup=get_back_kb("back_to_calendar")
        )
    await callback.answer()


@router.callback_query(F.data == "back_to_calendar")
async def back_to_calendar(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору даты"""
    await state.set_state(BookingFlow.selecting_date)
    await show_calendar(callback, state)


@router.callback_query(F.data.startswith("time_select:"))
async def handle_time_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора времени"""
    parts = callback.data.split(":")
    slot_id = parts[1]
    time_str = parts[2]
    
    async with get_db() as db:
        data = await state.get_data()
        date_str = data.get('selected_date')
        
        # Проверяем слот в момент выбора (вдруг его кто-то занял)
        slot = await get_slot(db, date_str, time_str)
        if not slot or not slot['is_available']:
            await callback.answer("❌ Это время уже занято", show_alert=True)
            # Обновляем список слотов, чтобы пользователь видел актуальное состояние
            await show_time_slots_refreshed(callback, date_str)
            return
    
    # Сохраняем выбор
    await state.update_data(selected_slot_id=slot_id, selected_time=time_str)
    await state.set_state(BookingFlow.selecting_service)
    await show_services(callback)


async def show_services(callback: types.CallbackQuery):
    """Показать список услуг"""
    async with get_db() as db:
        services = await get_all_services(db)
    
    if isinstance(callback, types.CallbackQuery):
        keyboard = get_services_kb(services)
        await callback.message.edit_text(
            "💆 <b>Выберите услугу</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )
    else:
        keyboard = get_services_kb(services)
        await callback.edit_text(
            "💆 <b>Выберите услугу</b>",
            parse_mode="HTML",
            reply_markup=keyboard
        )


@router.callback_query(F.data == "back_to_time")
async def back_to_time(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору времени"""
    await state.set_state(BookingFlow.selecting_time)
    data = await state.get_data()
    date_str = data.get('selected_date')
    await show_time_slots(callback, date_str)


@router.callback_query(F.data.startswith("service_select:"))
async def handle_service_selection(callback: types.CallbackQuery, state: FSMContext):
    """Обработка выбора услуги"""
    parts = callback.data.split(":", 2)
    service_id = parts[1]
    service_name = parts[2]
    
    await state.update_data(selected_service_id=service_id, selected_service_name=service_name)
    await state.set_state(BookingFlow.entering_name)
    
    if isinstance(callback, types.CallbackQuery):
        await callback.message.edit_text(
            "✍️ <b>Введите ваше имя</b> (или напишите /skip):",
            parse_mode="HTML",
            reply_markup=get_back_kb("back_to_services")
        )
        await callback.answer()
    else:
        await callback.edit_text(
            "✍️ <b>Введите ваше имя</b> (или напишите /skip):",
            parse_mode="HTML",
            reply_markup=get_back_kb("back_to_services")
        )


@router.callback_query(F.data == "back_to_services")
async def back_to_services(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к выбору услуги"""
    await state.set_state(BookingFlow.selecting_service)
    await show_services(callback)


@router.message(BookingFlow.entering_name)
async def handle_name_input(message: types.Message, state: FSMContext):
    """Обработка ввода имени"""
    if message.text == "/skip":
        name = message.from_user.full_name
    else:
        name = message.text.strip()
        if len(name) < 2:
            await message.answer("❗ Имя должно содержать минимум 2 символа")
            return
    
    await state.update_data(user_name=name)
    await state.set_state(BookingFlow.entering_phone)
    
    await message.answer(
        "📱 <b>Введите ваш номер телефона</b> (например: +79991234567):",
        parse_mode="HTML",
        reply_markup=get_back_kb("back_to_name")
    )


@router.callback_query(F.data == "back_to_name")
async def back_to_name(callback: types.CallbackQuery, state: FSMContext):
    """Возврат к вводу имени"""
    await state.set_state(BookingFlow.entering_name)
    await callback.message.edit_text(
        "✍️ <b>Введите ваше имя</b> (или напишите /skip):",
        parse_mode="HTML",
        reply_markup=get_back_kb("back_to_services")
    )
    await callback.answer()


@router.message(BookingFlow.entering_phone)
async def handle_phone_input(message: types.Message, state: FSMContext):
    """Обработка ввода телефона"""
    phone = message.text.strip()
    
    if not phone.startswith("+") or len(phone) < 10:
        await message.answer("❗ Введите корректный номер в формате +7...")
        return
    
    await state.update_data(user_phone=phone)
    await state.set_state(BookingFlow.confirming)
    
    data = await state.get_data()
    await message.answer(
        f"✅ <b>Подтвердите запись</b>\n\n"
        f"📅 Дата: {data['selected_date']}\n"
        f"🕐 Время: {data['selected_time']}\n"
        f"💆 Услуга: {data['selected_service_name']}\n"
        f"👤 Имя: {data['user_name']}\n"
        f"📱 Телефон: {phone}\n\n"
        f"Нажмите «Подтвердить» для завершения:",
        parse_mode="HTML",
        reply_markup=get_confirm_booking_kb()
    )


@router.callback_query(F.data == "cancel_booking_flow")
async def cancel_booking_flow(callback: types.CallbackQuery, state: FSMContext):
    """Отмена процесса записи"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Запись отменена",
        reply_markup=get_back_kb("main_menu")
    )
    await callback.answer()


@router.callback_query(F.data == "confirm_booking")
async def confirm_booking(callback: types.CallbackQuery, state: FSMContext, bot: Bot):
    """Подтверждение и создание записи"""
    data = await state.get_data()
    user_id = callback.from_user.id
    
    async with get_db() as db:
        slot = await get_slot(db, data['selected_date'], data['selected_time'])
        if not slot or not slot['is_available']:
            await callback.answer("❌ Это время только что заняли. Выберите другое.", show_alert=True)
            await state.set_state(BookingFlow.selecting_time)
            await show_time_slots(callback, data['selected_date'])
            return
        
        existing = await get_user_booking(db, user_id)
        if existing:
            await callback.answer("❗ У вас уже есть запись", show_alert=True)
            return
        
        await create_user(db, user_id, data['user_name'], data['user_phone'])
        await mark_slot_unavailable(db, slot['id'])
        
        booking_id = await create_booking(
            db=db,
            user_id=user_id,
            service_id=int(data['selected_service_id']),
            date=data['selected_date'],
            time=data['selected_time']
        )
        
        await db.commit()
    
    appointment_dt = datetime.strptime(
        f"{data['selected_date']} {data['selected_time']}",
        "%Y-%m-%d %H:%M"
    )
    reminder_job_id = await schedule_reminder(
        bot=bot,
        booking_id=booking_id,
        appointment_datetime=appointment_dt,
        user_id=user_id,
        service_name=data['selected_service_name'],
        appointment_time=data['selected_time']
    )
    
    if reminder_job_id:
        async with get_db() as db:
            await update_booking_reminder(db, booking_id, reminder_job_id)
            await db.commit()
    
    await callback.message.edit_text(
        f"🎉 <b>Запись подтверждена!</b>\n\n"
        f"📅 {data['selected_date']} в {data['selected_time']}\n"
        f"💆 {data['selected_service_name']}\n"
        f"📍 Ждём вас!",
        parse_mode="HTML",
        reply_markup=get_back_kb("main_menu")
    )
    
    try:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text=f"🔔 <b>Новая запись!</b>\n\n"
                 f"👤 {data['user_name']}\n"
                 f"📱 {data['user_phone']}\n"
                 f"📅 {data['selected_date']} в {data['selected_time']}\n"
                 f"💆 {data['selected_service_name']}",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Не удалось отправить уведомление админу: {e}")
    
    try:
        await bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"📅 <b>Запись на {data['selected_date']}</b>\n"
                 f"🕐 {data['selected_time']} — {data['selected_service_name']}\n"
                 f"👤 {data['user_name']}",
            parse_mode="HTML"
        )
    except Exception as e:
        logger.error(f"❌ Не удалось отправить в канал: {e}")
    
    await state.clear()
    await callback.answer()