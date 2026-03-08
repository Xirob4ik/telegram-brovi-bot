"""
Инициализация пакета handlers
"""
# Импортируем роутеры для регистрации в основном боте
from .start import router as start_router
from .booking import router as booking_router
from .admin import router as admin_router
from .prices import router as prices_router
from .portfolio import router as portfolio_router
from .cancel_booking import router as cancel_router

__all__ = [
    'start_router',
    'booking_router',
    'admin_router',
    'prices_router',
    'portfolio_router',
    'cancel_router'
]