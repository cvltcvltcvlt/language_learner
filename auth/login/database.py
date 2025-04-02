from sqlalchemy.future import select
from db import SessionLocal
from models import User


async def get_user_by_login(login: str):
    async with SessionLocal() as session:
        result = await session.execute(select(User).filter(User.login == login))
        return result.scalars().first()
