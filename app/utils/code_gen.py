import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from db import ShortLink
from sqlalchemy import select


async def code_gen(db, short_code: str = None) -> str:
    """
    Генерация кода для FastAPI приложения
    """
    # return str(uuid.uuid4())[:6]
    if short_code:
        query = select(ShortLink).where(ShortLink.short_code == short_code)
        result = await db.execute(query)
        if result.first():
            raise Exception("Alias already taken")
    else:
        length = 5
        short_code = str(uuid.uuid4())[:length]
        query = select(ShortLink).where(ShortLink.short_code == short_code)
        result = await db.execute(query)
        while result.first():
            short_code = str(uuid.uuid4())[:length]
            query = select(ShortLink).where(ShortLink.short_code == short_code)
            result = await db.execute(query)

    return short_code







