import datetime
from fastapi import Depends
from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from depends import engine, get_db
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, func, UUID


class Base(DeclarativeBase):
    pass


class User(SQLAlchemyBaseUserTableUUID, Base):
    pass


class ShortLink(Base):
    __tablename__ = "short_links"
    id = Column(Integer, primary_key=True, index=True)
    original_url = Column(String, nullable=False)
    short_code = Column(String, unique=True, index=True, nullable=False)
    created_at = Column(DateTime, default=func.now())
    expires_at = Column(DateTime, nullable=True)
    access_count = Column(Integer, default=0)
    last_accessed = Column(DateTime, nullable=True)
    user_id = Column(UUID, ForeignKey("user.id"))

    def get_ttl(self):
        if self.expires_at:
            expire_delta = self.expires_at - datetime.datetime.now()
            if expire_delta.total_seconds() < 0:
                raise Exception("Expiration date must be in the future___")

            return expire_delta
        else:
            return None

    def to_dict(self):
        return {
            "id": str(self.id),
            "original_url": self.original_url,
            "short_code": self.short_code,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "user_id": str(self.user_id) if self.user_id else None
        }



async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_user_db(session: AsyncSession = Depends(get_db)):
    yield SQLAlchemyUserDatabase(session, User)