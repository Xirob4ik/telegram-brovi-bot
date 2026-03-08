from aiogram import types, Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from models import User, Service, Slot, Appointment, get_db
from keyboards import get_main_keyboard, get_admin_keyboard, get_services_inline_keyboard, get_slots_inline_keyboard, get_confirm_keyboard
from utils.subscription import check_subscription
from config import ADMIN_IDS
from datetime import datetime, timedelta

class BookingState(StatesGroup):
    selecting_service = State()
    selecting_slot = State()
    confirming = State()

class AdminServiceState(StatesGroup):
    adding_name = State()
    adding_description = State()
    adding_price = State()
    adding_duration = State()

class AdminSlotState(StatesGroup):
    selecting_service_for_slot = State()
    selecting_date = State()
    selecting_time = State()

async def start_handler(message: types.Message, state: FSMContext):
    db = get_db()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
            db.add(user)
            db.commit()
        
        await state.finish()
        
        is_subscribed = await check_subscription(message.from_user.id, message.bot)
        
        if message.from_user.id in ADMIN_IDS:
            await message.answer(
                f"Привет, {message.from_user.full_name}!\n\n"
                "Выберите действие:",
                reply_markup=get_admin_keyboard()
            )
        else:
            await message.answer(
                f"Привет, {message.from_user.full_name}!\n\n"
                "Выберите действие:",
                reply_markup=get_main_keyboard()
            )
    finally:
        db.close()

async def book_handler(message: types.Message, state: FSMContext):
    is_subscribed = await check_subscription(message.from_user.id, message.bot)
    if not is_subscribed:
        await message.answer(
            "❌ Для записи необходимо подписаться на наш канал!\n"
            "Подпишитесь и нажмите /start"
        )
        return
    
    db = get_db()
    try:
        services = db.query(Service).filter(Service.is_active == True).all()
        
        if not services:
            await message.answer("❌ В данный момент нет доступных услуг")
            return
        
        await BookingState.selecting_service.set()
        await message.answer(
            "Выберите услугу:",
            reply_markup=get_services_inline_keyboard(services)
        )
    finally:
        db.close()

async def process_service_selection(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "cancel":
        await state.finish()
        await callback.message.answer("Запись отменена", reply_markup=get_main_keyboard())
        return
    
    service_id = int(callback.data.split("_")[-1])
    
    async with state.proxy() as data:
        data['service_id'] = service_id
    
    db = get_db()
    try:
        # Получаем свободные слоты для выбранной услуги
        slots = db.query(Slot).filter(
            Slot.service_id == service_id,
            Slot.is_available == True,
            Slot.is_booked == False
        ).order_by(Slot.start_time).all()
        
        if not slots:
            await callback.message.answer(
                "❌ Нет доступных слотов для этой услуги.\n"
                "Попробуйте выбрать другую услугу или время."
            )
            await state.finish()
            return
        
        await BookingState.selecting_slot.set()
        await callback.message.answer(
            "Выберите удобное время:",
            reply_markup=get_slots_inline_keyboard(slots)
        )
    finally:
        db.close()
    
    await callback.answer()

async def process_slot_selection(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "cancel":
        await state.finish()
        await callback.message.answer("Запись отменена", reply_markup=get_main_keyboard())
        return
    
    slot_id = int(callback.data.split("_")[-1])
    
    db = get_db()
    try:
        slot = db.query(Slot).filter(
            Slot.id == slot_id,
            Slot.is_available == True,
            Slot.is_booked == False
        ).first()
        
        if not slot:
            await callback.message.answer(
                "❌ Этот слот уже занят или недоступен.\n"
                "Пожалуйста, выберите другой."
            )
            await state.finish()
            return
        
        service = db.query(Service).filter(Service.id == slot.service_id).first()
        
        async with state.proxy() as data:
            data['slot_id'] = slot_id
            data['service_id'] = slot.service_id
        
        await BookingState.confirming.set()
        
        time_str = slot.start_time.strftime("%d.%m.%Y в %H:%M")
        await callback.message.answer(
            f"📋 Подтверждение записи:\n\n"
            f"Услуга: {service.name}\n"
            f"Цена: {service.price}₽\n"
            f"Время: {time_str}\n\n"
            f"Подтвердить запись?",
            reply_markup=get_confirm_keyboard()
        )
    finally:
        db.close()
    
    await callback.answer()

async def process_confirmation(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "cancel":
        await state.finish()
        await callback.message.answer("Запись отменена", reply_markup=get_main_keyboard())
        return
    
    if callback.data != "confirm_booking":
        return
    
    db = get_db()
    try:
        async with state.proxy() as data:
            slot_id = data.get('slot_id')
            service_id = data.get('service_id')
        
        if not slot_id or not service_id:
            await callback.message.answer("❌ Ошибка: данные записи не найдены")
            await state.finish()
            return
        
        # Проверяем слот еще раз перед бронированием
        slot = db.query(Slot).filter(
            Slot.id == slot_id,
            Slot.is_available == True,
            Slot.is_booked == False
        ).first()
        
        if not slot:
            await callback.message.answer(
                "❌ К сожалению, этот слот только что заняли.\n"
                "Пожалуйста, выберите другое время."
            )
            await state.finish()
            return
        
        # Находим или создаем пользователя
        user = db.query(User).filter(User.telegram_id == callback.from_user.id).first()
        if not user:
            user = User(
                telegram_id=callback.from_user.id,
                username=callback.from_user.username,
                full_name=callback.from_user.full_name
            )
            db.add(user)
            db.commit()
        
        # Создаем запись
        appointment = Appointment(
            user_id=user.id,
            slot_id=slot_id,
            service_id=service_id,
            status='confirmed'
        )
        db.add(appointment)
        
        # Помечаем слот как занятый
        slot.is_available = False
        slot.is_booked = True
        
        db.commit()
        
        time_str = slot.start_time.strftime("%d.%m.%Y в %H:%M")
        service = db.query(Service).filter(Service.id == service_id).first()
        
        await callback.message.answer(
            f"✅ Запись подтверждена!\n\n"
            f"Услуга: {service.name}\n"
            f"Время: {time_str}\n"
            f"Цена: {service.price}₽\n\n"
            f"Ждем вас!",
            reply_markup=get_main_keyboard()
        )
        
        await state.finish()
        
    except Exception as e:
        db.rollback()
        await callback.message.answer(f"❌ Произошла ошибка при создании записи: {e}")
        await state.finish()
    finally:
        db.close()
    
    await callback.answer()

async def price_handler(message: types.Message):
    db = get_db()
    try:
        services = db.query(Service).filter(Service.is_active == True).all()
        
        if not services:
            await message.answer("❌ В данный момент нет доступных услуг")
            return
        
        price_list = "💰 **Прайс-лист:**\n\n"
        for service in services:
            price_list += f"• {service.name}\n"
            if service.description:
                price_list += f"  _{service.description}_\n"
            price_list += f"  Цена: {service.price}₽ ({service.duration} мин)\n\n"
        
        await message.answer(price_list, parse_mode="Markdown")
    finally:
        db.close()

async def profile_handler(message: types.Message):
    db = get_db()
    try:
        user = db.query(User).filter(User.telegram_id == message.from_user.id).first()
        
        if not user:
            await message.answer("❌ Ваш профиль не найден. Нажмите /start")
            return
        
        appointments = db.query(Appointment).filter(
            Appointment.user_id == user.id
        ).order_by(Appointment.created_at.desc()).limit(5).all()
        
        profile_text = f"👤 **Ваш профиль**\n\n"
        profile_text += f"Имя: {user.full_name or 'Не указано'}\n"
        profile_text += f"Username: @{user.username or 'Не указано'}\n\n"
        
        if appointments:
            profile_text += "**Ваши последние записи:**\n"
            for apt in appointments:
                slot = db.query(Slot).filter(Slot.id == apt.slot_id).first()
                service = db.query(Service).filter(Service.id == apt.service_id).first()
                if slot and service:
                    time_str = slot.start_time.strftime("%d.%m.%Y %H:%M")
                    profile_text += f"• {service.name} - {time_str} [{apt.status}]\n"
        else:
            profile_text += "У вас пока нет записей"
        
        await message.answer(profile_text, parse_mode="Markdown")
    finally:
        db.close()

async def info_handler(message: types.Message):
    await message.answer(
        "ℹ️ **Информация о нас**\n\n"
        "Мы предоставляем качественные услуги парикмахерского сервиса.\n"
        "Работаем ежедневно с 10:00 до 22:00.\n\n"
        "Для записи выберите '📅 Записаться' в главном меню."
    )

# Admin handlers
async def admin_add_service_handler(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer(
        "Добавление новой услуги.\n\n"
        "Введите название услуги:"
    )
    await AdminServiceState.adding_name.set()

async def process_service_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['service_name'] = message.text
    
    await message.answer("Введите описание услуги (или отправьте '-' чтобы пропустить):")
    await AdminServiceState.adding_description.set()

async def process_service_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        if message.text == '-':
            data['service_description'] = None
        else:
            data['service_description'] = message.text
    
    await message.answer("Введите цену услуги (только число, например 500):")
    await AdminServiceState.adding_price.set()

async def process_service_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError()
        
        async with state.proxy() as data:
            data['service_price'] = price
        
        await message.answer("Введите длительность услуги в минутах (например, 30):")
        await AdminServiceState.adding_duration.set()
    except ValueError:
        await message.answer("❌ Неверный формат цены. Введите положительное число:")

async def process_service_duration(message: types.Message, state: FSMContext):
    try:
        duration = int(message.text)
        if duration <= 0:
            raise ValueError()
        
        db = get_db()
        try:
            async with state.proxy() as data:
                new_service = Service(
                    name=data['service_name'],
                    description=data.get('service_description'),
                    price=data['service_price'],
                    duration=duration,
                    is_active=True
                )
                db.add(new_service)
                db.commit()
            
            await message.answer(
                f"✅ Услуга '{data['service_name']}' успешно добавлена!\n"
                f"Цена: {data['service_price']}₽\n"
                f"Длительность: {duration} мин",
                reply_markup=get_admin_keyboard()
            )
            await state.finish()
        finally:
            db.close()
            
    except ValueError:
        await message.answer("❌ Неверный формат длительности. Введите положительное целое число:")

async def admin_services_list_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    db = get_db()
    try:
        services = db.query(Service).all()
        
        if not services:
            await message.answer("❌ Услуги пока не добавлены")
            return
        
        text = "📝 **Список услуг:**\n\n"
        for service in services:
            status = "✅" if service.is_active else "❌"
            text += f"{status} {service.name} - {service.price}₽ ({service.duration} мин)\n"
        
        await message.answer(text, parse_mode="Markdown")
    finally:
        db.close()

async def admin_add_slot_handler(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    db = get_db()
    try:
        services = db.query(Service).filter(Service.is_active == True).all()
        
        if not services:
            await message.answer("❌ Сначала добавьте услуги")
            return
        
        keyboard = InlineKeyboardMarkup(row_width=1)
        for service in services:
            keyboard.add(InlineKeyboardButton(
                service.name,
                callback_data=f"admin_slot_service_{service.id}"
            ))
        keyboard.add(InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
        
        await message.answer("Выберите услугу для создания слота:", reply_markup=keyboard)
        await AdminSlotState.selecting_service_for_slot.set()
    finally:
        db.close()

async def process_admin_slot_service(callback: types.CallbackQuery, state: FSMContext):
    if callback.data == "cancel":
        await state.finish()
        await callback.message.answer("Отменено", reply_markup=get_admin_keyboard())
        return
    
    service_id = int(callback.data.split("_")[-1])
    
    async with state.proxy() as data:
        data['slot_service_id'] = service_id
    
    await callback.message.answer(
        "Введите дату слота в формате ДД.ММ.ГГГГ (например, 25.12.2024):"
    )
    await AdminSlotState.selecting_date.set()
    await callback.answer()

async def process_slot_date(message: types.Message, state: FSMContext):
    try:
        date_obj = datetime.strptime(message.text, "%d.%m.%Y")
        
        async with state.proxy() as data:
            data['slot_date'] = date_obj
        
        await message.answer(
            "Введите время начала слота в формате ЧЧ:ММ (например, 14:30):"
        )
        await AdminSlotState.selecting_time.set()
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте ДД.ММ.ГГГГ:")

async def process_slot_time(message: types.Message, state: FSMContext):
    try:
        time_obj = datetime.strptime(message.text, "%H:%M").time()
        
        db = get_db()
        try:
            async with state.proxy() as data:
                date_obj = data['slot_date']
                service_id = data['slot_service_id']
                
                start_datetime = datetime.combine(date_obj.date(), time_obj)
                service = db.query(Service).filter(Service.id == service_id).first()
                end_datetime = start_datetime + timedelta(minutes=service.duration)
                
                # Проверяем нет ли пересекающихся слотов
                existing_slot = db.query(Slot).filter(
                    Slot.service_id == service_id,
                    Slot.start_time == start_datetime
                ).first()
                
                if existing_slot:
                    await message.answer("❌ Слот на это время уже существует!")
                    await state.finish()
                    return
                
                # Создаем новый слот
                new_slot = Slot(
                    service_id=service_id,
                    start_time=start_datetime,
                    end_time=end_datetime,
                    is_available=True,
                    is_booked=False
                )
                db.add(new_slot)
                db.commit()
            
            await message.answer(
                f"✅ Слот успешно добавлен!\n\n"
                f"Услуга: {service.name}\n"
                f"Начало: {start_datetime.strftime('%d.%m.%Y %H:%M')}\n"
                f"Конец: {end_datetime.strftime('%d.%m.%Y %H:%M')}",
                reply_markup=get_admin_keyboard()
            )
            await state.finish()
        finally:
            db.close()
            
    except ValueError:
        await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ:")

async def admin_slots_list_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    db = get_db()
    try:
        slots = db.query(Slot).order_by(Slot.start_time.desc()).limit(20).all()
        
        if not slots:
            await message.answer("❌ Слоты пока не добавлены")
            return
        
        text = "⏰ **Последние слоты:**\n\n"
        for slot in slots:
            service = db.query(Service).filter(Service.id == slot.service_id).first()
            status = "🟢 Свободен" if slot.is_available else "🔴 Занят"
            time_str = slot.start_time.strftime("%d.%m.%Y %H:%M")
            text += f"{status} | {service.name} | {time_str}\n"
        
        await message.answer(text, parse_mode="Markdown")
    finally:
        db.close()

async def admin_stats_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    db = get_db()
    try:
        total_users = db.query(User).count()
        total_appointments = db.query(Appointment).count()
        confirmed_appointments = db.query(Appointment).filter(Appointment.status == 'confirmed').count()
        total_services = db.query(Service).filter(Service.is_active == True).count()
        available_slots = db.query(Slot).filter(Slot.is_available == True).count()
        
        stats_text = "📊 **Статистика:**\n\n"
        stats_text += f"Пользователей: {total_users}\n"
        stats_text += f"Всего записей: {total_appointments}\n"
        stats_text += f"Активных записей: {confirmed_appointments}\n"
        stats_text += f"Услуг: {total_services}\n"
        stats_text += f"Свободных слотов: {available_slots}"
        
        await message.answer(stats_text, parse_mode="Markdown")
    finally:
        db.close()

async def admin_back_handler(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    
    await message.answer(
        "Главное меню:",
        reply_markup=get_admin_keyboard()
    )

def register_handlers(dp: Dispatcher):
    # User handlers
    dp.register_message_handler(start_handler, commands=["start"])
    dp.register_message_handler(book_handler, lambda message: message.text == "📅 Записаться")
    dp.register_message_handler(price_handler, lambda message: message.text == "💰 Прайс-лист")
    dp.register_message_handler(profile_handler, lambda message: message.text == "👤 Мой профиль")
    dp.register_message_handler(info_handler, lambda message: message.text == "ℹ️ Информация")
    
    # Booking callbacks
    dp.register_callback_query_handler(process_service_selection, lambda c: c.data.startswith("select_service_"))
    dp.register_callback_query_handler(process_slot_selection, lambda c: c.data.startswith("select_slot_"))
    dp.register_callback_query_handler(process_confirmation, lambda c: c.data in ["confirm_booking", "cancel"])
    
    # Admin handlers
    dp.register_message_handler(admin_add_service_handler, lambda message: message.text == "📝 Услуги: добавить")
    dp.register_message_handler(admin_services_list_handler, lambda message: message.text == "📝 Услуги: список")
    dp.register_message_handler(admin_add_slot_handler, lambda message: message.text == "⏰ Добавить слот")
    dp.register_message_handler(admin_slots_list_handler, lambda message: message.text == "⏰ Слоты: список")
    dp.register_message_handler(admin_stats_handler, lambda message: message.text == "📊 Статистика")
    dp.register_message_handler(admin_back_handler, lambda message: message.text == "🔙 В главное меню")
    
    # Admin service creation states
    dp.register_message_handler(process_service_name, state=AdminServiceState.adding_name)
    dp.register_message_handler(process_service_description, state=AdminServiceState.adding_description)
    dp.register_message_handler(process_service_price, state=AdminServiceState.adding_price)
    dp.register_message_handler(process_service_duration, state=AdminServiceState.adding_duration)
    
    # Admin slot creation states
    dp.register_message_handler(process_slot_date, state=AdminSlotState.selecting_date)
    dp.register_message_handler(process_slot_time, state=AdminSlotState.selecting_time)
    
    # Admin slot service selection
    dp.register_callback_query_handler(process_admin_slot_service, lambda c: c.data.startswith("admin_slot_service_"))
