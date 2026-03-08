"""
Инициализация пакета database
"""
from .db import get_db, init_db
from .models import (
    create_tables,
    add_default_services,
    # Users
    get_user,
    create_user,
    update_user_phone,
    # Services
    get_all_services,
    get_service,
    add_service,
    update_service,
    delete_service,
    # Slots
    create_slot,
    get_slot,
    get_available_slots,
    get_all_slots_by_date,
    mark_slot_unavailable,
    mark_slot_available,
    delete_slot,
    delete_slots_by_date,
    get_dates_with_available_slots,
    # Bookings
    create_booking,
    get_user_booking,
    get_booking_by_id,
    get_bookings_by_date,
    cancel_booking,
    delete_booking,
    update_booking_reminder,
    get_bookings_for_reminders,
)

__all__ = [
    'get_db', 'init_db',
    'create_tables', 'add_default_services',
    'get_user', 'create_user', 'update_user_phone',
    'get_all_services', 'get_service', 'add_service', 'update_service', 'delete_service',
    'create_slot', 'get_slot', 'get_available_slots', 'get_all_slots_by_date',
    'mark_slot_unavailable', 'mark_slot_available', 'delete_slot', 'delete_slots_by_date',
    'get_dates_with_available_slots',
    'create_booking', 'get_user_booking', 'get_booking_by_id', 'get_bookings_by_date',
    'cancel_booking', 'delete_booking', 'update_booking_reminder', 'get_bookings_for_reminders',
]