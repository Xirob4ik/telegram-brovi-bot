from aiogram import types, Dispatcher, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from database.db import get_db
from database.models import (
    create_user, get_user, update_user_phone,
    get_all_services, get_service, add_service,
    create_slot, get_slot, get_available_slots, mark_slot_unavailable,
    create_booking, get_user_booking, cancel_booking
)
from keyboards.inline import (
    get_main_keyboard, get_admin_keyboard, 
    get_services_inline_keyboard, get_confirm_keyboard
)
from config import ADMIN_IDS
from datetime import datetime, timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BookingState(StatesGroup):
    selecting_service = State()
    selecting_date = State()
    selecting_time = State()
    confirming = State()


class AdminServiceState(StatesGroup):
    adding_name = State()
    adding_price = State()


class AdminSlotState(StatesGroup):
    selecting_date = State()
    selecting_time = State()


async def start_handler(message: types.Message, state: FSMContext):
    await state.clear()
    
    telegram_id = message.from_user.id
    name = message.from_user.full_name
    
    async with get_db() as db:
        user = await get_user(db, telegram_id)
        if not user:
            await create_user(db, telegram_id, name, None)
            logger.info(f"Создан новый пользователь: {telegram_id}")
    
    if telegram_id in ADMIN_IDS:
        await message.answer(
            f"👋 Привет, {name}!\n\nВы администратор. Выберите действие:",
            reply_markup=get_admin_keyboard()
        )
    else:
        await message.answer(
            f"👋 Привет, {name}!\n\nВыберите действие:",
            reply_markup=get_main_keyboard()
        )


async def book_handler(message: types.Message, state: FSMContext):
    await BookingState.selecting_service.set()
    
    async with get_db() as db:
        services = await get_all_services(db)
    
    if not services:
        await message.answer("❌ В данный момент нет доступных услуг")
        return
    
    keyboard = get_services_inline_keyboard(services)
    await message.answer("💇‍♀️ Выберите услугу:", reply_markup=keyboard)


async def process_service_selection(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "cancel":
        await state.clear()
        await callback.message.answer("Запись отменена", reply_markup=get_main_keyboard())
        return
    
    service_id = int(callback.data.replace("service_", ""))
    
    async with state.proxy() as data:
        data['service_id'] = service_id
    
    today = datetime.now().date()
    dates = [(today + timedelta(days=i)).isoformat() for i in range(7)]
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(
            text=f"{datetime.strptime(d, '%Y-%m-%d').strftime('%d.%m')}",
            callback_data=f"date_{d}"
        )] for d in dates
    ])
    keyboard.inline_keyboard.append([types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    
    await BookingState.selecting_date.set()
    await callback.message.answer("📅 Выберите дату:", reply_markup=keyboard)
    await callback.answer()


async def process_date_selection(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "cancel":
        await state.clear()
        await callback.message.answer("Запись отменена", reply_markup=get_main_keyboard())
        return
    
    date = callback.data.replace("date_", "")
    
    async with state.proxy() as data:
        data['date'] = date
    
    async with get_db() as db:
        slots = await get_available_slots(db, date)
    
    if not slots:
        await callback.message.answer("❌ Нет доступных слотов на эту дату.\nПожалуйста, выберите другую дату.")
        await BookingState.selecting_date.set()
        return
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text=time, callback_data=f"time_{time}")]
        for time in [slot['time'] for slot in slots]
    ])
    keyboard.inline_keyboard.append([types.InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    
    await BookingState.selecting_time.set()
    await callback.message.answer(f"⏰ Выберите время на {datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m.%Y')}:", reply_markup=keyboard)
    await callback.answer()


async def process_time_selection(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "cancel":
        await state.clear()
        await callback.message.answer("Запись отменена", reply_markup=get_main_keyboard())
        return
    
    time = callback.data.replace("time_", "")
    
    async with state.proxy() as data:
        data['time'] = time
    
    async with get_db() as db:
        service = await get_service(db, data['service_id'])
    
    if not service:
        await callback.message.answer("❌ Услуга не найдена")
        await state.clear()
        return
    
    await BookingState.confirming.set()
    
    keyboard = get_confirm_keyboard()
    await callback.message.answer(
        f"📋 Подтверждение записи:\n\nУслуга: {service['name']}\nЦена: {service['price']}₽\nДата: {datetime.strptime(data['date'], '%Y-%m-%d').strftime('%d.%m.%Y')}\nВремя: {time}\n\nПодтвердить запись?",
        reply_markup=keyboard
    )
    await callback.answer()


async def process_confirmation(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "cancel":
        await state.clear()
        await callback.message.answer("Запись отменена", reply_markup=get_main_keyboard())
        return
    
    if callback.data != "confirm":
        return
    
    async with state.proxy() as data:
        service_id = data.get('service_id')
        date = data.get('date')
        time = data.get('time')
    
    if not all([service_id, date, time]):
        await callback.message.answer("❌ Ошибка: данные записи не найдены")
        await state.clear()
        return
    
    async with get_db() as db:
        slot = await get_slot(db, date, time)
        
        if not slot or not slot['is_available']:
            await callback.message.answer("❌ К сожалению, этот слот только что заняли.\nПожалуйста, выберите другое время.")
            await state.clear()
            return
        
        booking_id = await create_booking(db, callback.from_user.id, service_id, date, time)
        await mark_slot_unavailable(db, slot['id'])
        await db.commit()
        
        service = await get_service(db, service_id)
    
    await callback.message.answer(
        f"✅ Запись подтверждена!\n\nУслуга: {service['name']}\nДата: {datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m.%Y')}\nВремя: {time}\nЦена: {service['price']}₽\n\nЖдем вас!",
        reply_markup=get_main_keyboard()
    )
    
    await state.clear()
    await callback.answer()


async def price_handler(message: types.Message):
    async with get_db() as db:
        services = await get_all_services(db)
    
    if not services:
        await message.answer("❌ В данный момент нет доступных услуг")
        return
    
    price_list = "💰 **Прайс-лист:**\n\n"
    for service in services:
        price_list += f"• {service['name']} - {service['price']}₽\n"
    
    await message.answer(price_list, parse_mode="Markdown")


async def profile_handler(message: types.Message):
    async with get_db() as db:
        user = await get_user(db, message.from_user.id)
        booking = await get_user_booking(db, message.from_user.id)
    
    if not user:
        await message.answer("❌ Ваш профиль не найден. Нажмите /start")
        return
    
    profile_text = f"👤 **Ваш профиль**\n\nИмя: {user.get('name', 'Не указано')}\nТелефон: {user.get('phone', 'Не указан')}\n\n"
    
    if booking:
        profile_text += f"**Ваша активная запись:**\nДата: {booking['date']}\nВремя: {booking['time']}\nУслуга: {booking['service_name']}\nЦена: {booking['service_price']}₽"
    else:
        profile_text += "У вас нет активных записей"
    
    await message.answer(profile_text, parse_mode="Markdown")


async def admin_add_service_handler(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer("➕ Добавление новой услуги.\n\nВведите название услуги:")
    await AdminServiceState.adding_name.set()


async def process_service_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['service_name'] = message.text
    
    await message.answer("Введите цену услуги (только число, например 500):")
    await AdminServiceState.adding_price.set()


async def process_service_price(message: types.Message, state: FSMContext):
    try:
        price = int(message.text)
        if price <= 0:
            raise ValueError()
        
        async with state.proxy() as data:
            service_name = data['service_name']
            service_price = price
        
        async with get_db() as db:
            await add_service(db, service_name, service_price)
            await db.commit()
        
        await message.answer(f"✅ Услуга '{service_name}' успешно добавлена!\nЦена: {service_price}₽", reply_markup=get_admin_keyboard())
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат цены. Введите положительное целое число:")


async def admin_add_slot_handler(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer("➕ Добавление временного слота.\n\nВведите дату в формате ДД.ММ.ГГГГ (например, 25.12.2024):")
    await AdminSlotState.selecting_date.set()


async def process_slot_date(message: types.Message, state: FSMContext):
    try:
        date_obj = datetime.strptime(message.text, "%d.%m.%Y")
        date_str = date_obj.strftime("%Y-%m-%d")
        
        async with state.proxy() as data:
            data['slot_date'] = date_str
        
        await message.answer("Введите время начала слота в формате ЧЧ:ММ (например, 14:30):")
        await AdminSlotState.selecting_time.set()
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ:")


async def process_slot_time(message: types.Message, state: FSMContext):
    try:
        time_obj = datetime.strptime(message.text, "%H:%M").time()
        time_str = time_obj.strftime("%H:%M")
        
        async with state.proxy() as data:
            date_str = data['slot_date']
        
        async with get_db() as db:
            existing_slot = await get_slot(db, date_str, time_str)
            
            if existing_slot:
                await message.answer("❌ Такой слот уже существует.\nПожалуйста, выберите другое время или дату.", reply_markup=get_admin_keyboard())
                await state.clear()
                return
            
            await create_slot(db, date_str, time_str)
            await db.commit()
        
        await message.answer(f"✅ Слот успешно создан!\n\nДата: {datetime.strptime(date_str, '%Y-%m-%d').strftime('%d.%m.%Y')}\nВремя: {time_str}", reply_markup=get_admin_keyboard())
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ:")


async def admin_bookings_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer("📊 Функция просмотра всех записей будет доступна в следующем обновлении.\nСейчас вы можете добавлять слоты и услуги через соответствующие кнопки.")


def register_handlers(dp: Dispatcher):
    dp.message.register(start_handler, CommandStart())
    dp.message.register(book_handler, F.text == "📅 Записаться")
    dp.message.register(price_handler, F.text == "💰 Прайс")
    dp.message.register(profile_handler, F.text == "👤 Профиль")
    
    dp.callback_query.register(process_service_selection, F.data.startswith("service_"))
    dp.callback_query.register(process_date_selection, F.data.startswith("date_"))
    dp.callback_query.register(process_time_selection, F.data.startswith("time_"))
    dp.callback_query.register(process_confirmation, F.data.in_(["confirm", "cancel"]))
    
    dp.message.register(admin_add_service_handler, F.text == "Услуги: добавить")
    dp.message.register(admin_add_slot_handler, F.text == "Добавить слот")
    dp.message.register(admin_bookings_handler, F.text == "Все записи")
    
    dp.message.register(process_service_name, AdminServiceState.adding_name)
    dp.message.register(process_service_price, AdminServiceState.adding_price)
    dp.message.register(process_slot_date, AdminSlotState.selecting_date)
    dp.message.register(process_slot_time, AdminSlotState.selecting_time)
