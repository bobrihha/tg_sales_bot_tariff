"""
Клавиатуры админ-меню
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from data.tariffs import Operator, Tariff


def admin_main_kb() -> InlineKeyboardMarkup:
    """Главное меню админа"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏷️ Операторы", callback_data="admin:operators")
    )
    builder.row(
        InlineKeyboardButton(text="📦 Тарифы", callback_data="admin:tariffs")
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Главное меню", callback_data="main_menu")
    )
    return builder.as_markup()


def admin_operators_kb(operators: list[Operator]) -> InlineKeyboardMarkup:
    """Список операторов"""
    builder = InlineKeyboardBuilder()
    for operator in operators:
        builder.row(
            InlineKeyboardButton(
                text=operator.name,
                callback_data=f"admin:operator:{operator.id}"
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="➕ Добавить оператора",
            callback_data="admin:operator_add"
        )
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back_main")
    )
    return builder.as_markup()


def admin_operator_actions_kb(operator_id: int) -> InlineKeyboardMarkup:
    """Действия с оператором"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🗑️ Удалить",
            callback_data=f"admin:operator_delete:{operator_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:operators")
    )
    return builder.as_markup()


def admin_tariffs_operators_kb(operators: list[Operator]) -> InlineKeyboardMarkup:
    """Выбор оператора для управления тарифами"""
    builder = InlineKeyboardBuilder()
    for operator in operators:
        builder.row(
            InlineKeyboardButton(
                text=operator.name,
                callback_data=f"admin:tariffs_operator:{operator.id}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:back_main")
    )
    return builder.as_markup()


def admin_tariffs_kb(operator_id: int, tariffs: list[Tariff]) -> InlineKeyboardMarkup:
    """Список тарифов оператора"""
    builder = InlineKeyboardBuilder()
    for tariff in tariffs:
        status = "👁️" if tariff.is_public else "🙈"
        builder.row(
            InlineKeyboardButton(
                text=f"{status} {tariff.name}",
                callback_data=f"admin:tariff:{tariff.id}"
            )
        )
    builder.row(
        InlineKeyboardButton(
            text="➕ Добавить тариф",
            callback_data=f"admin:tariff_add:{operator_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:tariffs")
    )
    return builder.as_markup()


def admin_tariff_actions_kb(
    tariff_id: int,
    operator_id: int,
    is_public: bool,
) -> InlineKeyboardMarkup:
    """Действия с тарифом"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✏️ Редактировать",
            callback_data=f"admin:tariff_edit:{tariff_id}"
        )
    )
    toggle_text = "🙈 Скрыть" if is_public else "👁️ Показать"
    builder.row(
        InlineKeyboardButton(
            text=toggle_text,
            callback_data=f"admin:tariff_toggle:{tariff_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🗑️ Удалить",
            callback_data=f"admin:tariff_delete:{tariff_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"admin:tariffs_operator:{operator_id}"
        )
    )
    return builder.as_markup()


def admin_tariff_edit_kb(tariff_id: int) -> InlineKeyboardMarkup:
    """Меню редактирования тарифа"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✏️ Название",
            callback_data=f"admin:tariff_edit_name:{tariff_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📝 Описание",
            callback_data=f"admin:tariff_edit_desc:{tariff_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="📅 Абонплата",
            callback_data=f"admin:tariff_edit_monthly:{tariff_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="💳 Стоимость подключения",
            callback_data=f"admin:tariff_edit_price:{tariff_id}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад",
            callback_data=f"admin:tariff:{tariff_id}"
        )
    )
    return builder.as_markup()


def admin_tariff_visibility_kb() -> InlineKeyboardMarkup:
    """Выбор видимости тарифа"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Публичный",
            callback_data="admin:tariff_visibility:1"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="🙈 Скрытый",
            callback_data="admin:tariff_visibility:0"
        )
    )
    return builder.as_markup()
