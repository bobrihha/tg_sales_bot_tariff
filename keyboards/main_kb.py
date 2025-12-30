"""
Клавиатуры бота
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from data.tariffs import get_all_operators, get_tariffs_by_operator, PaymentMethod


def main_menu_kb() -> ReplyKeyboardMarkup:
    """Главное меню"""
    builder = ReplyKeyboardBuilder()
    builder.row(
        KeyboardButton(text="📋 Тарифы"),
        KeyboardButton(text="ℹ️ О нас"),
    )
    builder.row(
        KeyboardButton(text="❓ FAQ"),
        KeyboardButton(text="💬 Связаться"),
    )
    return builder.as_markup(resize_keyboard=True)


def operators_kb() -> InlineKeyboardMarkup:
    """Клавиатура выбора оператора"""
    builder = InlineKeyboardBuilder()
    operators = get_all_operators()

    for operator in operators:
        builder.row(
            InlineKeyboardButton(
                text=operator.name,
                callback_data=f"operator:{operator.id}"
            )
        )

    return builder.as_markup()


def tariffs_kb(operator_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора тарифа"""
    builder = InlineKeyboardBuilder()
    tariffs = get_tariffs_by_operator(operator_id, include_hidden=False)

    for tariff in tariffs:
        builder.row(
            InlineKeyboardButton(
                text=f"{tariff.name} — {tariff.connection_price:,} ₽",
                callback_data=f"tariff:{tariff.id}"
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="⬅️ К операторам",
            callback_data="back_to_operators"
        )
    )

    return builder.as_markup()


def tariff_action_kb(tariff_id: int, operator_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с тарифом"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Оформить заявку",
            callback_data=f"order:{tariff_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к тарифам",
            callback_data=f"back_to_operator:{operator_id}"
        )
    )
    return builder.as_markup()


def order_mode_kb(tariff_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора типа заявки"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🔁 Перенос номера",
            callback_data=f"order_mode:transfer:{tariff_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🆕 Новый номер",
            callback_data=f"order_mode:new:{tariff_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"tariff:{tariff_id}"
        )
    )
    return builder.as_markup()


def confirm_order_kb(tariff_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения заказа"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💳 Перейти к оплате",
            callback_data=f"pay:{tariff_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Отменить",
            callback_data="cancel_order"
        )
    )
    return builder.as_markup()


def payment_link_kb(payment_url: str) -> InlineKeyboardMarkup:
    """Клавиатура со ссылкой на оплату"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="💳 Оплатить через Robokassa",
            url=payment_url
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="✅ Я оплатил",
            callback_data="check_payment"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Отменить",
            callback_data="cancel_order"
        )
    )
    return builder.as_markup()


def back_to_operators_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата к операторам"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⬅️ К операторам",
            callback_data="back_to_operators"
        )
    )
    return builder.as_markup()


def back_to_main_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата в главное меню"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Главное меню",
            callback_data="main_menu"
        )
    )
    return builder.as_markup()


def cancel_kb() -> InlineKeyboardMarkup:
    """Кнопка отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена",
            callback_data="cancel"
        )
    )
    return builder.as_markup()


# ============== Direct Payment Keyboards ==============

def payment_methods_kb(methods: list[PaymentMethod], tariff_id: int) -> InlineKeyboardMarkup:
    """Клавиатура выбора банка для оплаты"""
    builder = InlineKeyboardBuilder()
    for method in methods:
        builder.row(
            InlineKeyboardButton(
                text=f"🏦 {method.name}",
                callback_data=f"select_payment:{method.id}:{tariff_id}"
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="❌ Отменить",
            callback_data="cancel_order"
        )
    )
    return builder.as_markup()


def payment_details_kb(order_id: int) -> InlineKeyboardMarkup:
    """Клавиатура после показа реквизитов: Я оплатил / Отмена"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Я оплатил",
            callback_data=f"i_paid:{order_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Отменить",
            callback_data="cancel_order"
        )
    )
    return builder.as_markup()


def admin_confirm_payment_kb(order_id: int, user_id: int) -> InlineKeyboardMarkup:
    """Клавиатура для админа: Подтвердить оплату"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Подтвердить оплату",
            callback_data=f"confirm_payment:{order_id}:{user_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="❌ Отклонить",
            callback_data=f"reject_payment:{order_id}:{user_id}"
        )
    )
    return builder.as_markup()

