from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings


settings = get_settings()
engine = create_async_engine(str(settings.database_url))
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
