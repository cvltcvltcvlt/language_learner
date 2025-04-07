from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from db import SessionLocal
from models import Lesson, Exercise, User, UserLessonProgress, LanguageLevel, Word
from gtts import gTTS
import os
import boto3
from io import BytesIO


# Получаем сессию при вызове функции
async def get_session():
    async with SessionLocal() as session:
        yield session

# Функция для получения урока по ID
async def get_lesson_by_id(lesson_id: int, session: AsyncSession):
    result = await session.execute(select(Lesson).filter(Lesson.id == lesson_id))
    return result.scalars().first()

# Функция для получения пользователя по ID
async def get_user_by_id(user_id: int, session: AsyncSession):
    result = await session.execute(select(User).filter(User.id == int(user_id)))
    return result.scalars().first()

# Функция для получения упражнения по ID
async def get_exercise_by_id(exercise_id: int, session: AsyncSession):
    result = await session.execute(select(Exercise).filter(Exercise.id == exercise_id))
    return result.scalars().first()

# Функция для создания нового урока и упражнений
async def create_lesson(title: str, lesson_type: str, exercises: list, xp: int, teacher_id: int, session: AsyncSession):
    new_lesson = Lesson(title=title, lesson_type=lesson_type, xp=xp, teacher_id=teacher_id)
    session.add(new_lesson)
    await session.commit()
    await session.refresh(new_lesson)

    # Создаем упражнения для этого урока
    for exercise in exercises:
        new_exercise = Exercise(
            lesson_id=new_lesson.id,
            question=exercise.question,
            correct_answer=exercise.correct_answer,
        )
        session.add(new_exercise)

    await session.commit()
    return new_lesson

# Функция для назначения урока студенту
async def assign_lesson_to_student(teacher_id: int, student_id: int, lesson_id: int, session: AsyncSession):
    teacher = await get_user_by_id(teacher_id, session)
    student = await get_user_by_id(student_id, session)
    lesson = await get_lesson_by_id(lesson_id, session)

    if teacher and teacher.role == "teacher" and student and student.role == "student" and lesson:
        progress = UserLessonProgress(user_id=student.id, lesson_id=lesson.id)
        session.add(progress)
        await session.commit()
        return True
    return False


async def get_full_lesson(lesson_id: int, session):
    # Получаем урок по ID
    lesson_stmt = select(Lesson).filter(Lesson.id == lesson_id)
    lesson_result = await session.execute(lesson_stmt)
    lesson = lesson_result.scalars().first()

    if not lesson:
        return None  # Если урок не найден

    # Получаем упражнения для урока
    exercise_stmt = select(Exercise).filter(Exercise.lesson_id == lesson_id)
    exercises_result = await session.execute(exercise_stmt)
    exercises = exercises_result.scalars().all()

    # Формируем результат
    return {
        "lesson_id": lesson.id,
        "title": lesson.title,
        "lesson_type": lesson.lesson_type,
        "exercises": [
            {"id": exercise.id, "question": exercise.question, "correct_answer": exercise.correct_answer}
            for exercise in exercises
        ]
    }


async def update_exercise(exercise_id: int, question: str, correct_answer: str, session: AsyncSession):
    # Получаем упражнение
    exercise = await get_exercise_by_id(exercise_id, session)

    if not exercise:
        return None  # Упражнение не найдено

    # Обновляем поля упражнения
    exercise.question = question
    exercise.correct_answer = correct_answer

    # Сохраняем изменения в базе
    session.add(exercise)
    await session.commit()

    return exercise  # Возвращаем обновленное упражнение


async def complete_lesson(user_id: int, points: int, session: AsyncSession):
    user = await session.get(User, user_id)
    if user:
        user.experience += points
        session.add(user)
        await session.commit()
        return user.experience, user.language_level
    return None, None


def calculate_language_level(experience: int) -> str:
    if experience < 100:
        return "A1"
    elif experience < 200:
        return "A2"
    elif experience < 300:
        return "B1"
    elif experience < 400:
        return "B2"
    elif experience < 500:
        return "C1"
    else:
        return "C2"


async def add_word(db: AsyncSession, word: str, translation: str, language_level: str, teacher_id: int):
    if language_level not in LanguageLevel.__members__:
        raise ValueError("Invalid language level.")

    user = await get_user_by_id(teacher_id, db)

    if user.role != "teacher":
        raise ValueError("Only teachers can add words")

    new_word = Word(word=word, translation=translation, language_level=language_level, user_id=teacher_id)

    db.add(new_word)
    await db.commit()
    await db.refresh(new_word)

    return new_word


async def get_random_word_for_level(session: AsyncSession, user_level: str):
    levels = [user_level]

    level_mapping = {
        "A1": ["A1", "A2"],
        "A2": ["A1", "A2", "B1"],
        "B1": ["A2", "B1", "B2"],
        "B2": ["B1", "B2", "C1"],
        "C1": ["B2", "C1", "C2"],
        "C2": ["C1", "C2"]
    }

    if user_level in level_mapping:
        levels.extend(level_mapping[user_level])

    result = await session.execute(
        select(Word).filter(Word.language_level.in_(levels)).order_by(func.random()).limit(1)
    )
    word = result.scalar_one_or_none()
    return word


def generate_audio_for_word(word: str, word_id: int, directory: str = "audio_files"):
    if not os.path.exists(directory):
        os.makedirs(directory)

    file_name = os.path.join(directory, f"{word_id}.mp3")

    if os.path.exists(file_name):
        print(f"Audio file for word '{word}' with id {word_id} already exists.")
        return file_name

    tts = gTTS(text=word, lang='en')
    tts.save(file_name)
    print(f"Audio saved for word '{word}' with id {word_id} as {file_name}")

    return file_name


async def get_lessons_by_teacher(teacher_id: int, session: AsyncSession):
    stmt = select(Lesson).filter(Lesson.teacher_id == teacher_id)
    result = await session.execute(stmt)
    lessons = result.scalars().all()
    return lessons
