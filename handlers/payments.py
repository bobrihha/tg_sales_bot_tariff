"""
Обработчики платежей через Robokassa
"""
import time
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

from keyboards.main_kb import payment_link_kb, main_menu_kb
from data.tariffs import get_tariff_by_id, get_operator_by_id
from utils.robokassa import generate_payment_link
from handlers.orders import OrderStates
from config import load_config
from database import create_order, get_order_by_id, update_order_status

router = Router()
config = load_config()


def generate_order_id() -> int:
    """Генерация уникального ID заказа"""
    return int(time.time() * 1000) % 1000000000


def _build_admin_message(order: dict, status_text: str) -> str:
    mode_text = "Перенос номера" if order.get("mode") == "transfer" else "Новый номер"

    lines = [
        "🔔 <b>НОВАЯ ЗАЯВКА!</b>",
        "",
        f"<b>Заказ:</b> #{order['order_id']}",
        f"<b>Оператор:</b> {order.get('operator_name', 'Не указан')}",
        f"<b>Тариф:</b> {order.get('tariff_name', 'Не указан')}",
        f"<b>Стоимость подключения:</b> {order['connection_price']:,} ₽",
    ]

    if order.get("monthly_fee"):
        lines.append(f"<b>Абонплата:</b> {order['monthly_fee']:,} ₽/мес")

    lines.extend([
        "",
        f"<b>Тип заявки:</b> {mode_text}",
    ])

    if order.get("mode") == "transfer":
        lines.append(f"<b>Номер для переноса:</b> {order.get('transfer_phone', 'Не указано')}")

    lines.extend([
        f"<b>ФИО:</b> {order.get('full_name', 'Не указано')}",
        f"<b>Регион/город:</b> {order.get('region_city', 'Не указано')}",
        "",
        f"🆔 Telegram ID: {order.get('user_id')}",
        f"👤 Username: @{order.get('username') or 'отсутствует'}",
        "",
        f"✅ <b>Статус:</b> {status_text}",
    ])

    return "\n".join(lines)


async def _send_admin_notification(order: dict, bot: Bot, status_text: str) -> None:
    if not config.bot.admin_ids:
        return

    admin_message = _build_admin_message(order, status_text)

    for admin_id in config.bot.admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_message,
                parse_mode="HTML"
            )

            photo_1 = order.get("passport_photo_1")
            photo_2 = order.get("passport_photo_2")
            if photo_1:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_1,
                    caption="Паспорт: 1-я страница"
                )
            if photo_2:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_2,
                    caption="Паспорт: 2-я страница (регистрация)"
                )
        except Exception as exc:
            print(f"Ошибка отправки админу {admin_id}: {exc}")


@router.callback_query(F.data.startswith("pay:"))
async def create_payment(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Создание платежа и генерация ссылки Robokassa"""
    tariff_id = int(callback.data.split(":")[1])
    tariff = get_tariff_by_id(tariff_id)

    if not tariff:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    data = await state.get_data()
    required_fields = ["mode", "full_name", "region_city", "passport_photo_1", "passport_photo_2"]
    if any(field not in data for field in required_fields):
        await callback.answer("Данные заявки не заполнены", show_alert=True)
        return
    if data.get("mode") == "transfer" and not data.get("transfer_phone"):
        await callback.answer("Не указан номер для переноса", show_alert=True)
        return

    operator = get_operator_by_id(tariff.operator_id)
    order_id = generate_order_id()

    # Сохраняем заказ в БД
    await create_order(
        order_id=order_id,
        user_id=callback.from_user.id,
        username=callback.from_user.username,
        tariff_id=tariff_id,
        tariff_name=tariff.name,
        operator_id=tariff.operator_id,
        operator_name=operator.name if operator else "Не указан",
        monthly_fee=tariff.monthly_fee,
        connection_price=tariff.connection_price,
        mode=data.get("mode"),
        transfer_phone=data.get("transfer_phone"),
        full_name=data.get("full_name"),
        region_city=data.get("region_city"),
        passport_photo_1=data.get("passport_photo_1"),
        passport_photo_2=data.get("passport_photo_2"),
    )

    await state.update_data(order_id=order_id)
    await state.set_state(OrderStates.waiting_payment)

    # Генерируем ссылку на оплату
    payment_url = generate_payment_link(
        order_id=order_id,
        amount=float(tariff.connection_price),
        description=f"Оплата тарифа: {tariff.name}",
        user_id=callback.from_user.id,
        tariff_id=str(tariff_id),
    )

    await callback.message.edit_text(
        f"<b>💳 Оплата заказа #{order_id}</b>\n\n"
        f"📡 Оператор: <b>{operator.name if operator else 'Не указан'}</b>\n"
        f"📦 Тариф: <b>{tariff.name}</b>\n"
        f"💰 Сумма к оплате: <b>{tariff.connection_price:,} ₽</b>\n\n"
        f"Нажмите кнопку ниже для перехода на страницу оплаты.\n\n"
        f"⚠️ После оплаты нажмите «Я оплатил» для подтверждения.",
        reply_markup=payment_link_kb(payment_url),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "check_payment")
async def check_payment(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Проверка оплаты (ручное подтверждение)"""
    data = await state.get_data()
    order_id = data.get("order_id")

    if not order_id:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    order = await get_order_by_id(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    # Обновляем статус в БД
    await update_order_status(order_id, "paid")
    order["status"] = "paid"

    await callback.message.edit_text(
        f"✅ <b>Заявка отправлена!</b>\n\n"
        f"Заказ #{order_id}\n"
        f"Тариф: {order.get('tariff_name', 'Не указан')}\n"
        f"Сумма: {order['connection_price']:,} ₽\n\n"
        f"Мы проверим оплату и свяжемся с вами в ближайшее время.\n"
        f"Спасибо за покупку! 🎉",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=main_menu_kb()
    )

    await _send_admin_notification(
        order=order,
        bot=bot,
        status_text="Ожидает проверки оплаты"
    )

    await state.clear()
    await callback.answer("Заявка отправлена!")
