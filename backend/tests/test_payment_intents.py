from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.payments import (
    create_payment_intent,
    payment_offers_keyboard,
    payment_offers_text,
)
from app.db.models import PaymentIntent
from app.services.case_service import CaseService
from app.services.payment_intent_service import PaymentIntentService
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_payment_intents_allow_repeated_clicks_and_calculate_stats(
    db_session: AsyncSession,
) -> None:
    await db_session.execute(delete(PaymentIntent))
    first_user = await UserService(db_session).get_or_create(
        300_000_001, "first", "Первый", "Пользователь"
    )
    second_user = await UserService(db_session).get_or_create(
        300_000_002, "second", "Второй", "Пользователь"
    )
    first_case = await CaseService(db_session).create(first_user.id)
    second_case = await CaseService(db_session).create(second_user.id)
    service = PaymentIntentService(db_session)

    first = await service.create(
        user_id=first_user.id,
        case_id=first_case.id,
        offer_code="complaint",
    )
    await service.create(
        user_id=first_user.id,
        case_id=first_case.id,
        offer_code="complaint",
    )
    await service.create(
        user_id=second_user.id,
        case_id=second_case.id,
        offer_code="complaint",
    )
    await service.create(user_id=first_user.id, offer_code="fine_check")

    stats = await service.stats()
    by_offer = {item.offer_code: item for item in stats.offers}

    assert first.user_id == first_user.id
    assert first.case_id == first_case.id
    assert first.offer_code == "complaint"
    assert stats.total_clicks == 4
    assert stats.unique_users == 2
    assert stats.unique_cases == 2
    assert by_offer["complaint"].clicks == 3
    assert by_offer["complaint"].unique_users == 2
    assert by_offer["fine_check"].clicks == 1
    assert by_offer["turnkey"].clicks == 0


@pytest.mark.asyncio
async def test_telegram_payment_click_is_saved_before_unavailable_alert(
    db_session: AsyncSession,
) -> None:
    user = await UserService(db_session).get_or_create(
        300_000_003, "telegram", "Тест", "Оплата"
    )
    case = await CaseService(db_session).create(user.id)
    callback = SimpleNamespace(
        data=f"pay:intent:{case.id}:turnkey",
        from_user=SimpleNamespace(id=user.telegram_id),
        answer=AsyncMock(),
    )

    await create_payment_intent(callback, db_session)
    await create_payment_intent(callback, db_session)

    intents = list(
        await db_session.scalars(
            select(PaymentIntent).where(PaymentIntent.user_id == user.id)
        )
    )
    assert len(intents) == 2
    assert all(intent.case_id == case.id for intent in intents)
    assert all(intent.offer_code == "turnkey" for intent in intents)
    assert callback.answer.await_count == 2
    assert "находится в разработке" in callback.answer.await_args.args[0]
    assert callback.answer.await_args.kwargs["show_alert"] is True


def test_payment_offers_are_shown_with_price_ranges() -> None:
    text = payment_offers_text()
    keyboard = payment_offers_keyboard(case_id=42)

    assert "Проверка штрафа\nАнализ перспектив с помощью ИИ\n0–99 ₽" in text
    assert "Жалоба\nГотовый пакет документов\n299–990 ₽" in text
    assert "Под ключ\nСопровождение обжалования\n990–2 990 ₽" in text
    assert [row[0].callback_data for row in keyboard.inline_keyboard] == [
        "pay:intent:42:fine_check",
        "pay:intent:42:complaint",
        "pay:intent:42:turnkey",
    ]
