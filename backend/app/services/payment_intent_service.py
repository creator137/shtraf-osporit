from dataclasses import dataclass

from sqlalchemy import desc, distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import PaymentIntent
from app.offers import OFFERS


@dataclass(frozen=True)
class OfferIntentStats:
    offer_code: str
    clicks: int
    unique_users: int


@dataclass(frozen=True)
class PaymentIntentStats:
    total_clicks: int
    unique_users: int
    unique_cases: int
    offers: list[OfferIntentStats]


class PaymentIntentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self, *, user_id: int, offer_code: str, case_id: int | None = None
    ) -> PaymentIntent:
        if offer_code not in OFFERS:
            raise ValueError("Unknown offer")
        intent = PaymentIntent(
            user_id=user_id,
            case_id=case_id,
            offer_code=offer_code,
        )
        self.session.add(intent)
        await self.session.flush()
        return intent

    async def stats(self) -> PaymentIntentStats:
        total_clicks = await self.session.scalar(select(func.count(PaymentIntent.id)))
        unique_users = await self.session.scalar(
            select(func.count(distinct(PaymentIntent.user_id)))
        )
        unique_cases = await self.session.scalar(
            select(func.count(distinct(PaymentIntent.case_id)))
            .where(PaymentIntent.case_id.is_not(None))
        )
        rows = await self.session.execute(
            select(
                PaymentIntent.offer_code,
                func.count(PaymentIntent.id),
                func.count(distinct(PaymentIntent.user_id)),
            ).group_by(PaymentIntent.offer_code)
        )
        by_offer = {
            offer_code: (clicks, offer_users)
            for offer_code, clicks, offer_users in rows
        }
        return PaymentIntentStats(
            total_clicks=total_clicks or 0,
            unique_users=unique_users or 0,
            unique_cases=unique_cases or 0,
            offers=[
                OfferIntentStats(
                    offer_code=offer_code,
                    clicks=by_offer.get(offer_code, (0, 0))[0],
                    unique_users=by_offer.get(offer_code, (0, 0))[1],
                )
                for offer_code in OFFERS
            ],
        )

    async def list_recent(self, limit: int = 100) -> list[PaymentIntent]:
        intents = await self.session.scalars(
            select(PaymentIntent)
            .options(
                selectinload(PaymentIntent.user),
                selectinload(PaymentIntent.case),
            )
            .order_by(desc(PaymentIntent.created_at), desc(PaymentIntent.id))
            .limit(limit)
        )
        return list(intents)
