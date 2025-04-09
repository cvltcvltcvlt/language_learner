from sqlalchemy.future import select
from db import SessionLocal
from models import Word, User

async def get_user_by_id(user_id: int):
    async with SessionLocal() as session:
        return await session.get(User, int(user_id))

async def get_words(limit=5):
    async with SessionLocal() as session:
        result = await session.execute(select(Word))
        words = result.scalars().all()
    return words[:limit]
