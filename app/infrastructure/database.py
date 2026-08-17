from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config.settings import DATABASE_URL
from app.infrastructure.base import Base

# Импортируем модели, чтобы SQLAlchemy зарегистрировал их в metadata
from app.infrastructure.models.trade_model import TradeModel  # noqa: F401


engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    poolclass=NullPool,
)

async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def create_tables() -> None:
    # Some environments (CI, dev) may not have the `greenlet` package
    # installed which SQLAlchemy uses to run sync DB APIs from async code.
    # In that case, create tables synchronously using a regular engine.
    try:
        import greenlet  # type: ignore
        has_greenlet = True
    except Exception:
        has_greenlet = False

    if not has_greenlet:
        # Create tables synchronously to avoid greenlet dependency.
        from sqlalchemy import create_engine

        sync_url = DATABASE_URL.replace("+aiosqlite", "")
        sync_engine = create_engine(sync_url, echo=False)
        Base.metadata.create_all(bind=sync_engine)
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)