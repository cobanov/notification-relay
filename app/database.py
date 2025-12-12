from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, Text, TIMESTAMP, func
from app.config import settings


class Base(DeclarativeBase):
    pass


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    app_name = Column(Text, nullable=True)
    app_package = Column(Text, nullable=True)
    title = Column(Text, nullable=True)
    text = Column(Text, nullable=True)
    text_big = Column(Text, nullable=True)
    text_lines = Column(Text, nullable=True)
    sub_text = Column(Text, nullable=True)
    ticker = Column(Text, nullable=True)
    timestamp = Column(Text, nullable=True)
    system_time = Column(Text, nullable=True)
    location = Column(Text, nullable=True)
    location_link = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.current_timestamp())


# Create async engine
engine: AsyncEngine = create_async_engine(
    settings.database_url,
    echo=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency for getting database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
