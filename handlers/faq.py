"""
Обработчик FAQ
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

router = Router()


FAQ_ITEMS = {
    "payment": {
        "question": "💳 Как оплатить?",
        "answer": (
            "<b>Способы оплаты:</b>\n\n"
            "Оплата происходит через безопасный сервис Robokassa.\n"
            "Принимаются: банковские карты, СБП, электронные кошельки.\n\n"
            "После выбора тарифа нажмите «Оформить заказ» и следуйте инструкциям."
        )
    },
    "refund": {
        "question": "💸 Можно ли вернуть деньги?",
        "answer": (
            "<b>Возврат средств:</b>\n\n"
            "Да, мы вернём деньги в полном объёме, если услуга вам не подошла.\n"
            "Обратитесь в поддержку в течение 14 дней после покупки."
        )
    },
    "delivery": {
        "question": "📦 Когда я получу доступ?",
        "answer": (
            "<b>Доступ к материалам:</b>\n\n"
            "Сразу после подтверждения оплаты мы свяжемся с вами и выдадим доступ."
        )
    },
}


def faq_menu_kb() -> InlineKeyboardMarkup:
    """Клавиатура FAQ"""
    builder = InlineKeyboardBuilder()
    for key, item in FAQ_ITEMS.items():
        builder.row(
            InlineKeyboardButton(
                text=item["question"],
                callback_data=f"faq:{key}"
            )
        )
    return builder.as_markup()


def faq_back_kb() -> InlineKeyboardMarkup:
    """Кнопка возврата к FAQ"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="⬅️ Назад к FAQ",
            callback_data="back_to_faq"
        )
    )
    return builder.as_markup()


@router.message(F.text == "❓ FAQ")
async def show_faq(message: Message):
    """Показать меню FAQ"""
    await message.answer(
        "<b>❓ Часто задаваемые вопросы</b>\n\n"
        "Выберите интересующий вопрос:",
        reply_markup=faq_menu_kb(),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("faq:"))
async def show_faq_answer(callback: CallbackQuery):
    """Показать ответ на вопрос FAQ"""
    faq_key = callback.data.split(":")[1]
    
    if faq_key not in FAQ_ITEMS:
        await callback.answer("Вопрос не найден", show_alert=True)
        return
    
    item = FAQ_ITEMS[faq_key]
    await callback.message.edit_text(
        f"<b>{item['question']}</b>\n\n{item['answer']}",
        reply_markup=faq_back_kb(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_faq")
async def back_to_faq(callback: CallbackQuery):
    """Вернуться к списку FAQ"""
    await callback.message.edit_text(
        "<b>❓ Часто задаваемые вопросы</b>\n\n"
        "Выберите интересующий вопрос:",
        reply_markup=faq_menu_kb(),
        parse_mode="HTML"
    )
    await callback.answer()
