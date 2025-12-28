"""
Telegram Sales Bot - Главный файл
Бот-менеджер продаж с интеграцией Robokassa
"""
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from config import load_config
from handlers import setup_routers
from database import init_db
from webhook_server import start_webhook_server


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""
    # Загрузка конфигурации
    config = load_config()
    
    # Инициализация базы данных
    await init_db()
    logger.info("📦 База данных инициализирована")
    
    # Инициализация бота
    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    
    # Инициализация диспетчера
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Подключение роутеров
    dp.include_router(setup_routers())
    
    # Запуск webhook сервера для Robokassa
    webhook_runner = await start_webhook_server(bot)
    logger.info(f"🌐 Webhook сервер запущен на порту {config.webhook.port}")
    
    # Логирование запуска
    logger.info("🚀 Бот запущен!")
    logger.info(f"📦 Магазин Robokassa: {config.robokassa.merchant_login}")
    logger.info(f"🧪 Тестовый режим: {'Да' if config.robokassa.is_test else 'Нет'}")
    
    if config.bot.admin_ids:
        logger.info(f"📩 Заявки будут отправляться на ID: {config.bot.admin_ids}")
    else:
        logger.warning("⚠️ ADMIN_IDS не указаны! Укажите Telegram ID для получения заявок.")
    
    # Запуск поллинга
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await webhook_runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
