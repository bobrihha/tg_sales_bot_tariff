"""
Обработчики платежей - прямая оплата с выбором банка
"""
import time
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards.main_kb import (
    payment_methods_kb,
    payment_details_kb,
    admin_confirm_payment_kb,
    main_menu_kb,
)
from data.tariffs import (
    get_tariff_by_id,
    get_operator_by_id,
    get_active_payment_methods,
    get_payment_method_by_id,
)
from handlers.orders import OrderStates
from config import load_config
from database import (
    create_order,
    get_order_by_id,
    update_order_status,
    update_order_receipt,
    confirm_order_payment,
    reject_order_payment,
)

router = Router()
config = load_config()


class PaymentStates(StatesGroup):
    """Состояния оплаты"""
    waiting_payment_receipt = State()  # Ожидание фото чека


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
    """Выбор способа оплаты (банка)"""
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

    # Получаем активные способы оплаты
    methods = get_active_payment_methods()
    if not methods:
        await callback.message.edit_text(
            "⚠️ <b>Способы оплаты не настроены</b>\n\n"
            "Пожалуйста, свяжитесь с администратором.",
            parse_mode="HTML"
        )
        await callback.answer()
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

    await state.update_data(order_id=order_id, tariff_id=tariff_id)
    await state.set_state(OrderStates.waiting_payment)

    await callback.message.edit_text(
        f"<b>💳 Оплата заказа #{order_id}</b>\n\n"
        f"📡 Оператор: <b>{operator.name if operator else 'Не указан'}</b>\n"
        f"📦 Тариф: <b>{tariff.name}</b>\n"
        f"💰 Сумма к оплате: <b>{tariff.connection_price:,} ₽</b>\n\n"
        f"Выберите банк для оплаты:",
        reply_markup=payment_methods_kb(methods, tariff_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("select_payment:"))
async def select_payment_method(callback: CallbackQuery, state: FSMContext):
    """Показ реквизитов выбранного банка"""
    parts = callback.data.split(":")
    method_id = int(parts[1])
    tariff_id = int(parts[2])

    method = get_payment_method_by_id(method_id)
    if not method:
        await callback.answer("Способ оплаты не найден", show_alert=True)
        return

    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    data = await state.get_data()
    order_id = data.get("order_id")
    
    if not order_id:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    # Сохраняем выбранный способ оплаты
    await state.update_data(selected_payment_method_id=method_id, selected_payment_method_name=method.name)

    await callback.message.edit_text(
        f"<b>💳 Оплата заказа #{order_id}</b>\n\n"
        f"💰 Сумма к оплате: <b>{tariff.connection_price:,} ₽</b>\n\n"
        f"<b>🏦 Банк: {method.name}</b>\n\n"
        f"<b>Реквизиты для оплаты:</b>\n"
        f"{method.details}\n\n"
        f"⚠️ После оплаты нажмите «Я оплатил» и отправьте фото чека.",
        reply_markup=payment_details_kb(order_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("i_paid:"))
async def handle_i_paid(callback: CallbackQuery, state: FSMContext):
    """Клиент нажал 'Я оплатил' - запрос чека"""
    order_id = int(callback.data.split(":")[1])
    
    data = await state.get_data()
    if data.get("order_id") != order_id:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    await state.set_state(PaymentStates.waiting_payment_receipt)
    
    await callback.message.edit_text(
        f"<b>📸 Отправьте фото чека об оплате</b>\n\n"
        f"Заказ: #{order_id}\n\n"
        f"После проверки оплаты администратором вы получите уведомление.",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(PaymentStates.waiting_payment_receipt)
async def process_payment_receipt(message: Message, state: FSMContext, bot: Bot):
    """Обработка фото чека"""
    if not message.photo:
        await message.answer(
            "⚠️ Пожалуйста, отправьте фото чека об оплате.",
            parse_mode="HTML"
        )
        return

    receipt_file_id = message.photo[-1].file_id
    data = await state.get_data()
    order_id = data.get("order_id")
    payment_method_name = data.get("selected_payment_method_name", "Не указан")

    if not order_id:
        await message.answer("Заказ не найден. Начните заново.")
        await state.clear()
        return

    # Сохраняем чек в БД
    await update_order_receipt(order_id, receipt_file_id, payment_method_name)

    # Получаем заказ для отправки админу
    order = await get_order_by_id(order_id)
    if not order:
        await message.answer("Заказ не найден.")
        await state.clear()
        return

    # Уведомляем клиента
    await message.answer(
        f"✅ <b>Чек получен!</b>\n\n"
        f"Заказ: #{order_id}\n"
        f"Способ оплаты: {payment_method_name}\n\n"
        f"Ожидайте подтверждения оплаты администратором.\n"
        f"Мы уведомим вас, когда оплата будет подтверждена.",
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )

    # Отправляем админу запрос на подтверждение
    for admin_id in config.bot.admin_ids:
        try:
            await bot.send_photo(
                chat_id=admin_id,
                photo=receipt_file_id,
                caption=(
                    f"💳 <b>ЗАПРОС НА ПОДТВЕРЖДЕНИЕ ОПЛАТЫ</b>\n\n"
                    f"Заказ: #{order_id}\n"
                    f"Тариф: {order.get('tariff_name')}\n"
                    f"Сумма: {order.get('connection_price'):,} ₽\n"
                    f"Способ оплаты: {payment_method_name}\n\n"
                    f"Клиент: {order.get('full_name')}\n"
                    f"@{order.get('username') or 'отсутствует'}\n\n"
                    f"Проверьте оплату и подтвердите."
                ),
                reply_markup=admin_confirm_payment_kb(order_id, order.get("user_id")),
                parse_mode="HTML"
            )
        except Exception as exc:
            print(f"Ошибка отправки админу {admin_id}: {exc}")

    await state.clear()


@router.callback_query(F.data.startswith("confirm_payment:"))
async def admin_confirm_payment(callback: CallbackQuery, bot: Bot):
    """Админ подтверждает оплату"""
    if callback.from_user.id not in config.bot.admin_ids:
        await callback.answer("Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    order_id = int(parts[1])
    user_id = int(parts[2])

    # Подтверждаем оплату в БД
    await confirm_order_payment(order_id)

    # Получаем заказ
    order = await get_order_by_id(order_id)
    if not order:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    # Уведомляем клиента
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"✅ <b>Оплата подтверждена!</b>\n\n"
                f"Заказ: #{order_id}\n"
                f"Тариф: {order.get('tariff_name')}\n"
                f"Сумма: {order.get('connection_price'):,} ₽\n\n"
                f"Ваша заявка принята в работу.\n"
                f"Мы свяжемся с вами в ближайшее время. 🎉"
            ),
            parse_mode="HTML"
        )
    except Exception as exc:
        print(f"Ошибка отправки клиенту {user_id}: {exc}")

    # Отправляем полную заявку всем админам
    await _send_admin_notification(order, bot, "Оплачено ✅")

    # Обновляем сообщение админа
    await callback.message.edit_caption(
        caption=(
            f"✅ <b>ОПЛАТА ПОДТВЕРЖДЕНА</b>\n\n"
            f"Заказ: #{order_id}\n"
            f"Тариф: {order.get('tariff_name')}\n"
            f"Сумма: {order.get('connection_price'):,} ₽\n"
            f"Способ оплаты: {order.get('payment_method_name')}\n\n"
            f"Клиент уведомлён. Заявка отправлена."
        ),
        parse_mode="HTML"
    )
    await callback.answer("Оплата подтверждена!")


@router.callback_query(F.data.startswith("reject_payment:"))
async def admin_reject_payment(callback: CallbackQuery, bot: Bot):
    """Админ отклоняет оплату"""
    if callback.from_user.id not in config.bot.admin_ids:
        await callback.answer("Нет доступа", show_alert=True)
        return

    parts = callback.data.split(":")
    order_id = int(parts[1])
    user_id = int(parts[2])

    # Отклоняем оплату в БД
    await reject_order_payment(order_id)

    # Получаем заказ
    order = await get_order_by_id(order_id)

    # Уведомляем клиента
    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                f"❌ <b>Оплата не подтверждена</b>\n\n"
                f"Заказ: #{order_id}\n\n"
                f"К сожалению, мы не смогли подтвердить вашу оплату.\n"
                f"Пожалуйста, свяжитесь с нами для уточнения деталей."
            ),
            parse_mode="HTML"
        )
    except Exception as exc:
        print(f"Ошибка отправки клиенту {user_id}: {exc}")

    # Обновляем сообщение админа
    await callback.message.edit_caption(
        caption=(
            f"❌ <b>ОПЛАТА ОТКЛОНЕНА</b>\n\n"
            f"Заказ: #{order_id}\n"
            f"Клиент уведомлён."
        ),
        parse_mode="HTML"
    )
    await callback.answer("Оплата отклонена")


@router.callback_query(F.data == "check_payment")
async def check_payment(callback: CallbackQuery, state: FSMContext, bot: Bot):
    """Обратная совместимость - старая кнопка 'Я оплатил'"""
    data = await state.get_data()
    order_id = data.get("order_id")

    if not order_id:
        await callback.answer("Заказ не найден", show_alert=True)
        return

    # Перенаправляем на новый flow - запрос чека
    await state.set_state(PaymentStates.waiting_payment_receipt)
    
    await callback.message.edit_text(
        f"<b>📸 Отправьте фото чека об оплате</b>\n\n"
        f"Заказ: #{order_id}\n\n"
        f"После проверки оплаты администратором вы получите уведомление.",
        parse_mode="HTML"
    )
    await callback.answer()
