from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.main import consent_keyboard, main_menu_keyboard
from app.bot.states import DocumentUpload
from app.bot.utils import safe_answer, safe_callback_answer
from app.services.consent_service import PERSONAL_DATA_CONSENT_TEXT, ConsentService
from app.services.user_service import UserService


router = Router(name="consent")
CONSENT_INTRO = (
    "Перед началом работы с сервисом необходимо подписать согласие на обработку "
    "персональных данных. Сначала ознакомьтесь с текстом, затем отметьте оба пункта."
)


async def send_consent_request(message: Message, state: FSMContext) -> None:
    await state.set_state(DocumentUpload.waiting_for_consent)
    await state.set_data(
        {"consent_viewed": False, "consent_acknowledged": False, "consent_signed": False}
    )
    await safe_answer(message, CONSENT_INTRO, reply_markup=consent_keyboard())


def _consent_chunks(max_length: int = 3900) -> list[str]:
    chunks: list[str] = []
    current = ""
    for paragraph in PERSONAL_DATA_CONSENT_TEXT.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}" if current else paragraph
        if len(candidate) > max_length and current:
            chunks.append(current)
            current = paragraph
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


async def _refresh_keyboard(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    data = await state.get_data()
    await callback.message.edit_reply_markup(
        reply_markup=consent_keyboard(
            viewed=bool(data.get("consent_viewed")),
            acknowledged=bool(data.get("consent_acknowledged")),
            signed=bool(data.get("consent_signed")),
        )
    )


@router.callback_query(DocumentUpload.waiting_for_consent, F.data == "consent:view")
async def view_consent(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    data = await state.get_data()
    await state.update_data(consent_viewed=True)
    for chunk in _consent_chunks():
        await safe_answer(callback.message, chunk)
    if not data.get("consent_viewed"):
        await _refresh_keyboard(callback, state)
    await safe_callback_answer(callback)


@router.callback_query(
    DocumentUpload.waiting_for_consent, F.data == "consent:acknowledge"
)
async def acknowledge_consent(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("consent_viewed"):
        await safe_callback_answer(
            callback, "Сначала откройте и прочитайте текст согласия.", show_alert=True
        )
        return
    await state.update_data(
        consent_acknowledged=not bool(data.get("consent_acknowledged"))
    )
    await _refresh_keyboard(callback, state)
    await safe_callback_answer(callback)


@router.callback_query(DocumentUpload.waiting_for_consent, F.data == "consent:sign")
async def sign_consent(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get("consent_viewed"):
        await safe_callback_answer(
            callback, "Сначала откройте и прочитайте текст согласия.", show_alert=True
        )
        return
    await state.update_data(consent_signed=not bool(data.get("consent_signed")))
    await _refresh_keyboard(callback, state)
    await safe_callback_answer(callback)


@router.callback_query(DocumentUpload.waiting_for_consent, F.data == "consent:confirm")
async def confirm_consent(
    callback: CallbackQuery, state: FSMContext, session: AsyncSession
) -> None:
    if callback.message is None:
        return
    data = await state.get_data()
    if not all(
        data.get(key)
        for key in ("consent_viewed", "consent_acknowledged", "consent_signed")
    ):
        await safe_callback_answer(
            callback, "Ознакомьтесь с текстом и отметьте оба пункта.", show_alert=True
        )
        return
    telegram_user = callback.from_user
    user = await UserService(session).get_or_create(
        telegram_id=telegram_user.id,
        username=telegram_user.username,
        first_name=telegram_user.first_name,
        last_name=telegram_user.last_name,
    )
    await ConsentService(session).accept_current(user)
    await session.commit()
    await state.set_data({})
    await state.set_state(DocumentUpload.waiting_for_file)
    await safe_callback_answer(callback, "Согласие сохранено.")
    await safe_answer(
        callback.message,
        "Согласие сохранено. Теперь отправьте постановление о штрафе в формате PDF или изображения.",
        reply_markup=main_menu_keyboard(),
    )


@router.callback_query(DocumentUpload.waiting_for_consent, F.data == "consent:decline")
async def decline_consent(callback: CallbackQuery, state: FSMContext) -> None:
    if callback.message is None:
        return
    await state.clear()
    await safe_callback_answer(callback)
    await safe_answer(
        callback.message,
        "Без согласия начать работу с сервисом нельзя.",
        reply_markup=main_menu_keyboard(),
    )
