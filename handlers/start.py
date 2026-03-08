"""
Обработчики команд /start и главного меню
"""
from aiogram import Router, F, types, Dispatcher
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from database.db import get_db
from database.models import create_user
from keyboards.inline import get_main_menu_kb, get_main_menu_kb_with_admin, get_subscription_kb
from utils.subscription import check_user_subscription
from config import ADMIN_ID

router = Router()


@router.message(CommandStart())
async def cmd_start(message: types.Message, state: FSMContext):
    """Обработчик команды /start"""
    async with get_db() as db:
        await create_user(db, message.from_user.id, message.from_user.full_name)
        await db.commit()
    
    await state.clear()
    
    if message.from_user.id != ADMIN_ID:
        is_subscribed = await check_user_subscription(message.bot, message.from_user.id)
        
        if not is_subscribed:
            await message.answer(
                "🔔 <b>Для записи необходимо подписаться на канал</b>",
                parse_mode="HTML",
                reply_markup=get_subscription_kb()
            )
            return
    
    await show_main_menu(message)


@router.callback_query(F.data == "main_menu")
@router.callback_query(F.data == "check_subscription")
async def handle_menu_navigation(callback: types.CallbackQuery, state: FSMContext):
    """Навигация по меню и проверка подписки"""
    await state.clear()
    
    if callback.from_user.id != ADMIN_ID:
        is_subscribed = await check_user_subscription(callback.bot, callback.from_user.id)
        
        if not is_subscribed:
            await callback.answer("❗ Сначала подпишитесь на канал", show_alert=True)
            await callback.message.edit_text(
                "🔔 <b>Для записи необходимо подписаться на канал</b>",
                parse_mode="HTML",
                reply_markup=get_subscription_kb()
            )
            return
    
    await callback.message.edit_text(
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=get_main_menu_kb_with_admin() if callback.from_user.id == ADMIN_ID else get_main_menu_kb()
    )
    await callback.answer()


async def show_main_menu(message: types.Message):
    """Показать главное меню"""
    keyboard = get_main_menu_kb_with_admin() if message.from_user.id == ADMIN_ID else get_main_menu_kb()
    
    await message.answer(
        "👋 <b>Добро пожаловать!</b>\n\n"
        "Выберите действие:",
        parse_mode="HTML",
        reply_markup=keyboard
    )


@router.callback_query(F.data == "admin_menu")
async def show_admin_menu(callback: types.CallbackQuery):
    """Показать админ-меню"""
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("🔐 Доступ запрещён", show_alert=True)
        return
    
    from keyboards.inline import get_admin_menu_kb
    await callback.message.edit_text(
        "🛠 <b>Админ-панель</b>",
        parse_mode="HTML",
        reply_markup=get_admin_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    keyboard = get_main_menu_kb_with_admin() if callback.from_user.id == ADMIN_ID else get_main_menu_kb()
    await callback.message.edit_text(
        "📋 <b>Главное меню</b>",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await callback.answer()