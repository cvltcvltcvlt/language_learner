import random
from auth.tests.database import get_words, get_user_by_id
from db import SessionLocal


async def get_words_for_test(limit=5):
    words = await get_words(limit)
    return [{"id": w.id, "word": w.word, "translation": w.translation} for w in words]

async def check_user_answers(answers):
    word_map = {w.id: w.translation for w in await get_words()}
    correct = sum(1 for ans in answers if word_map.get(ans["word_id"], "").lower() == ans["translation"].lower())
    return {"correct": correct, "incorrect": len(answers) - correct}

async def update_user_progress(user_id, correct_answers):
    async with SessionLocal() as session:
        user = await get_user_by_id(user_id)
        if user:
            user.learned_words += correct_answers
            user.streak_days += 1
            await session.commit()
