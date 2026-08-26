from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import get_settings


settings = get_settings()
engine = create_async_engine(
    settings.async_database_url,
    connect_args=settings.database_connect_args,
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
