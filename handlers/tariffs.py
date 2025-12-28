"""
Обработчики тарифов
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from keyboards.main_kb import operators_kb, tariffs_kb, tariff_action_kb, back_to_operators_kb
from data.tariffs import (
    get_all_operators,
    get_operator_by_id,
    get_tariffs_by_operator,
    get_tariff_by_id,
    format_tariff_info,
)

router = Router()


@router.message(F.text == "📋 Тарифы")
async def show_operators(message: Message):
    """Показать список операторов"""
    operators = get_all_operators()
    if not operators:
        await message.answer(
            "Пока нет доступных операторов.",
            parse_mode="HTML"
        )
        return

    await message.answer(
        "<b>📡 Выберите оператора</b>",
        reply_markup=operators_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "back_to_operators")
async def back_to_operators(callback: CallbackQuery):
    """Вернуться к списку операторов"""
    await callback.message.edit_text(
        "<b>📡 Выберите оператора</b>",
        reply_markup=operators_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("operator:"))
async def show_operator_tariffs(callback: CallbackQuery):
    """Показать тарифы выбранного оператора"""
    operator_id = int(callback.data.split(":")[1])
    operator = get_operator_by_id(operator_id)

    if not operator:
        await callback.answer("Оператор не найден", show_alert=True)
        return

    tariffs = get_tariffs_by_operator(operator_id, include_hidden=False)
    if not tariffs:
        await callback.message.edit_text(
            f"У оператора <b>{operator.name}</b> пока нет тарифов.",
            reply_markup=back_to_operators_kb(),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        f"<b>📦 Тарифы оператора {operator.name}</b>\n\nВыберите тариф:",
        reply_markup=tariffs_kb(operator_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("tariff:"))
async def show_tariff_details(callback: CallbackQuery):
    """Показать детали тарифа"""
    tariff_id = int(callback.data.split(":")[1])
    tariff = get_tariff_by_id(tariff_id)

    if not tariff:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    operator = get_operator_by_id(tariff.operator_id)
    operator_name = operator.name if operator else None
    tariff_info = format_tariff_info(tariff, operator_name)

    await callback.message.edit_text(
        tariff_info,
        reply_markup=tariff_action_kb(tariff_id, tariff.operator_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("back_to_operator:"))
async def back_to_operator(callback: CallbackQuery):
    """Вернуться к тарифам оператора"""
    operator_id = int(callback.data.split(":")[1])
    operator = get_operator_by_id(operator_id)

    if not operator:
        await callback.answer("Оператор не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>📦 Тарифы оператора {operator.name}</b>\n\nВыберите тариф:",
        reply_markup=tariffs_kb(operator_id),
        parse_mode="HTML"
    )
    await callback.answer()
