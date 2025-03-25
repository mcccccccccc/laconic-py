from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
import redis.asyncio as redis
from config import settings


engine = create_async_engine(settings.database_url)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


# async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
#     async with async_session_maker() as session:
#         yield session


async def get_db(): # pragma: no cover
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_redis():
    redis_client = redis.Redis(host=settings.redis_host, port=settings.redis_port, db=4, decode_responses=True)
    try:
        yield redis_client
    finally:
        await redis_client.aclose()