"""
Webhook сервер для Robokassa callbacks
Обрабатывает Result URL, Success URL и Fail URL
"""
import logging
from aiohttp import web
from config import load_config
from utils.robokassa import verify_result_signature
from database import get_order_by_id, update_order_status

logger = logging.getLogger(__name__)
config = load_config()

# Глобальная переменная для бота (устанавливается при запуске)
_bot = None


def set_bot(bot):
    """Установить экземпляр бота для отправки уведомлений"""
    global _bot
    _bot = bot


async def robokassa_result(request: web.Request) -> web.Response:
    """
    Result URL - Robokassa отправляет сюда уведомление об успешной оплате
    Это серверный callback, пользователь его не видит
    """
    try:
        # Получаем параметры
        params = await request.post() if request.method == 'POST' else request.query
        
        out_sum = params.get('OutSum', '')
        inv_id = params.get('InvId', '')
        signature = params.get('SignatureValue', '')
        
        # Собираем Shp_ параметры
        shp_params = {}
        for key, value in params.items():
            if key.startswith('Shp_') or key.startswith('shp_'):
                shp_params[key] = value
        
        logger.info(f"Robokassa Result: InvId={inv_id}, OutSum={out_sum}")
        
        # Проверяем подпись
        if not verify_result_signature(out_sum, inv_id, signature, shp_params):
            logger.warning(f"Invalid signature for order {inv_id}")
            return web.Response(text="bad sign", status=400)
        
        # Получаем заказ
        order_id = int(inv_id)
        order = await get_order_by_id(order_id)
        
        if not order:
            logger.warning(f"Order {order_id} not found")
            return web.Response(text="bad order", status=404)
        
        # Обновляем статус
        await update_order_status(order_id, 'paid')
        
        # Уведомляем клиента
        if _bot and order.get('user_id'):
            try:
                await _bot.send_message(
                    chat_id=order['user_id'],
                    text=(
                        f"✅ <b>Оплата получена!</b>\n\n"
                        f"Заказ #{order_id}\n"
                        f"Тариф: {order.get('tariff_name', 'Не указан')}\n"
                        f"Сумма: {float(out_sum):,.0f} ₽\n\n"
                        f"Спасибо за покупку! Мы свяжемся с вами в ближайшее время. 🎉"
                    ),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Failed to notify user: {e}")
        
        # Уведомляем админов
        if _bot and config.bot.admin_ids:
            mode_text = "Перенос номера" if order.get('mode') == 'transfer' else "Новый номер"
            admin_msg = (
                f"💰 <b>ОПЛАТА ПОЛУЧЕНА!</b>\n\n"
                f"<b>Заказ:</b> #{order_id}\n"
                f"<b>Оператор:</b> {order.get('operator_name', 'Не указан')}\n"
                f"<b>Тариф:</b> {order.get('tariff_name', 'Не указан')}\n"
                f"<b>Сумма:</b> {float(out_sum):,.0f} ₽\n\n"
                f"<b>Тип заявки:</b> {mode_text}\n"
                f"<b>ФИО:</b> {order.get('full_name', 'Не указано')}\n"
                f"<b>Регион/город:</b> {order.get('region_city', 'Не указано')}\n\n"
                f"🆔 Telegram ID: {order.get('user_id')}\n"
                f"👤 Username: @{order.get('username') or 'отсутствует'}"
            )
            for admin_id in config.bot.admin_ids:
                try:
                    await _bot.send_message(
                        chat_id=admin_id,
                        text=admin_msg,
                        parse_mode="HTML"
                    )
                    
                    # Отправляем фото паспорта
                    if order.get('passport_photo_1'):
                        await _bot.send_photo(
                            chat_id=admin_id,
                            photo=order['passport_photo_1'],
                            caption="Паспорт: 1-я страница"
                        )
                    if order.get('passport_photo_2'):
                        await _bot.send_photo(
                            chat_id=admin_id,
                            photo=order['passport_photo_2'],
                            caption="Паспорт: 2-я страница (регистрация)"
                        )
                except Exception as e:
                    logger.error(f"Failed to notify admin {admin_id}: {e}")
        
        logger.info(f"Order {order_id} marked as paid")
        return web.Response(text=f"OK{inv_id}")
        
    except Exception as e:
        logger.error(f"Error processing Robokassa result: {e}")
        return web.Response(text="error", status=500)


async def robokassa_success(request: web.Request) -> web.Response:
    """
    Success URL - пользователь перенаправляется сюда после успешной оплаты
    """
    params = request.query
    inv_id = params.get('InvId', 'N/A')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Оплата успешна</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
            .success {{ color: #28a745; font-size: 48px; }}
            h1 {{ color: #333; }}
            p {{ color: #666; }}
        </style>
    </head>
    <body>
        <div class="success">✅</div>
        <h1>Оплата успешна!</h1>
        <p>Заказ #{inv_id}</p>
        <p>Спасибо за покупку! Вернитесь в Telegram-бота.</p>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')


async def robokassa_fail(request: web.Request) -> web.Response:
    """
    Fail URL - пользователь перенаправляется сюда при отмене оплаты
    """
    params = request.query
    inv_id = params.get('InvId', 'N/A')
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Оплата отменена</title>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
            .fail {{ color: #dc3545; font-size: 48px; }}
            h1 {{ color: #333; }}
            p {{ color: #666; }}
        </style>
    </head>
    <body>
        <div class="fail">❌</div>
        <h1>Оплата отменена</h1>
        <p>Заказ #{inv_id}</p>
        <p>Вы можете попробовать оплатить снова в Telegram-боте.</p>
    </body>
    </html>
    """
    return web.Response(text=html, content_type='text/html')


async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint"""
    return web.Response(text="OK")


def create_app() -> web.Application:
    """Создание веб-приложения"""
    app = web.Application()
    
    # Регистрация маршрутов
    app.router.add_route('*', '/robokassa/result', robokassa_result)
    app.router.add_get('/robokassa/success', robokassa_success)
    app.router.add_get('/robokassa/fail', robokassa_fail)
    app.router.add_get('/health', health_check)
    
    return app


async def start_webhook_server(bot=None):
    """Запуск webhook сервера"""
    if bot:
        set_bot(bot)
    
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(
        runner,
        host=config.webhook.host,
        port=config.webhook.port
    )
    
    await site.start()
    logger.info(f"Webhook server started on {config.webhook.host}:{config.webhook.port}")
    
    return runner
