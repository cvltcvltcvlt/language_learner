from datetime import timedelta, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import User

async def get_user_by_id(session: AsyncSession, user_id: int) -> User:
    result = await session.execute(select(User).filter(User.id == user_id))
    return result.scalar_one_or_none()

async def update_user(session: AsyncSession, user_id: int, data: dict) -> User:
    user = await get_user_by_id(session, user_id)
    if user:
        if 'email' in data:
            user.email = data['email']
        if 'timezone' in data:
            user.timezone = data['timezone']
        if 'language_level' in data:
            user.language_level = data['language_level']
        if 'password' in data:
            user.set_password(data['password'])
        session.add(user)
        await session.commit()
    return user

async def delete_user(session: AsyncSession, user_id: int) -> bool:
    user = await get_user_by_id(session, user_id)
    if user:
        await session.delete(user)
        await session.commit()
        return True
    return False

async def get_all_users(session: AsyncSession) -> list:
    result = await session.execute(select(User))
    return result.scalars().all()


async def get_teachers_by_filter(session):
    query = select(User).filter(User.role == 'teacher')

    result = await session.execute(query)
    teachers = result.scalars().all()

    return teachers


async def update_user_streaks(session: AsyncSession, user_id: int):
    user = await get_user_by_id(session, user_id)

    if not user:
        return None

    last_active = user.last_active
    now = datetime.utcnow()

    inactivity_duration = now - last_active

    if inactivity_duration > timedelta(days=1):
        user.streak_days = 0
        user.last_active = now
    elif inactivity_duration <= timedelta(days=1):
        if last_active.date() != now.date():
            user.streak_days += 1
        user.last_active = now

    await session.commit()

    return user.streak_days
