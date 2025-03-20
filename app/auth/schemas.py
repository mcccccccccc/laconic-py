import uuid
import datetime
from pydantic import BaseModel, HttpUrl
from fastapi_users import schemas


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserCreate(schemas.BaseUserCreate):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass

class CreateShortRequest(BaseModel):
    original_url: HttpUrl
    custom_alias: str = None
    expires_at: datetime.datetime | None = None


class UpdateLinkRequest(BaseModel):
    original_url: HttpUrl | None = None
    expires_at: datetime.datetime | None = None