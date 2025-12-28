"""
Обработчики команды /start и главного меню
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext

from keyboards.main_kb import main_menu_kb

router = Router()


WELCOME_MESSAGE = """
🎉 <b>Добро пожаловать!</b>

Я ваш персональный помощник по выбору тарифов. 

Я помогу вам:
• 📋 Подобрать идеальный тариф
• ❓ Ответить на ваши вопросы
• 💳 Оформить заказ и оплату

Выберите действие в меню ниже 👇
"""


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start"""
    await state.clear()
    await message.answer(
        WELCOME_MESSAGE,
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )


@router.message(F.text == "ℹ️ О нас")
async def about_us(message: Message):
    """Информация о компании/услугах"""
    about_text = """
<b>ℹ️ О нас</b>

Мы предлагаем качественные услуги и индивидуальный подход к каждому клиенту.

🔹 Опыт работы более 5 лет
🔹 Сотни довольных клиентов  
🔹 Гарантия результата
🔹 Поддержка 24/7

Выберите тариф и убедитесь сами! 👇
"""
    await message.answer(about_text, parse_mode="HTML")


@router.message(F.text == "💬 Связаться")
async def contact_us(message: Message):
    """Связь с поддержкой"""
    contact_text = """
<b>💬 Связаться с нами</b>

Есть вопросы? Мы всегда на связи!

📩 Напишите ваш вопрос прямо сюда, и мы ответим в ближайшее время.
"""
    await message.answer(contact_text, parse_mode="HTML")


@router.callback_query(F.data == "main_menu")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()
    await callback.message.answer(
        WELCOME_MESSAGE,
        reply_markup=main_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()
