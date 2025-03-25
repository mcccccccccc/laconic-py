import os
from typing import Callable, AsyncGenerator
import pytest_asyncio
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from app import app
from db import *
from depends import get_redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import select
from unittest.mock import AsyncMock


pytestmark = pytest.mark.asyncio

# @pytest.fixture(scope="session")
# def event_loop(request):
#     """Create an instance of the default event loop for each test case."""
#     loop = asyncio.get_event_loop_policy().new_event_loop()
#     yield loop
#     loop.close()

# @pytest_asyncio.fixture
# async def mock_redis():
#     redis_mock = AsyncMock()
#     yield redis_mock

# @pytest.fixture
# def get_redis_override(mock_redis):
#     async def _override_get_redis():
#         yield mock_redis
#     return _override_get_redis

# @pytest.fixture
# def app_fixture_with_redis(get_redis_override):
#     app.dependency_overrides[get_redis] = get_redis_override
#     return app


# @pytest.mark.asyncio
async def test_health():
    async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.text == "ok"





@pytest_asyncio.fixture
async def db_session():
    # settings.database_url
    engine = create_async_engine("sqlite+aiosqlite:///./test.db", connect_args = {"check_same_thread": False})
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        async with async_session(bind=conn) as session:
            yield session
            await session.flush()
            await session.rollback()
            os.remove("./test.db")


@pytest.fixture()
def get_db_override(db_session: AsyncSession) -> Callable:
    async def _override_get_db():
        yield db_session

    return _override_get_db


@pytest.fixture()
def app_fixture(get_db_override: Callable) -> FastAPI:
    app.dependency_overrides[get_db] = get_db_override
    # app.dependency_overrides[get_redis] = get_redis_override
    return app


@pytest_asyncio.fixture
async def async_client(app_fixture: FastAPI) -> AsyncGenerator:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac

# @pytest.mark.asyncio
# @pytest.mark.anyio
async def test_login(async_client: AsyncClient, db_session: AsyncSession):
    # Регистрация нового пользователя
    response = await async_client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )
    print(response.text)
    assert response.status_code == 201


    # Логин с зарегистрированным пользователем
    response = await async_client.post(
        "/auth/jwt/login",
        data={"username": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_shorten_url(async_client: AsyncClient, db_session: AsyncSession):
    response = await async_client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 201

    response = await async_client.post(
        "/auth/jwt/login",
        data={"username": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    response = await async_client.post(
        "/links/shorten",
        json={"original_url": "http://example.com"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "short_url" in response.json()

async def test_search_link(async_client: AsyncClient, db_session: AsyncSession):
    response = await async_client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 201

    response = await async_client.post(
        "/auth/jwt/login",
        data={"username": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    response = await async_client.post(
        "/links/shorten",
        json={"original_url": "http://example.com"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

    response = await async_client.get(
        "/links/search",
        params={"original_url": "example.com"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "short_code" in response.json()

async def test_redirect_url(async_client: AsyncClient, db_session: AsyncSession):
    response = await async_client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 201

    response = await async_client.post(
        "/auth/jwt/login",
        data={"username": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    response = await async_client.post(
        "/links/shorten",
        json={"original_url": "http://example.com"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    short_code = response.json()["short_url"].split("/")[-1]
    # print(response.json())
    # print(short_code)

    response = await async_client.get(f"/links/{short_code}")
    assert response.status_code == 307  # redirect
    assert response.headers["Location"] == "http://example.com/"

async def test_delete_link(async_client: AsyncClient, db_session: AsyncSession):
    response = await async_client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 201

    response = await async_client.post(
        "/auth/jwt/login",
        data={"username": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    response = await async_client.post(
        "/links/shorten",
        json={"original_url": "http://example.com"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    short_code = response.json()["short_url"].split("/")[-1]

    response = await async_client.delete(
        f"/links/{short_code}",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200

async def test_update_link(async_client: AsyncClient, db_session: AsyncSession):
    response = await async_client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 201

    response = await async_client.post(
        "/auth/jwt/login",
        data={"username": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    response = await async_client.post(
        "/links/shorten",
        json={"original_url": "http://example.com"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    short_code = response.json()["short_url"].split("/")[-1]

    response = await async_client.put(
        f"/links/{short_code}",
        json={"original_url": "http://newexample.com"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200


async def test_link_stats(async_client: AsyncClient, db_session: AsyncSession):
    response = await async_client.post(
        "/auth/register",
        json={"email": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 201

    response = await async_client.post(
        "/auth/jwt/login",
        data={"username": "test@example.com", "password": "password123"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    response = await async_client.post(
        "/links/shorten",
        json={"original_url": "http://example.com"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    short_code = response.json()["short_url"].split("/")[-1]

    response = await async_client.get(
        f"/links/{short_code}/stats",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "original_url" in response.json()

async def test_get_expired_links(async_client: AsyncClient, db_session: AsyncSession):
    response = await async_client.post(
        "/auth/register",
        json={"email": "admin@example.com", "password": "adminpassword"}
    )
    query = select(User).where(User.email == "admin@example.com")
    result = await db_session.execute(query)
    adm_user = result.first()[0]
    adm_user.is_superuser = True
    await db_session.commit()

    assert response.status_code == 201

    response = await async_client.post(
        "/auth/jwt/login",
        data={"username": "admin@example.com", "password": "adminpassword"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    response = await async_client.get(
        "/admin/links/expired",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)

async def test_search_link_admin(async_client: AsyncClient, db_session: AsyncSession):
    response = await async_client.post(
        "/auth/register",
        json={"email": "admin@example.com", "password": "adminpassword"}
    )
    assert response.status_code == 201
    query = select(User).where(User.email == "admin@example.com")
    result = await db_session.execute(query)
    adm_user = result.first()[0]
    adm_user.is_superuser = True
    await db_session.commit()

    response = await async_client.post(
        "/auth/jwt/login",
        data={"username": "admin@example.com", "password": "adminpassword"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    response = await async_client.get(
        "/admin/links/search",
        params={"original_url": "example.com"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)

async def test_delete_unauth_links(async_client: AsyncClient, db_session: AsyncSession):
    response = await async_client.post(
        "/auth/register",
        json={"email": "admin@example.com", "password": "adminpassword"}
    )
    assert response.status_code == 201
    query = select(User).where(User.email == "admin@example.com")
    result = await db_session.execute(query)
    adm_user = result.first()[0]
    adm_user.is_superuser = True
    await db_session.commit()

    response = await async_client.post(
        "/auth/jwt/login",
        data={"username": "admin@example.com", "password": "adminpassword"}
    )
    assert response.status_code == 200
    token = response.json()["access_token"]

    response = await async_client.get(
        "/admin/links/del_unauth_links",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert "message" in response.json()