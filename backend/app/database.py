import uuid

from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

from .config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# SQLite UUID adapter: register converter to store UUIDs as strings
@event.listens_for(engine.sync_engine, "connect")
def sqlite_connect(dbapi_connection, connection_record):
    if settings.DB_TYPE != "postgres":
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()


def gen_uuid() -> str:
    """Generate a UUID as a string, compatible with both SQLite and PostgreSQL."""
    return str(uuid.uuid4())
