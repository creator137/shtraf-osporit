from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Case, User
from app.services.document_service import remove_local_document_file


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        return await self.session.scalar(
            select(User).where(User.telegram_id == telegram_id)
        )

    async def delete_by_telegram_id(self, telegram_id: int) -> bool:
        user = await self.session.scalar(
            select(User)
            .where(User.telegram_id == telegram_id)
            .options(selectinload(User.cases).selectinload(Case.documents))
        )
        if user is None:
            return False
        for case in user.cases:
            for document in case.documents:
                remove_local_document_file(document)
        await self.session.delete(user)
        return True

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> User:
        statement = (
            insert(User)
            .values(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
            )
            .on_conflict_do_update(
                index_elements=[User.telegram_id],
                set_={
                    "username": username,
                    "first_name": first_name,
                    "last_name": last_name,
                    "updated_at": func.now(),
                },
            )
            .returning(User)
        )
        users = await self.session.scalars(
            statement, execution_options={"populate_existing": True}
        )
        return users.one()

    async def update_name(
        self, user: User, first_name: str, last_name: str | None
    ) -> User:
        user.first_name = first_name
        user.last_name = last_name
        await self.session.flush()
        return user
