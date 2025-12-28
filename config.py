"""
Конфигурация бота
Загружает настройки из .env файла
"""
import os
from dataclasses import dataclass, field
from typing import List
from dotenv import load_dotenv

# Загрузка переменных окружения из .env
load_dotenv()


@dataclass
class BotConfig:
    """Основные настройки бота"""
    token: str
    admin_ids: List[int] = field(default_factory=list)  # Список ID администраторов


@dataclass
class RobokassaConfig:
    """Настройки Robokassa"""
    merchant_login: str  # Идентификатор магазина
    password1: str  # Пароль #1 для формирования подписи
    password2: str  # Пароль #2 для проверки подписи
    is_test: bool = True  # Тестовый режим
    
    @property
    def base_url(self) -> str:
        """URL для оплаты"""
        return "https://auth.robokassa.ru/Merchant/Index.aspx"


@dataclass
class WebhookConfig:
    """Настройки webhook сервера"""
    host: str
    port: int


@dataclass
class Config:
    """Главная конфигурация"""
    bot: BotConfig
    robokassa: RobokassaConfig
    webhook: WebhookConfig


def _parse_admin_ids(value: str) -> List[int]:
    """Парсинг списка админ ID через запятую"""
    if not value:
        return []
    ids = []
    for part in value.split(","):
        part = part.strip()
        if part.isdigit():
            ids.append(int(part))
    return ids


def load_config() -> Config:
    """Загрузка конфигурации из переменных окружения"""
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        raise ValueError("BOT_TOKEN не указан в .env файле!")
    
    # Поддержка как ADMIN_ID так и ADMIN_IDS
    admin_ids_str = os.getenv("ADMIN_IDS") or os.getenv("ADMIN_ID", "")
    admin_ids = _parse_admin_ids(admin_ids_str)
    
    return Config(
        bot=BotConfig(
            token=bot_token,
            admin_ids=admin_ids,
        ),
        robokassa=RobokassaConfig(
            merchant_login=os.getenv("ROBOKASSA_LOGIN", ""),
            password1=os.getenv("ROBOKASSA_PASSWORD1", ""),
            password2=os.getenv("ROBOKASSA_PASSWORD2", ""),
            is_test=os.getenv("ROBOKASSA_TEST", "true").lower() == "true",
        ),
        webhook=WebhookConfig(
            host=os.getenv("WEBHOOK_HOST", "0.0.0.0"),
            port=int(os.getenv("WEBHOOK_PORT", "8080")),
        ),
    )
