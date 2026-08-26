from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Case


class CaseService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user_id: int) -> Case:
        case = Case(user_id=user_id)
        self.session.add(case)
        await self.session.flush()
        return case

    async def list_for_user(self, user_id: int, limit: int = 10) -> list[Case]:
        result = await self.session.scalars(
            select(Case)
            .where(Case.user_id == user_id)
            .options(selectinload(Case.documents))
            .order_by(desc(Case.created_at))
            .limit(limit)
        )
        return list(result)

    async def get_for_user(self, user_id: int, case_id: int) -> Case | None:
        return await self.session.scalar(
            select(Case)
            .where(Case.id == case_id, Case.user_id == user_id)
            .options(selectinload(Case.documents))
        )
