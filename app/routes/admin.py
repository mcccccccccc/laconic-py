import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db import ShortLink, User
from auth.users import super_user
from depends import get_db
from sqlalchemy import select
from config import settings


router = APIRouter()

@router.get("/links/expired")
async def get_expired_links(db: Session = Depends(get_db), super_user: User = Depends(super_user)):
    query = select(ShortLink).where((ShortLink.expires_at is not None), (ShortLink.expires_at < datetime.datetime.now()))
    r = await db.execute(query)
    expired_links = r.fetchall()

    res = [e[0].to_dict() for e in expired_links]

    return res

@router.get("/links/search")
async def search_link(original_url: str, db: Session = Depends(get_db), super_user: User = Depends(super_user)):
    query = select(ShortLink).where(ShortLink.original_url.like("%"+original_url+"%"))
    r = await db.execute(query)
    links = r.fetchall()

    res = [e[0].to_dict() for e in links]

    return res

@router.get("/links/del_unauth_links")
async def delete_unauth_links(db: Session = Depends(get_db), super_user: User = Depends(super_user)):
    query = select(ShortLink).where(ShortLink.user_id == None)
    r = await db.execute(query)
    links = r.fetchall()

    i = 0
    for link in links:
        if (datetime.datetime.now() - link[0].created_at).days > settings.max_age_auth_links_days:
            await db.delete(link[0])
            i += 1

    await db.commit()

    return {"message": f"Deleted {i} unauth links after  {settings.max_age_auth_links_days}"}
