from fastapi import FastAPI
from contextlib import asynccontextmanager
from starlette.responses import PlainTextResponse
from auth.users import auth_backend, fastapi_users
from auth.schemas import UserCreate, UserRead, UserUpdate
from db import create_db_and_tables
from routes.short_link import router as short_link_router
from routes.admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI): # pragma: no cover
    await create_db_and_tables()
    yield
    pass


app = FastAPI(lifespan=lifespan)

app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"]
)
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

app.include_router(
    admin_router,
    prefix="/admin",
    tags=["admin"]
)

app.include_router(
    short_link_router
)

@app.get("/health")
def health():
    return PlainTextResponse('ok')



