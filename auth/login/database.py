from sqlalchemy.future import select
from db import SessionLocal
from models import User
import jwt
import datetime


async def get_user_by_login(login: str):
    async with SessionLocal() as session:
        result = await session.execute(select(User).filter(User.login == login))
        return result.scalars().first()

def create_access_token(user_id: int):
    """Create JWT access token for user"""
    SECRET_KEY = "supersecretkey"  # Should be in environment variables
    TOKEN_EXPIRATION_DAYS = 7
    
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=TOKEN_EXPIRATION_DAYS)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token
