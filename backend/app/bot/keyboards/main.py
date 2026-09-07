from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


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


def consent_keyboard(
    *, viewed: bool = False, acknowledged: bool = False, signed: bool = False
) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text="📄 Ознакомиться с согласием", callback_data="consent:view")],
        [
            InlineKeyboardButton(
                text=f"{'☑' if acknowledged else '☐'} Я ознакомлен(а)",
                callback_data="consent:acknowledge",
            )
        ],
        [
            InlineKeyboardButton(
                text=f"{'☑' if signed else '☐'} Подписываю согласие",
                callback_data="consent:sign",
            )
        ],
    ]
    if viewed and acknowledged and signed:
        rows.append(
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить и продолжить",
                    callback_data="consent:confirm",
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton(text="Отказаться", callback_data="consent:decline")]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)
