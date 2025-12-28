"""
Обработчики заявок
"""
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards.main_kb import confirm_order_kb, cancel_kb, main_menu_kb, order_mode_kb
from data.tariffs import get_tariff_by_id, get_operator_by_id

router = Router()


class OrderStates(StatesGroup):
    """Состояния формы заявки"""
    waiting_transfer_phone = State()
    waiting_full_name = State()
    waiting_region_city = State()
    waiting_passport_photo_1 = State()
    waiting_passport_photo_2 = State()
    confirmation = State()
    waiting_payment = State()


@router.callback_query(F.data.startswith("order:"))
async def start_order(callback: CallbackQuery, state: FSMContext):
    """Начало оформления заявки"""
    tariff_id = int(callback.data.split(":")[1])
    tariff = get_tariff_by_id(tariff_id)

    if not tariff:
        await callback.answer("Тариф не найден", show_alert=True)
        return

    await state.clear()
    await state.update_data(tariff_id=tariff_id)

    await callback.message.edit_text(
        f"<b>📝 Оформление заявки</b>\n\n"
        f"Тариф: <b>{tariff.name}</b>\n"
        f"Выберите тип заявки:",
        reply_markup=order_mode_kb(tariff_id),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("order_mode:"))
async def choose_order_mode(callback: CallbackQuery, state: FSMContext):
    """Выбор типа заявки"""
    _, mode, tariff_id = callback.data.split(":")
    tariff_id = int(tariff_id)

    if mode not in {"transfer", "new"}:
        await callback.answer("Тип заявки не распознан", show_alert=True)
        return

    await state.update_data(mode=mode, tariff_id=tariff_id)

    if mode == "transfer":
        await state.set_state(OrderStates.waiting_transfer_phone)
        await callback.message.edit_text(
            "📱 Введите номер телефона для переноса (без 7/8, пробелов и тире):",
            parse_mode="HTML"
        )
    else:
        await state.set_state(OrderStates.waiting_full_name)
        await callback.message.edit_text(
            "👤 Введите ФИО:",
            parse_mode="HTML"
        )
    await callback.answer()


@router.message(OrderStates.waiting_transfer_phone)
async def process_transfer_phone(message: Message, state: FSMContext):
    """Обработка номера для переноса"""
    phone_raw = message.text or ""
    phone = re.sub(r"\D", "", phone_raw)

    if not phone:
        await message.answer(
            "Введите номер телефона цифрами (без 7/8, пробелов и тире).",
            parse_mode="HTML"
        )
        return

    await state.update_data(transfer_phone=phone)
    await state.set_state(OrderStates.waiting_full_name)

    await message.answer(
        "👤 Введите ФИО:",
        parse_mode="HTML"
    )


@router.message(OrderStates.waiting_full_name)
async def process_full_name(message: Message, state: FSMContext):
    """Обработка ФИО"""
    full_name = (message.text or "").strip()
    if not full_name:
        await message.answer("ФИО не может быть пустым.")
        return

    await state.update_data(full_name=full_name)
    await state.set_state(OrderStates.waiting_region_city)

    await message.answer(
        "🌍 Укажите регион и город:",
        parse_mode="HTML"
    )


@router.message(OrderStates.waiting_region_city)
async def process_region_city(message: Message, state: FSMContext):
    """Обработка региона и города"""
    region_city = (message.text or "").strip()
    if not region_city:
        await message.answer("Регион и город не могут быть пустыми.")
        return

    await state.update_data(region_city=region_city)
    await state.set_state(OrderStates.waiting_passport_photo_1)

    await message.answer(
        "📷 Отправьте фото паспорта: 1-я страница.",
        parse_mode="HTML"
    )


@router.message(OrderStates.waiting_passport_photo_1)
async def process_passport_photo_1(message: Message, state: FSMContext):
    """Обработка фото паспорта (1-я страница)"""
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото паспорта.")
        return

    photo_id = message.photo[-1].file_id
    await state.update_data(passport_photo_1=photo_id)
    await state.set_state(OrderStates.waiting_passport_photo_2)

    await message.answer(
        "📷 Отправьте фото паспорта: 2-я страница (регистрация).",
        parse_mode="HTML"
    )


@router.message(OrderStates.waiting_passport_photo_2)
async def process_passport_photo_2(message: Message, state: FSMContext):
    """Обработка фото паспорта (2-я страница)"""
    if not message.photo:
        await message.answer("Пожалуйста, отправьте фото паспорта.")
        return

    photo_id = message.photo[-1].file_id
    await state.update_data(passport_photo_2=photo_id)
    await state.set_state(OrderStates.confirmation)

    await send_confirmation(message, state)


async def send_confirmation(message: Message, state: FSMContext):
    """Показать подтверждение заявки"""
    data = await state.get_data()
    tariff = get_tariff_by_id(data["tariff_id"])

    if not tariff:
        await message.answer("Тариф не найден.")
        return

    operator = get_operator_by_id(tariff.operator_id)
    mode = data.get("mode")
    mode_text = "Перенос номера" if mode == "transfer" else "Новый номер"

    lines = [
        "<b>✅ Проверьте данные заявки:</b>",
        "",
        f"📡 <b>Оператор:</b> {operator.name if operator else 'Не указан'}",
        f"📦 <b>Тариф:</b> {tariff.name}",
        f"💳 <b>Стоимость подключения:</b> {tariff.connection_price:,} ₽",
    ]

    if tariff.monthly_fee:
        lines.append(f"📅 <b>Абонплата:</b> {tariff.monthly_fee:,} ₽/мес")

    lines.extend([
        "",
        f"🧾 <b>Тип заявки:</b> {mode_text}",
    ])

    if mode == "transfer":
        lines.append(f"📱 <b>Номер для переноса:</b> {data.get('transfer_phone')}")

    lines.extend([
        f"👤 <b>ФИО:</b> {data.get('full_name')}",
        f"🌍 <b>Регион/город:</b> {data.get('region_city')}",
        "📎 <b>Фото паспорта:</b> получены (2 шт.)",
        "",
        "Всё верно? Нажмите «Перейти к оплате»."
    ])

    await message.answer(
        "\n".join(lines),
        reply_markup=confirm_order_kb(data["tariff_id"]),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    """Отмена заявки"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Заявка отменена.\n\nВы можете начать заново в любое время.",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=main_menu_kb()
    )
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Отмена текущего действия"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Действие отменено.",
        parse_mode="HTML"
    )
    await callback.message.answer(
        "Выберите действие:",
        reply_markup=main_menu_kb()
    )
    await callback.answer()
