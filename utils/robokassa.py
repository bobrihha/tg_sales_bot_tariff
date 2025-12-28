"""
Модуль интеграции с Robokassa
"""
import hashlib
from urllib.parse import urlencode
from typing import Optional
from config import load_config


config = load_config()


def generate_payment_link(
    order_id: int,
    amount: float,
    description: str,
    user_id: int,
    tariff_id: str,
) -> str:
    """
    Генерация ссылки на оплату Robokassa
    
    Args:
        order_id: Уникальный номер заказа
        amount: Сумма оплаты в рублях
        description: Описание заказа
        user_id: Telegram ID пользователя
        tariff_id: ID тарифа
    
    Returns:
        URL для оплаты
    """
    merchant_login = config.robokassa.merchant_login
    password1 = config.robokassa.password1
    
    # Формирование подписи: MerchantLogin:OutSum:InvId:Password1
    signature_string = f"{merchant_login}:{amount:.2f}:{order_id}:{password1}"
    signature = hashlib.md5(signature_string.encode()).hexdigest()
    
    # Дополнительные параметры (передаём user_id и tariff_id)
    # Robokassa передаст их обратно в Result URL
    shp_tariff = tariff_id
    shp_user = user_id
    
    # Подпись с дополнительными параметрами (сортировка по алфавиту)
    signature_string_with_shp = f"{merchant_login}:{amount:.2f}:{order_id}:{password1}:Shp_tariff={shp_tariff}:Shp_user={shp_user}"
    signature = hashlib.md5(signature_string_with_shp.encode()).hexdigest()
    
    params = {
        "MerchantLogin": merchant_login,
        "OutSum": f"{amount:.2f}",
        "InvId": order_id,
        "Description": description,
        "SignatureValue": signature,
        "Shp_tariff": shp_tariff,
        "Shp_user": shp_user,
    }
    
    # Добавляем IsTest если тестовый режим
    if config.robokassa.is_test:
        params["IsTest"] = 1
    
    url = f"{config.robokassa.base_url}?{urlencode(params)}"
    return url


def verify_result_signature(
    out_sum: str,
    inv_id: str,
    signature: str,
    shp_params: dict,
) -> bool:
    """
    Проверка подписи от Robokassa (Result URL)
    
    Args:
        out_sum: Сумма оплаты
        inv_id: Номер заказа
        signature: Подпись от Robokassa
        shp_params: Дополнительные параметры (Shp_*)
    
    Returns:
        True если подпись верна
    """
    password2 = config.robokassa.password2
    
    # Формирование строки для проверки: OutSum:InvId:Password2:Shp_*
    # Shp параметры должны быть отсортированы по алфавиту
    shp_string = ":".join(f"{k}={v}" for k, v in sorted(shp_params.items()))
    
    if shp_string:
        check_string = f"{out_sum}:{inv_id}:{password2}:{shp_string}"
    else:
        check_string = f"{out_sum}:{inv_id}:{password2}"
    
    expected_signature = hashlib.md5(check_string.encode()).hexdigest().upper()
    
    return signature.upper() == expected_signature


def verify_success_signature(
    out_sum: str,
    inv_id: str,
    signature: str,
    shp_params: dict,
) -> bool:
    """
    Проверка подписи от Robokassa (Success URL)
    
    Args:
        out_sum: Сумма оплаты
        inv_id: Номер заказа
        signature: Подпись от Robokassa
        shp_params: Дополнительные параметры (Shp_*)
    
    Returns:
        True если подпись верна
    """
    password1 = config.robokassa.password1
    
    # Для Success URL используется Password1
    shp_string = ":".join(f"{k}={v}" for k, v in sorted(shp_params.items()))
    
    if shp_string:
        check_string = f"{out_sum}:{inv_id}:{password1}:{shp_string}"
    else:
        check_string = f"{out_sum}:{inv_id}:{password1}"
    
    expected_signature = hashlib.md5(check_string.encode()).hexdigest().upper()
    
    return signature.upper() == expected_signature
