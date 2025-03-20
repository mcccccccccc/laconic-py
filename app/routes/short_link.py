from fastapi import FastAPI, HTTPException
from sqlalchemy.orm import Session
import redis.asyncio as redis
import datetime
import uuid
from starlette.responses import RedirectResponse
from fastapi import Depends, BackgroundTasks, APIRouter
from sqlalchemy import select
from auth.users import current_active_user, current_user
from auth.db import User, ShortLink
from depends import get_redis, get_db
from auth.schemas import CreateShortRequest, UpdateLinkRequest


router: APIRouter = APIRouter(tags=["links"])

@router.post("/links/shorten")
async def shorten_url(
        request: CreateShortRequest,
        db: Session = Depends(get_db),
        redis_client: redis.Redis = Depends(get_redis),
        user: User = Depends(current_user)
):

    short_code = request.custom_alias if request.custom_alias else str(uuid.uuid4())[:6]

    expire_delta = None
    if request.expires_at:
        expire_delta = request.expires_at - datetime.datetime.now()
        if expire_delta.total_seconds() < 0:
            raise HTTPException(status_code=400, detail="Expiration date must be in the future")

    query = select(ShortLink).where(ShortLink.short_code == short_code)
    r = await db.execute(query)

    if r.fetchone():
        raise HTTPException(status_code=400, detail="Alias already taken")

    short_link = ShortLink(
        original_url=str(request.original_url),
        short_code=short_code,
        expires_at=request.expires_at,
        user_id=user.id if user else None,
    )
    db.add(short_link)
    await db.commit()

    if expire_delta:
        await redis_client.setex(short_code, expire_delta, short_link.original_url)
    else:
        await redis_client.set(short_code, short_link.original_url)


    return {"short_url": f"http://localhost:8000/links/{short_code}"}


@router.get("/links/search")
async def search_link(original_url: str, db: Session = Depends(get_db), user: User = Depends(current_active_user)):
    query = select(ShortLink).where(ShortLink.original_url.like("%"+original_url+"%"), ShortLink.user_id==user.id)
    r = await db.execute(query)
    short_link = r.first()

    if not short_link:
        raise HTTPException(status_code=404, detail="Short link not found")

    short_link = short_link[0]
    return {
        "short_code": short_link.short_code,
        "original_url": short_link.original_url,
        "created_at": short_link.created_at,
        "expires_at": short_link.expires_at,
        "access_count": short_link.access_count,
        "last_accessed": short_link.last_accessed,
    }

async def update_stat(short_code: str, db: Session):
    query = select(ShortLink).where(ShortLink.short_code == short_code)
    r = await db.execute(query)
    short_link = r.fetchone()
    if not short_link:
        return

    short_link = short_link[0]
    short_link.access_count += 1
    short_link.last_accessed = datetime.datetime.now()
    await db.commit()


@router.get("/links/{short_code}")
async def redirect_url(short_code: str, db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis), background_tasks: BackgroundTasks = None):

    cached_url = await redis_client.get(short_code)
    if cached_url:
        background_tasks.add_task(update_stat, short_code, db)
        return RedirectResponse(cached_url)

    # short_link = db.query(ShortLink).filter(ShortLink.short_code == short_code, (ShortLink.expires_at == None) | (ShortLink.expires_at > datetime.datetime.now())).first()
    query = select(ShortLink).where(ShortLink.short_code == short_code, (ShortLink.expires_at == None) | (ShortLink.expires_at > datetime.datetime.now()))
    r = await db.execute(query)
    short_link = r.fetchone()


    if not short_link:
        raise HTTPException(status_code=404, detail="Short link not found")

    short_link = short_link[0]
    if short_link.expires_at and short_link.expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=404, detail="Short link expired")

    if not cached_url:
        if short_link.expires_at:
            expire_delta = short_link.get_ttl()
            # expire_delta = short_link.expires_at - datetime.datetime.now()
            await redis_client.setex(short_code, expire_delta, short_link.original_url)
        else:
            await redis_client.set(short_code, short_link.original_url)

    background_tasks.add_task(update_stat, short_code, db)

    return RedirectResponse(short_link.original_url)


@router.delete("/links/{short_code}")
async def delete_link(short_code: str,
                      db: Session = Depends(get_db),
                      redis_client: redis.Redis = Depends(get_redis),
                      user: User = Depends(current_active_user)
                      ):
    query = select(ShortLink).where((ShortLink.short_code==short_code) & (ShortLink.user_id==user.id))
    r = await db.execute(query)
    short_link = r.fetchone()
    if not short_link:
        raise HTTPException(status_code=404, detail="Link not found")

    short_link = short_link[0]

    await db.delete(short_link)
    await db.commit()
    await redis_client.delete(short_code)


    return {"detail": "Link deleted"}

@router.put("/links/{short_code}")
async def update_link(
        short_code: str, request: UpdateLinkRequest,
        db: Session = Depends(get_db),
        redis_client: redis.Redis = Depends(get_redis),
        user: User = Depends(current_active_user)
    ):
    query = select(ShortLink).where((ShortLink.short_code == short_code) & (ShortLink.user_id == user.id))
    r = await db.execute(query)
    link = r.scalars().first()
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")

    if request.original_url:
        link.original_url = str(request.original_url)

    if request.expires_at:
        link.expires_at = request.expires_at

    await db.commit()

    async with redis_client.pipeline(transaction=True) as pipe:
        ttl = link.get_ttl()
        r = await (pipe.delete(short_code).setex(short_code, ttl, link.original_url))

    return {"detail": "Link updated"}

@router.get("/links/{short_code}/stats")
async def link_stats(
        short_code: str,
        db: Session = Depends(get_db),
        user: User = Depends(current_active_user)
):
    query = select(ShortLink).where((ShortLink.short_code == short_code) & (ShortLink.user_id == user.id))
    r = await db.execute(query)
    link = r.scalars().first()
    if not link:
        raise HTTPException(status_code=404, detail="Short link not found")
    return {
        "original_url": link.original_url,
        "created_at": link.created_at,
        "expires_at": link.expires_at,
        "access_count": link.access_count,
        "last_accessed": link.last_accessed,
    }