"""
Инициализация пакета keyboards
"""
from .inline import (
    get_main_keyboard,
    get_admin_keyboard,
    get_services_inline_keyboard,
    get_confirm_keyboard
)

__all__ = [
    'get_main_keyboard',
    'get_admin_keyboard',
    'get_services_inline_keyboard',
    'get_confirm_keyboard'
]
