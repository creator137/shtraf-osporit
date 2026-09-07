from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.handlers.consent import _consent_chunks, confirm_consent
from app.bot.keyboards.main import consent_keyboard
from app.bot.states import DocumentUpload
from app.services.consent_service import PERSONAL_DATA_CONSENT_VERSION, ConsentService
from app.services.user_service import UserService


def test_consent_text_fits_telegram_and_confirmation_requires_both_marks() -> None:
    chunks = _consent_chunks()
    incomplete = consent_keyboard(viewed=True, acknowledged=True, signed=False)
    complete = consent_keyboard(viewed=True, acknowledged=True, signed=True)

    assert chunks
    assert all(len(chunk) <= 3900 for chunk in chunks)
    assert not any(
        button.callback_data == "consent:confirm"
        for row in incomplete.inline_keyboard
        for button in row
    )
    assert any(
        button.callback_data == "consent:confirm"
        for row in complete.inline_keyboard
        for button in row
    )


@pytest.mark.asyncio
async def test_confirm_consent_records_current_version(
    db_session: AsyncSession,
) -> None:
    telegram_user = SimpleNamespace(
        id=400_000_001,
        username="consent_flow",
        first_name="Тест",
        last_name="Согласие",
    )
    message = SimpleNamespace(answer=AsyncMock())
    callback = SimpleNamespace(
        message=message,
        from_user=telegram_user,
        answer=AsyncMock(),
    )
    state = SimpleNamespace(
        get_data=AsyncMock(
            return_value={
                "consent_viewed": True,
                "consent_acknowledged": True,
                "consent_signed": True,
            }
        ),
        set_data=AsyncMock(),
        set_state=AsyncMock(),
    )

    await confirm_consent(callback, state, db_session)

    user = await UserService(db_session).get_by_telegram_id(telegram_user.id)
    assert user is not None
    consent = await ConsentService(db_session).latest_for_user(user.id)
    assert consent is not None
    assert consent.telegram_id == telegram_user.id
    assert consent.version == PERSONAL_DATA_CONSENT_VERSION
    assert consent.accepted_at is not None
    state.set_state.assert_awaited_once_with(DocumentUpload.waiting_for_file)
    assert "Согласие сохранено" in message.answer.await_args.args[0]
