"""User access helpers: fetch or create User row, current language."""
from datetime import datetime, timezone

from sqlalchemy import select

from bot.db import session_scope
from bot.models import User


async def get_or_create_user(tg_id: int, username: str | None = None) -> tuple[User, bool]:
    """Return (user, created) where created=True for new rows."""
    async with session_scope() as s:
        user = await s.get(User, tg_id)
        if user:
            if username and user.username != username:
                user.username = username
            return user, False
        user = User(tg_id=tg_id, username=username, lang="vi", plan="free")
        s.add(user)
        await s.flush()
        return user, True


async def get_lang(tg_id: int) -> str:
    async with session_scope() as s:
        user = await s.get(User, tg_id)
        return user.lang if user else "vi"


async def set_lang(tg_id: int, lang: str) -> None:
    async with session_scope() as s:
        user = await s.get(User, tg_id)
        if user:
            user.lang = lang


async def is_premium(tg_id: int) -> bool:
    async with session_scope() as s:
        user = await s.get(User, tg_id)
        if not user:
            return False
        if user.plan != "premium":
            return False
        if user.premium_until and user.premium_until < datetime.now(timezone.utc):
            return False
        return True


async def list_all_users() -> list[User]:
    async with session_scope() as s:
        res = await s.execute(select(User))
        return list(res.scalars().all())
