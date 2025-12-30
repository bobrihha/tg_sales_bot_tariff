"""
Админ-меню для управления операторами и тарифами
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import load_config
from data.tariffs import (
    add_operator,
    add_tariff,
    delete_operator,
    delete_tariff,
    get_all_operators,
    get_operator_by_id,
    get_tariff_by_id,
    get_tariffs_by_operator,
    toggle_tariff_visibility,
    update_tariff,
    # Payment methods
    get_all_payment_methods,
    get_payment_method_by_id,
    add_payment_method,
    update_payment_method,
    delete_payment_method,
    toggle_payment_method,
)
from keyboards.admin_kb import (
    admin_main_kb,
    admin_operators_kb,
    admin_operator_actions_kb,
    admin_tariffs_operators_kb,
    admin_tariffs_kb,
    admin_tariff_actions_kb,
    admin_tariff_edit_kb,
    admin_tariff_visibility_kb,
    # Payment methods
    admin_payment_methods_kb,
    admin_payment_method_actions_kb,
    admin_payment_method_edit_kb,
)

router = Router()
config = load_config()


class AdminStates(StatesGroup):
    """Состояния админ-меню"""
    waiting_operator_name = State()
    waiting_tariff_name = State()
    waiting_tariff_description = State()
    waiting_tariff_monthly_fee = State()
    waiting_tariff_connection_price = State()
    editing_tariff_name = State()
    editing_tariff_description = State()
    editing_tariff_monthly_fee = State()
    editing_tariff_connection_price = State()
    # Payment methods
    waiting_payment_method_name = State()
    waiting_payment_method_details = State()
    editing_payment_method_name = State()
    editing_payment_method_details = State()


def _is_admin(user_id: int) -> bool:
    return user_id in config.bot.admin_ids


def _render_tariff_admin_text(tariff) -> str:
    operator = get_operator_by_id(tariff.operator_id)
    operator_name = operator.name if operator else "Не указан"
    status = "Публичный" if tariff.is_public else "Скрытый"
    monthly_fee = f"{tariff.monthly_fee} ₽/мес" if tariff.monthly_fee else "не указана"

    return (
        f"<b>Тариф:</b> {tariff.name}\n"
        f"<b>Оператор:</b> {operator_name}\n"
        f"<b>Статус:</b> {status}\n"
        f"<b>Абонплата:</b> {monthly_fee}\n"
        f"<b>Стоимость подключения:</b> {tariff.connection_price} ₽\n\n"
        f"<b>Описание:</b>\n{tariff.description}"
    )


@router.message(Command("admin"))
async def admin_start(message: Message, state: FSMContext):
    """Открыть админ-меню"""
    if not _is_admin(message.from_user.id):
        return

    await state.clear()
    await message.answer(
        "<b>⚙️ Админ-меню</b>",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "admin:back_main")
async def admin_back_main(callback: CallbackQuery, state: FSMContext):
    """Назад в админ-меню"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.clear()
    await callback.message.edit_text(
        "<b>⚙️ Админ-меню</b>",
        reply_markup=admin_main_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:operators")
async def admin_show_operators(callback: CallbackQuery):
    """Список операторов"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    operators = get_all_operators()
    await callback.message.edit_text(
        "<b>🏷️ Операторы</b>\n\nВыберите оператора:",
        reply_markup=admin_operators_kb(operators),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:operator_add")
async def admin_add_operator(callback: CallbackQuery, state: FSMContext):
    """Запрос имени нового оператора"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_operator_name)
    await callback.message.edit_text(
        "Введите название оператора:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_operator_name)
async def admin_save_operator(message: Message, state: FSMContext):
    """Сохранение оператора"""
    if not _is_admin(message.from_user.id):
        return

    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не может быть пустым.")
        return

    add_operator(name)
    await state.clear()

    operators = get_all_operators()
    await message.answer(
        "Оператор добавлен.\n\n<b>🏷️ Операторы</b>",
        reply_markup=admin_operators_kb(operators),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:operator:"))
async def admin_operator_details(callback: CallbackQuery):
    """Детали оператора"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    operator_id = int(callback.data.split(":")[2])
    operator = get_operator_by_id(operator_id)
    if not operator:
        await callback.answer("Оператор не найден", show_alert=True)
        return

    await callback.message.edit_text(
        f"<b>Оператор:</b> {operator.name}",
        reply_markup=admin_operator_actions_kb(operator_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:operator_delete:"))
async def admin_delete_operator(callback: CallbackQuery):
    """Удаление оператора"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    operator_id = int(callback.data.split(":")[2])
    delete_operator(operator_id)

    operators = get_all_operators()
    await callback.message.edit_text(
        "Оператор удалён.\n\n<b>🏷️ Операторы</b>",
        reply_markup=admin_operators_kb(operators),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:tariffs")
async def admin_tariffs_choose_operator(callback: CallbackQuery):
    """Выбор оператора для управления тарифами"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    operators = get_all_operators()
    await callback.message.edit_text(
        "<b>📦 Тарифы</b>\n\nВыберите оператора:",
        reply_markup=admin_tariffs_operators_kb(operators),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:tariffs_operator:"))
async def admin_show_tariffs(callback: CallbackQuery):
    """Список тарифов оператора"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    operator_id = int(callback.data.split(":")[2])
    operator = get_operator_by_id(operator_id)
    if not operator:
        await callback.answer("Оператор не найден", show_alert=True)
        return

    tariffs = get_tariffs_by_operator(operator_id, include_hidden=True)
    await callback.message.edit_text(
        f"<b>📦 Тарифы оператора {operator.name}</b>",
        reply_markup=admin_tariffs_kb(operator_id, tariffs),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:tariff_add:"))
async def admin_add_tariff(callback: CallbackQuery, state: FSMContext):
    """Начало добавления тарифа"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    operator_id = int(callback.data.split(":")[2])
    operator = get_operator_by_id(operator_id)
    if not operator:
        await callback.answer("Оператор не найден", show_alert=True)
        return

    await state.update_data(operator_id=operator_id)
    await state.set_state(AdminStates.waiting_tariff_name)

    await callback.message.edit_text(
        f"Введите название тарифа для оператора <b>{operator.name}</b>:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_tariff_name)
async def admin_save_tariff_name(message: Message, state: FSMContext):
    """Сохранение названия тарифа"""
    if not _is_admin(message.from_user.id):
        return

    name = (message.text or "").strip()
    if not name:
        await message.answer("Название тарифа не может быть пустым.")
        return

    await state.update_data(tariff_name=name)
    await state.set_state(AdminStates.waiting_tariff_description)

    await message.answer(
        "Введите описание тарифа (можно с эмодзи и переносами строк):",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_tariff_description)
async def admin_save_tariff_description(message: Message, state: FSMContext):
    """Сохранение описания тарифа"""
    if not _is_admin(message.from_user.id):
        return

    description = (message.text or "").strip()
    if not description:
        await message.answer("Описание не может быть пустым.")
        return

    await state.update_data(tariff_description=description)
    await state.set_state(AdminStates.waiting_tariff_monthly_fee)

    await message.answer(
        "Введите абонплату в рублях (или 0, если не нужно показывать):",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_tariff_monthly_fee)
async def admin_save_tariff_monthly_fee(message: Message, state: FSMContext):
    """Сохранение абонплаты"""
    if not _is_admin(message.from_user.id):
        return

    value = (message.text or "").strip()
    if not value.isdigit():
        await message.answer("Введите число (например 0 или 400).")
        return

    monthly_fee = int(value)
    await state.update_data(tariff_monthly_fee=None if monthly_fee == 0 else monthly_fee)
    await state.set_state(AdminStates.waiting_tariff_connection_price)

    await message.answer(
        "Введите стоимость подключения (разовая оплата) в рублях:",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_tariff_connection_price)
async def admin_save_tariff_connection_price(message: Message, state: FSMContext):
    """Сохранение стоимости подключения"""
    if not _is_admin(message.from_user.id):
        return

    value = (message.text or "").strip()
    if not value.isdigit():
        await message.answer("Введите число (например 1500).")
        return

    connection_price = int(value)
    await state.update_data(tariff_connection_price=connection_price)
    await message.answer(
        "Сделать тариф публичным или скрытым?",
        reply_markup=admin_tariff_visibility_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:tariff_visibility:"))
async def admin_finish_tariff(callback: CallbackQuery, state: FSMContext):
    """Завершение создания тарифа"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    data = await state.get_data()
    operator_id = data.get("operator_id")
    name = data.get("tariff_name")
    description = data.get("tariff_description")
    monthly_fee = data.get("tariff_monthly_fee")
    connection_price = data.get("tariff_connection_price")

    if not all([operator_id, name, description, connection_price is not None]):
        await callback.answer("Данные тарифа не заполнены", show_alert=True)
        return

    is_public = callback.data.split(":")[2] == "1"
    add_tariff(
        operator_id=operator_id,
        name=name,
        description=description,
        monthly_fee=monthly_fee,
        connection_price=connection_price,
        is_public=is_public,
    )

    await state.clear()

    tariffs = get_tariffs_by_operator(operator_id, include_hidden=True)
    await callback.message.edit_text(
        "Тариф добавлен.",
        reply_markup=admin_tariffs_kb(operator_id, tariffs),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:tariff:"))
async def admin_tariff_details(callback: CallbackQuery):
    """Детали тарифа"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    tariff_id = int(callback.data.split(":")[2])
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    text = _render_tariff_admin_text(tariff)
    await callback.message.edit_text(
        text,
        reply_markup=admin_tariff_actions_kb(tariff_id, tariff.operator_id, tariff.is_public),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:tariff_edit:"))
async def admin_tariff_edit_menu(callback: CallbackQuery, state: FSMContext):
    """Меню редактирования тарифа"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.clear()
    tariff_id = int(callback.data.split(":")[2])
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    text = _render_tariff_admin_text(tariff)
    await callback.message.edit_text(
        f"{text}\n\nВыберите, что изменить:",
        reply_markup=admin_tariff_edit_kb(tariff_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:tariff_edit_name:"))
async def admin_tariff_edit_name(callback: CallbackQuery, state: FSMContext):
    """Редактирование названия тарифа"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    tariff_id = int(callback.data.split(":")[2])
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    await state.update_data(edit_tariff_id=tariff_id)
    await state.set_state(AdminStates.editing_tariff_name)
    await callback.message.edit_text(
        f"Текущее название: <b>{tariff.name}</b>\n\nВведите новое название:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:tariff_edit_desc:"))
async def admin_tariff_edit_description(callback: CallbackQuery, state: FSMContext):
    """Редактирование описания тарифа"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    tariff_id = int(callback.data.split(":")[2])
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    await state.update_data(edit_tariff_id=tariff_id)
    await state.set_state(AdminStates.editing_tariff_description)
    await callback.message.edit_text(
        "Введите новое описание тарифа:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:tariff_edit_monthly:"))
async def admin_tariff_edit_monthly_fee(callback: CallbackQuery, state: FSMContext):
    """Редактирование абонплаты"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    tariff_id = int(callback.data.split(":")[2])
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    await state.update_data(edit_tariff_id=tariff_id)
    await state.set_state(AdminStates.editing_tariff_monthly_fee)
    await callback.message.edit_text(
        "Введите абонплату в рублях (или 0, если не нужно показывать):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:tariff_edit_price:"))
async def admin_tariff_edit_price(callback: CallbackQuery, state: FSMContext):
    """Редактирование стоимости подключения"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    tariff_id = int(callback.data.split(":")[2])
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    await state.update_data(edit_tariff_id=tariff_id)
    await state.set_state(AdminStates.editing_tariff_connection_price)
    await callback.message.edit_text(
        "Введите стоимость подключения (разовая оплата) в рублях:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.editing_tariff_name)
async def admin_apply_tariff_name(message: Message, state: FSMContext):
    """Сохранение нового названия"""
    if not _is_admin(message.from_user.id):
        return

    name = (message.text or "").strip()
    if not name:
        await message.answer("Название тарифа не может быть пустым.")
        return

    data = await state.get_data()
    tariff_id = data.get("edit_tariff_id")
    if not tariff_id:
        await message.answer("Тариф не найден. Откройте /admin заново.")
        await state.clear()
        return

    tariff = update_tariff(tariff_id, name=name)
    if not tariff:
        await message.answer("Тариф не найден. Откройте /admin заново.")
        await state.clear()
        return

    await state.clear()
    await message.answer(
        _render_tariff_admin_text(tariff),
        reply_markup=admin_tariff_actions_kb(tariff.id, tariff.operator_id, tariff.is_public),
        parse_mode="HTML"
    )


@router.message(AdminStates.editing_tariff_description)
async def admin_apply_tariff_description(message: Message, state: FSMContext):
    """Сохранение нового описания"""
    if not _is_admin(message.from_user.id):
        return

    description = (message.text or "").strip()
    if not description:
        await message.answer("Описание не может быть пустым.")
        return

    data = await state.get_data()
    tariff_id = data.get("edit_tariff_id")
    if not tariff_id:
        await message.answer("Тариф не найден. Откройте /admin заново.")
        await state.clear()
        return

    tariff = update_tariff(tariff_id, description=description)
    if not tariff:
        await message.answer("Тариф не найден. Откройте /admin заново.")
        await state.clear()
        return

    await state.clear()
    await message.answer(
        _render_tariff_admin_text(tariff),
        reply_markup=admin_tariff_actions_kb(tariff.id, tariff.operator_id, tariff.is_public),
        parse_mode="HTML"
    )


@router.message(AdminStates.editing_tariff_monthly_fee)
async def admin_apply_tariff_monthly_fee(message: Message, state: FSMContext):
    """Сохранение абонплаты"""
    if not _is_admin(message.from_user.id):
        return

    value = (message.text or "").strip()
    if not value.isdigit():
        await message.answer("Введите число (например 0 или 400).")
        return

    monthly_fee = int(value)
    monthly_fee_value = None if monthly_fee == 0 else monthly_fee

    data = await state.get_data()
    tariff_id = data.get("edit_tariff_id")
    if not tariff_id:
        await message.answer("Тариф не найден. Откройте /admin заново.")
        await state.clear()
        return

    tariff = update_tariff(tariff_id, monthly_fee=monthly_fee_value)
    if not tariff:
        await message.answer("Тариф не найден. Откройте /admin заново.")
        await state.clear()
        return

    await state.clear()
    await message.answer(
        _render_tariff_admin_text(tariff),
        reply_markup=admin_tariff_actions_kb(tariff.id, tariff.operator_id, tariff.is_public),
        parse_mode="HTML"
    )


@router.message(AdminStates.editing_tariff_connection_price)
async def admin_apply_tariff_connection_price(message: Message, state: FSMContext):
    """Сохранение стоимости подключения"""
    if not _is_admin(message.from_user.id):
        return

    value = (message.text or "").strip()
    if not value.isdigit():
        await message.answer("Введите число (например 1500).")
        return

    connection_price = int(value)
    data = await state.get_data()
    tariff_id = data.get("edit_tariff_id")
    if not tariff_id:
        await message.answer("Тариф не найден. Откройте /admin заново.")
        await state.clear()
        return

    tariff = update_tariff(tariff_id, connection_price=connection_price)
    if not tariff:
        await message.answer("Тариф не найден. Откройте /admin заново.")
        await state.clear()
        return

    await state.clear()
    await message.answer(
        _render_tariff_admin_text(tariff),
        reply_markup=admin_tariff_actions_kb(tariff.id, tariff.operator_id, tariff.is_public),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:tariff_toggle:"))
async def admin_tariff_toggle(callback: CallbackQuery):
    """Переключить видимость тарифа"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    tariff_id = int(callback.data.split(":")[2])
    tariff = toggle_tariff_visibility(tariff_id)
    if not tariff:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    text = _render_tariff_admin_text(tariff)
    await callback.message.edit_text(
        text,
        reply_markup=admin_tariff_actions_kb(tariff_id, tariff.operator_id, tariff.is_public),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:tariff_delete:"))
async def admin_tariff_delete(callback: CallbackQuery):
    """Удалить тариф"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    tariff_id = int(callback.data.split(":")[2])
    tariff = get_tariff_by_id(tariff_id)
    if not tariff:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    delete_tariff(tariff_id)
    tariffs = get_tariffs_by_operator(tariff.operator_id, include_hidden=True)
    await callback.message.edit_text(
        "Тариф удалён.",
        reply_markup=admin_tariffs_kb(tariff.operator_id, tariffs),
        parse_mode="HTML"
    )
    await callback.answer()


# ============== Payment Methods Handlers ==============

def _render_payment_method_text(method) -> str:
    """Форматирование информации о способе оплаты"""
    status = "✅ Активен" if method.is_active else "❌ Отключен"
    return (
        f"<b>💳 Способ оплаты:</b> {method.name}\n"
        f"<b>Статус:</b> {status}\n\n"
        f"<b>Реквизиты:</b>\n{method.details}"
    )


@router.callback_query(F.data == "admin:payment_methods")
async def admin_show_payment_methods(callback: CallbackQuery, state: FSMContext):
    """Список способов оплаты"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.clear()
    methods = get_all_payment_methods()
    await callback.message.edit_text(
        "<b>💳 Способы оплаты</b>\n\nВыберите способ оплаты для настройки:",
        reply_markup=admin_payment_methods_kb(methods),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin:payment_method_add")
async def admin_add_payment_method(callback: CallbackQuery, state: FSMContext):
    """Запрос названия нового способа оплаты"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.set_state(AdminStates.waiting_payment_method_name)
    await callback.message.edit_text(
        "Введите название способа оплаты (например: <b>Сбербанк</b> или <b>Тинькофф</b>):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.waiting_payment_method_name)
async def admin_save_payment_method_name(message: Message, state: FSMContext):
    """Сохранение названия способа оплаты"""
    if not _is_admin(message.from_user.id):
        return

    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не может быть пустым.")
        return

    await state.update_data(payment_method_name=name)
    await state.set_state(AdminStates.waiting_payment_method_details)

    await message.answer(
        "Введите реквизиты для оплаты.\n\n"
        "Например:\n"
        "<code>Карта: 1234 5678 9012 3456\n"
        "Получатель: Иванов Иван Иванович\n"
        "Банк: Сбербанк</code>",
        parse_mode="HTML"
    )


@router.message(AdminStates.waiting_payment_method_details)
async def admin_save_payment_method_details(message: Message, state: FSMContext):
    """Сохранение реквизитов способа оплаты"""
    if not _is_admin(message.from_user.id):
        return

    details = (message.text or "").strip()
    if not details:
        await message.answer("Реквизиты не могут быть пустыми.")
        return

    data = await state.get_data()
    name = data.get("payment_method_name")
    if not name:
        await message.answer("Ошибка. Начните заново через /admin.")
        await state.clear()
        return

    add_payment_method(name=name, details=details)
    await state.clear()

    methods = get_all_payment_methods()
    await message.answer(
        "✅ Способ оплаты добавлен.\n\n<b>💳 Способы оплаты</b>",
        reply_markup=admin_payment_methods_kb(methods),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:payment_method:"))
async def admin_payment_method_details(callback: CallbackQuery):
    """Детали способа оплаты"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    method_id = int(callback.data.split(":")[2])
    method = get_payment_method_by_id(method_id)
    if not method:
        await callback.answer("Способ оплаты не найден", show_alert=True)
        return

    text = _render_payment_method_text(method)
    await callback.message.edit_text(
        text,
        reply_markup=admin_payment_method_actions_kb(method_id, method.is_active),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:payment_method_toggle:"))
async def admin_toggle_payment_method(callback: CallbackQuery):
    """Переключить активность способа оплаты"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    method_id = int(callback.data.split(":")[2])
    method = toggle_payment_method(method_id)
    if not method:
        await callback.answer("Способ оплаты не найден", show_alert=True)
        return

    text = _render_payment_method_text(method)
    await callback.message.edit_text(
        text,
        reply_markup=admin_payment_method_actions_kb(method_id, method.is_active),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:payment_method_delete:"))
async def admin_delete_payment_method(callback: CallbackQuery):
    """Удалить способ оплаты"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    method_id = int(callback.data.split(":")[2])
    delete_payment_method(method_id)

    methods = get_all_payment_methods()
    await callback.message.edit_text(
        "🗑️ Способ оплаты удалён.\n\n<b>💳 Способы оплаты</b>",
        reply_markup=admin_payment_methods_kb(methods),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:payment_method_edit:"))
async def admin_payment_method_edit_menu(callback: CallbackQuery, state: FSMContext):
    """Меню редактирования способа оплаты"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    await state.clear()
    method_id = int(callback.data.split(":")[2])
    method = get_payment_method_by_id(method_id)
    if not method:
        await callback.answer("Способ оплаты не найден", show_alert=True)
        return

    text = _render_payment_method_text(method)
    await callback.message.edit_text(
        f"{text}\n\nВыберите, что изменить:",
        reply_markup=admin_payment_method_edit_kb(method_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:payment_method_edit_name:"))
async def admin_payment_method_edit_name(callback: CallbackQuery, state: FSMContext):
    """Редактирование названия способа оплаты"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    method_id = int(callback.data.split(":")[2])
    method = get_payment_method_by_id(method_id)
    if not method:
        await callback.answer("Способ оплаты не найден", show_alert=True)
        return

    await state.update_data(edit_payment_method_id=method_id)
    await state.set_state(AdminStates.editing_payment_method_name)
    await callback.message.edit_text(
        f"Текущее название: <b>{method.name}</b>\n\nВведите новое название:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.editing_payment_method_name)
async def admin_apply_payment_method_name(message: Message, state: FSMContext):
    """Сохранение нового названия"""
    if not _is_admin(message.from_user.id):
        return

    name = (message.text or "").strip()
    if not name:
        await message.answer("Название не может быть пустым.")
        return

    data = await state.get_data()
    method_id = data.get("edit_payment_method_id")
    if not method_id:
        await message.answer("Способ оплаты не найден. Откройте /admin заново.")
        await state.clear()
        return

    method = update_payment_method(method_id, name=name)
    if not method:
        await message.answer("Способ оплаты не найден. Откройте /admin заново.")
        await state.clear()
        return

    await state.clear()
    await message.answer(
        _render_payment_method_text(method),
        reply_markup=admin_payment_method_actions_kb(method.id, method.is_active),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("admin:payment_method_edit_details:"))
async def admin_payment_method_edit_details(callback: CallbackQuery, state: FSMContext):
    """Редактирование реквизитов способа оплаты"""
    if not _is_admin(callback.from_user.id):
        await callback.answer("Нет доступа", show_alert=True)
        return

    method_id = int(callback.data.split(":")[2])
    method = get_payment_method_by_id(method_id)
    if not method:
        await callback.answer("Способ оплаты не найден", show_alert=True)
        return

    await state.update_data(edit_payment_method_id=method_id)
    await state.set_state(AdminStates.editing_payment_method_details)
    await callback.message.edit_text(
        "Введите новые реквизиты:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(AdminStates.editing_payment_method_details)
async def admin_apply_payment_method_details(message: Message, state: FSMContext):
    """Сохранение новых реквизитов"""
    if not _is_admin(message.from_user.id):
        return

    details = (message.text or "").strip()
    if not details:
        await message.answer("Реквизиты не могут быть пустыми.")
        return

    data = await state.get_data()
    method_id = data.get("edit_payment_method_id")
    if not method_id:
        await message.answer("Способ оплаты не найден. Откройте /admin заново.")
        await state.clear()
        return

    method = update_payment_method(method_id, details=details)
    if not method:
        await message.answer("Способ оплаты не найден. Откройте /admin заново.")
        await state.clear()
        return

    await state.clear()
    await message.answer(
        _render_payment_method_text(method),
        reply_markup=admin_payment_method_actions_kb(method.id, method.is_active),
        parse_mode="HTML"
    )

