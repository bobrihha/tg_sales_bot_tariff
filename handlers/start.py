"""
Обработчики команды /start и главного меню
"""
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from keyboards.main_kb import main_menu_kb
from config import load_config

router = Router()
config = load_config()


class ContactStates(StatesGroup):
    """Состояния для связи с поддержкой"""
    waiting_message = State()


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
async def contact_us(message: Message, state: FSMContext):
    """Связь с поддержкой"""
    await state.set_state(ContactStates.waiting_message)
    contact_text = """
<b>💬 Связаться с нами</b>

Есть вопросы? Мы всегда на связи!

📩 Напишите ваш вопрос прямо сейчас, и мы ответим в ближайшее время.

<i>Отправьте текстовое сообщение или нажмите любую кнопку меню для отмены.</i>
"""
    await message.answer(contact_text, parse_mode="HTML")


@router.message(ContactStates.waiting_message)
async def forward_message_to_admin(message: Message, state: FSMContext, bot: Bot):
    """Пересылка сообщения администраторам"""
    if not message.text:
        await message.answer("Пожалуйста, отправьте текстовое сообщение.")
        return
    
    # Проверяем, не нажал ли пользователь кнопку меню
    menu_buttons = ["📋 Тарифы", "ℹ️ О нас", "❓ FAQ", "💬 Связаться"]
    if message.text in menu_buttons:
        await state.clear()
        return  # Пусть другой обработчик обработает
    
    user = message.from_user
    username = f"@{user.username}" if user.username else "отсутствует"
    
    admin_text = (
        f"📩 <b>НОВОЕ СООБЩЕНИЕ</b>\n\n"
        f"<b>От:</b> {user.full_name}\n"
        f"<b>Username:</b> {username}\n"
        f"<b>ID:</b> {user.id}\n\n"
        f"<b>Сообщение:</b>\n{message.text}"
    )
    
    # Отправляем всем админам
    sent = False
    for admin_id in config.bot.admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode="HTML"
            )
            sent = True
        except Exception as e:
            print(f"Ошибка отправки админу {admin_id}: {e}")
    
    await state.clear()
    
    if sent:
        await message.answer(
            "✅ <b>Сообщение отправлено!</b>\n\n"
            "Мы ответим вам в ближайшее время.",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "❌ Не удалось отправить сообщение. Попробуйте позже.",
            reply_markup=main_menu_kb(),
            parse_mode="HTML"
        )


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
