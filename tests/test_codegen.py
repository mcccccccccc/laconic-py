import os
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select
from db import Base, ShortLink
from utils.code_gen import code_gen

@pytest.mark.asyncio
async def test_code_gen():
    # Создаем тестовую базу данных
    engine = create_async_engine("sqlite+aiosqlite:///./test.db", connect_args={"check_same_thread": False})
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_maker() as session:
        # Тестируем генерацию нового кода
        short_code = await code_gen(session)
        assert len(short_code) == 5

        # Проверяем, что код уникален
        query = select(ShortLink).where(ShortLink.short_code == short_code)
        result = await session.execute(query)
        assert result.first() is None

        # Тестируем генерацию кода с заданным alias
        custom_alias = "custom"
        short_code = await code_gen(session, custom_alias)
        assert short_code == custom_alias

        # Проверяем, что при повторном использовании alias возникает исключение
        short_link = ShortLink(
            original_url="https://example.com",
            short_code=custom_alias,
            expires_at=datetime.now(),
            user_id=None,
        )
        session.add(short_link)
        await session.commit()
        with pytest.raises(Exception, match="Alias already taken"):
            await code_gen(session, custom_alias)

    await engine.dispose()
    os.remove("./test.db")