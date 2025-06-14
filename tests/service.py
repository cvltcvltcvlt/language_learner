from sqlalchemy import select, func

from lessons.database import get_session
from tests.database import get_words, get_user_by_id
from db import SessionLocal
from models import Word


async def get_words_for_test():
    """Get multiple words for testing"""
    async for session in get_session():
        # Get 15 random words for testing
        result = await session.execute(
            select(Word).order_by(func.random()).limit(15)
        )
        words = result.scalars().all()
        
        if words:
            return [
                {
                    "id": word.id, 
                    "word": word.word, 
                    "translation": word.translation
                } 
                for word in words
            ]
    return []

async def check_user_answers(answers):
    word_map = {w.id: w.translation for w in await get_words()}
    correct = sum(
        1 for ans in answers
        if word_map.get(ans.word_id, "").lower() == ans.translation.lower()
    )
    return {"correct": correct, "incorrect": len(answers) - correct}

async def update_user_progress(user_id, correct_answers):
    async with SessionLocal() as session:
        user = await get_user_by_id(user_id)
        if user:
            user.learned_words += correct_answers
            user.streak_days += 1
            await session.commit()
