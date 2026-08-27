from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


CHECK_FINE_TEXT = "⚖️ Оспорить штраф"
MY_CASES_TEXT = "📁 Мои дела"
HELP_TEXT = "❓ Помощь"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=CHECK_FINE_TEXT)],
            [KeyboardButton(text=MY_CASES_TEXT), KeyboardButton(text=HELP_TEXT)],
        ],
        resize_keyboard=True,
    )
