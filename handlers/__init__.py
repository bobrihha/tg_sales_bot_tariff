"""
Модуль обработчиков
"""
from aiogram import Router

from .start import router as start_router
from .tariffs import router as tariffs_router
from .orders import router as orders_router
from .payments import router as payments_router
from .faq import router as faq_router
from .admin import router as admin_router


def setup_routers() -> Router:
    """Настройка всех роутеров"""
    router = Router()
    router.include_router(start_router)
    router.include_router(tariffs_router)
    router.include_router(orders_router)
    router.include_router(payments_router)
    router.include_router(faq_router)
    router.include_router(admin_router)
    return router
