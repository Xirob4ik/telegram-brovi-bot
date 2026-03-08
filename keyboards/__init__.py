"""
Инициализация пакета keyboards
"""
from .inline import (
    get_main_menu_kb,
    get_calendar_kb,
    get_time_slots_kb,
    get_services_kb,
    get_confirm_booking_kb,
    get_subscription_kb,
    get_admin_menu_kb,
    get_admin_slots_kb,
    get_admin_services_kb,
    get_cancel_booking_kb,
    get_back_kb
)

__all__ = [
    'get_main_menu_kb', 'get_calendar_kb', 'get_time_slots_kb',
    'get_services_kb', 'get_confirm_booking_kb', 'get_subscription_kb',
    'get_admin_menu_kb', 'get_admin_slots_kb', 'get_admin_services_kb',
    'get_cancel_booking_kb', 'get_back_kb'
]