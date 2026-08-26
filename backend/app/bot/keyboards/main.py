from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


CHECK_FINE_TEXT = "🔎 Проверить штраф"
MY_CASES_TEXT = "📁 Мои дела"
HELP_TEXT = "❓ Помощь"
ENTER_NAME_TEXT = "✍️ Ввести ФИО"


def profile_name_keyboard(profile_name: str | None) -> ReplyKeyboardMarkup:
    buttons = []
    if profile_name:
        buttons.append([KeyboardButton(text=f"✅ Использовать: {profile_name}")])
    buttons.append([KeyboardButton(text=ENTER_NAME_TEXT)])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True, one_time_keyboard=True)


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=CHECK_FINE_TEXT)],
            [KeyboardButton(text=MY_CASES_TEXT), KeyboardButton(text=HELP_TEXT)],
        ],
        resize_keyboard=True,
    )
