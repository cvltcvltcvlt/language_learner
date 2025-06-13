from datetime import timedelta, datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from models import User

async def get_user_by_id(session: AsyncSession, user_id: int) -> User:
    result = await session.execute(select(User).filter(User.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_email(email: str) -> User:
    """Get user by email address"""
    from db import SessionLocal
    async with SessionLocal() as session:
        result = await session.execute(select(User).filter(User.email == email))
        return result.scalar_one_or_none()

async def create_user(email: str, username: str = None, first_name: str = "", last_name: str = "", 
                     language_level: str = "A1", avatar_url: str = None, oauth_providers: dict = None, 
                     is_active: bool = True, **kwargs) -> User:
    """Create a new user"""
    from db import SessionLocal
    
    # Language level XP mapping
    LANGUAGE_LEVEL_XP = {
        "A1": 0, "A2": 200, "B1": 500, "B2": 1000, "C1": 2000, "C2": 3000,
    }
    
    async with SessionLocal() as session:
        # Check if user already exists
        existing_user = await session.execute(select(User).filter(User.email == email))
        if existing_user.scalar_one_or_none():
            raise ValueError("User with this email already exists")
        
        # Generate username if not provided
        if not username:
            username = email.split('@')[0]
            
        # Check if username is taken and modify if needed
        existing_username = await session.execute(select(User).filter(User.login == username))
        if existing_username.scalar_one_or_none():
            username = f"{username}_{len(username)}"
        
        initial_xp = LANGUAGE_LEVEL_XP.get(language_level, 0)
        
        new_user = User(
            login=username,
            email=email,
            language_level=language_level,
            experience=initial_xp,
            # Add other fields as available in the User model
        )
        
        # Set additional fields if they exist in the User model
        if hasattr(new_user, 'first_name'):
            new_user.first_name = first_name
        if hasattr(new_user, 'last_name'):
            new_user.last_name = last_name
        if hasattr(new_user, 'avatar_url'):
            new_user.avatar_url = avatar_url
        if hasattr(new_user, 'oauth_providers'):
            new_user.oauth_providers = oauth_providers
        if hasattr(new_user, 'is_active'):
            new_user.is_active = is_active
        
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        return new_user

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
