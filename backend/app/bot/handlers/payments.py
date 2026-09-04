from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.utils import safe_answer, safe_callback_answer
from app.offers import OFFERS
from app.services.case_service import CaseService
from app.services.payment_intent_service import PaymentIntentService
from app.services.user_service import UserService


router = Router(name="payments")


def payment_offers_text() -> str:
    lines = ["Выберите подходящий вариант:"]
    for offer in OFFERS.values():
        lines.extend(
            [
                "",
                f"{offer.icon} {offer.title}",
                offer.description,
                offer.price,
            ]
        )
    return "\n".join(lines)


def payment_offers_keyboard(case_id: int | None) -> InlineKeyboardMarkup:
    case_value = case_id or 0
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"💳 Перейти к оплате: {offer.title}",
                    callback_data=f"pay:intent:{case_value}:{offer.code}",
                )
            ]
            for offer in OFFERS.values()
        ]
    )


async def send_payment_offers(message, case_id: int | None) -> None:
    await safe_answer(
        message,
        payment_offers_text(),
        reply_markup=payment_offers_keyboard(case_id),
    )


@router.callback_query(F.data.startswith("pay:intent:"))
async def create_payment_intent(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    if callback.data is None:
        return
    parts = callback.data.split(":")
    if len(parts) != 4:
        await safe_callback_answer(callback, "Предложение не найдено.", show_alert=True)
        return
    _, _, case_value, offer_code = parts
    if offer_code not in OFFERS:
        await safe_callback_answer(callback, "Предложение не найдено.", show_alert=True)
        return

    user = await UserService(session).get_by_telegram_id(callback.from_user.id)
    if user is None:
        await safe_callback_answer(callback, "Сначала запустите бота.", show_alert=True)
        return

    try:
        case_id = int(case_value)
    except ValueError:
        await safe_callback_answer(callback, "Дело не найдено.", show_alert=True)
        return
    linked_case_id: int | None = None
    if case_id:
        case = await CaseService(session).get_for_user(user.id, case_id)
        if case is None:
            await safe_callback_answer(callback, "Дело не найдено.", show_alert=True)
            return
        linked_case_id = case.id

    await PaymentIntentService(session).create(
        user_id=user.id,
        case_id=linked_case_id,
        offer_code=offer_code,
    )
    await session.commit()
    await safe_callback_answer(
        callback,
        "Способ оплаты находится в разработке. Мы сообщим, когда возможность оплаты станет доступна.",
        show_alert=True,
    )
