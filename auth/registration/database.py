from sqlalchemy.future import select
from db import SessionLocal
from models import User


async def get_user_by_login(login: str):
    async with SessionLocal() as session:
        result = await session.execute(select(User).filter(User.login == login))
        return result.scalars().first()


LANGUAGE_LEVEL_XP = {
    "A1": 0,
    "A2": 200,
    "B1": 500,
    "B2": 1000,
    "C1": 2000,
    "C2": 3000,
}


async def insert_user(login: str, password: str, email: str, role: str, language_level: str = "A1"):
    async with SessionLocal() as session:
        existing_user = await get_user_by_login(login)
        if existing_user:
            return None

        initial_xp = LANGUAGE_LEVEL_XP[language_level]

        new_user = User(
            login=login,
            email=email,
            role=role,
            language_level=language_level,
            experience=initial_xp,
        )

        new_user.set_password(password)

        session.add(new_user)
        await session.commit()
        return new_user

