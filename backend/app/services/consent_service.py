from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserConsent


PERSONAL_DATA_CONSENT_VERSION = "pd-consent-v1"

PERSONAL_DATA_CONSENT_TEXT = (
    "Перед использованием сервиса нужно согласие на обработку персональных данных.\n\n"
    "Сервис получает и обрабатывает ваш Telegram ID, имя/username из Telegram, "
    "постановление о штрафе и документы дела.\n\n"
    "Цель обработки: создание и ведение дела по оспариванию штрафа, хранение "
    "документов и просмотр дела оператором сервиса.\n\n"
    "Telegram используется как интерфейс. Данные дела и документы сохраняются "
    "в серверной инфраструктуре сервиса. На Vercel временно может храниться "
    "telegram_file_id для доступа к файлу до подключения отдельного файлового хранилища."
)


class ConsentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def has_current_consent(self, user_id: int) -> bool:
        consent = await self.session.scalar(
            select(UserConsent.id).where(
                UserConsent.user_id == user_id,
                UserConsent.version == PERSONAL_DATA_CONSENT_VERSION,
            )
        )
        return consent is not None

    async def latest_for_user(self, user_id: int) -> UserConsent | None:
        return await self.session.scalar(
            select(UserConsent)
            .where(UserConsent.user_id == user_id)
            .order_by(desc(UserConsent.accepted_at))
            .limit(1)
        )

    async def accept_current(self, user: User) -> UserConsent:
        existing = await self.session.scalar(
            select(UserConsent).where(
                UserConsent.user_id == user.id,
                UserConsent.version == PERSONAL_DATA_CONSENT_VERSION,
            )
        )
        if existing is not None:
            return existing

        consent = UserConsent(
            user_id=user.id,
            telegram_id=user.telegram_id,
            version=PERSONAL_DATA_CONSENT_VERSION,
        )
        self.session.add(consent)
        await self.session.flush()
        return consent
