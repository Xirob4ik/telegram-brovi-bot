"""
Модуль напоминаний с использованием APScheduler
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from datetime import datetime, timedelta
from aiogram import Bot
from database.db import get_db
from database.models import get_bookings_for_reminders, update_booking_reminder
from config import REMINDER_HOURS_BEFORE, ADMIN_ID
import logging

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Europe/Moscow")


def init_scheduler():
    """Инициализация планировщика"""
    if not scheduler.running:
        scheduler.start()
        logger.info("✅ APScheduler запущен")


async def schedule_reminder(
    bot: Bot,
    booking_id: int,
    appointment_datetime: datetime,
    user_id: int,
    service_name: str,
    appointment_time: str
):
    """Запланировать напоминание за REMINDER_HOURS_BEFORE до записи"""
    reminder_time = appointment_datetime - timedelta(hours=REMINDER_HOURS_BEFORE)
    now = datetime.now()
    
    if reminder_time <= now:
        logger.info(f"⏭ Напоминание для записи #{booking_id} не создано (время прошло)")
        return None
    
    job_id = f"reminder_{booking_id}"
    
    async def send_reminder():
        try:
            await bot.send_message(
                chat_id=user_id,
                text=f"🔔 <b>Напоминание о записи</b>\n\n"
                     f"Вы записаны на процедуру бровей завтра в <b>{appointment_time}</b>.\n"
                     f"Услуга: {service_name}\n"
                     f"Ждём вас ❤️",
                parse_mode="HTML"
            )
            logger.info(f"📧 Напоминание отправлено пользователю {user_id}")
        except Exception as e:
            logger.error(f"❌ Ошибка отправки напоминания: {e}")
    
    trigger = DateTrigger(run_date=reminder_time)
    job = scheduler.add_job(
        send_reminder,
        trigger=trigger,
        id=job_id,
        replace_existing=True,
        misfire_grace_time=3600
    )
    
    logger.info(f"⏰ Напоминание #{job_id} запланировано на {reminder_time}")
    return job.id


def cancel_reminder(booking_id: int):
    """Отменить напоминание по ID записи"""
    job_id = f"reminder_{booking_id}"
    try:
        scheduler.remove_job(job_id)
        logger.info(f"🗑 Напоминание #{job_id} удалено")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка удаления напоминания: {e}")
        return False


async def restore_reminders(bot: Bot):
    """Восстановить задачи напоминаний после перезапуска бота"""
    now = datetime.now()
    
    for day_offset in range(1, 32):
        check_date = (now + timedelta(days=day_offset)).date()
        check_datetime = datetime.combine(check_date, datetime.min.time())
        
        async with get_db() as db:
            bookings = await get_bookings_for_reminders(db, check_datetime)
            
            for booking in bookings:
                appointment_dt = datetime.strptime(
                    f"{booking['date']} {booking['time']}",
                    "%Y-%m-%d %H:%M"
                )
                reminder_time = appointment_dt - timedelta(hours=REMINDER_HOURS_BEFORE)
                
                if reminder_time > now:
                    await schedule_reminder(
                        bot=bot,
                        booking_id=booking['id'],
                        appointment_datetime=appointment_dt,
                        user_id=booking['telegram_id'],
                        service_name=booking['service_name'],
                        appointment_time=booking['time']
                    )
    
    logger.info("✅ Задачи напоминаний восстановлены")