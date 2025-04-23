from datetime import datetime
from functools import wraps

from aiohttp import web
from sqlalchemy import delete

from lessons.schemas import AssignLessonSchema, AnswerSchema, UpdateExerciseSchema
from lessons.database import create_lesson, assign_lesson_to_student, get_exercise_by_id, get_session, \
    get_user_by_id, get_lesson_by_id, get_full_lesson, update_exercise, calculate_language_level, add_word, \
    get_random_word_for_level, generate_audio_for_word, get_lessons_by_teacher
import random
from sqlalchemy.future import select
from models import Lesson, Word, User, Exercise, Material, LanguageLevel, UserWordProgress, UserLessonProgress, \
    AdminLevel, Admin

lesson_routes = web.RouteTableDef()


from aiohttp import web
from sqlalchemy.future import select
from lessons.database import get_session, calculate_language_level
from models import Lesson, Exercise, Material, Word, LanguageLevel


@lesson_routes.get("/lessons/available/{user_id}")
async def get_available_lessons(request):
    """
    ---
    summary: Get available lessons for a user
    description: Returns a list of lessons that the user has enough XP to access.
    tags:
      - Lessons
    responses:
      "200":
        description: List of available lessons
        content:
          application/json:
            example:
              - id: 1
                title: "Lesson 1"
                lesson_type: "vocabulary"
                xp: 10
                required_experience: 100
      "404":
        description: User not found
    """
    user_id = int(request.match_info["user_id"])

    async for session in get_session():
        user = await session.get(User, user_id)
        if not user:
            return web.json_response({"error": "User not found"}, status=404)

        stmt = select(Lesson)
        result = await session.execute(stmt)
        all_lessons = result.scalars().all()

        available_lessons = [
            {
                "id": lesson.id,
                "title": lesson.title,
                "lesson_type": lesson.lesson_type,
                "xp": lesson.xp,
                "required_experience": lesson.required_experience
            }
            for lesson in all_lessons
            if (lesson.required_experience or 0) <= user.experience
        ]

        return web.json_response(available_lessons, status=200)


@lesson_routes.post("/lessons")
async def create_lesson_route(request):
    """
    ---
    summary: Create a new lesson
    description: Allows an admin to create a lesson with exercises, materials, and words to learn.
    tags:
      - Lessons
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              creator_id:
                type: integer
              title:
                type: string
              lesson_type:
                type: string
              xp:
                type: integer
              required_experience:
                type: integer
              theory:
                type: string
              materials:
                type: array
                items:
                  type: object
                  properties:
                    title:
                      type: string
                    content_type:
                      type: string
                    content_url:
                      type: string
              exercises:
                type: array
                items:
                  type: object
                  properties:
                    question:
                      type: string
                    correct_answer:
                      type: string
              words_to_learn:
                type: array
                items:
                  type: object
                  properties:
                    word:
                      type: string
                    translation:
                      type: string
            required:
              - creator_id
              - title
              - lesson_type
              - exercises
    responses:
      "201":
        description: Lesson created successfully
      "400":
        description: Invalid input
    """
    async for session in get_session():
        data = await request.json()

        creator_id = data.get("creator_id")
        title = data.get("title")
        lesson_type = data.get("lesson_type")
        xp = data.get("xp", 10)
        required_experience = data.get("required_experience", 0)
        theory = data.get("theory", "")
        materials = data.get("materials", [])
        exercises = data.get("exercises", [])
        words_to_learn_input = data.get("words_to_learn", [])

        if not creator_id or not title or not lesson_type or not exercises:
            return web.json_response({"error": "Missing required fields"}, status=400)

        # Рассчитываем уровень языка для новых слов
        language_level_for_words = calculate_language_level(required_experience)

        # Создание урока
        lesson = Lesson(
            title=title,
            lesson_type=lesson_type,
            xp=xp,
            required_experience=required_experience,
            theory=theory,
        )
        session.add(lesson)
        await session.flush()  # Чтобы получить lesson.id

        # Добавление упражнений
        for ex in exercises:
            question = ex.get("question")
            correct_answer = ex.get("correct_answer")
            if not question or not correct_answer:
                return web.json_response({"error": "Each exercise must have question and correct_answer"}, status=400)

            exercise = Exercise(
                lesson_id=lesson.id,
                question=question,
                correct_answer=correct_answer
            )
            session.add(exercise)

        # Добавление материалов
        for mat in materials:
            material_title = mat.get("title")
            content_type = mat.get("content_type")
            content_url = mat.get("content_url")
            if not material_title or not content_type or not content_url:
                return web.json_response({"error": "Each material must have title, content_type and content_url"}, status=400)

            material = Material(
                lesson_id=lesson.id,
                title=material_title,
                content_type=content_type,
                content_url=content_url
            )
            session.add(material)

        # Добавление слов
        word_ids = []
        for word_entry in words_to_learn_input:
            word_text = word_entry.get("word")
            translation = word_entry.get("translation")

            if not word_text or not translation:
                return web.json_response({"error": "Each word must have 'word' and 'translation'"}, status=400)

            existing_word = await session.execute(
                select(Word).where(Word.word == word_text)
            )
            existing_word = existing_word.scalars().first()

            if existing_word:
                word_ids.append(int(existing_word.id))
            else:
                new_word = Word(
                    word=word_text,
                    translation=translation,
                    language_level=language_level_for_words,
                    user_id=int(creator_id)
                )
                session.add(new_word)
                await session.flush()
                word_ids.append(int(new_word.id))

        lesson.words_to_learn = word_ids
        session.add(lesson)
        await session.flush()

        await session.commit()

        return web.json_response({"message": "Lesson created successfully"}, status=201)


@lesson_routes.post("/lessons/assign")
async def assign_lesson_route(request):
    """
    ---
    summary: Assign a lesson to a student
    description: Allows a teacher to assign a lesson to a student.
    tags:
      - Lessons
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              teacher_id:
                type: integer
              student_id:
                type: integer
              lesson_id:
                type: integer
            required:
              - teacher_id
              - student_id
              - lesson_id
    responses:
      "200":
        description: Lesson assigned successfully
      "403":
        description: Only teachers can assign lessons
      "404":
        description: Student or lesson not found
      "400":
        description: Assignment failed
    """
    async for session in get_session():
        data = await request.json()
        assign_data = AssignLessonSchema(**data)

        teacher = await get_user_by_id(assign_data.teacher_id, session)
        student = await get_user_by_id(assign_data.student_id, session)
        lesson = await get_lesson_by_id(assign_data.lesson_id, session)

        if not teacher or teacher.role != "teacher":
            return web.json_response({"error": "Only teachers can assign lessons"}, status=403)

        if not student or student.role != "student":
            return web.json_response({"error": "Student not found"}, status=404)

        if not lesson:
            return web.json_response({"error": "Lesson not found"}, status=404)

        success = await assign_lesson_to_student(assign_data.teacher_id, assign_data.student_id, assign_data.lesson_id, session)
        if success:
            return web.json_response({"message": "Lesson assigned successfully"}, status=200)
        return web.json_response({"error": "Assignment failed"}, status=400)


@lesson_routes.get("/lessons/random/{user_id}")
async def get_random_lesson(request):
    """
    ---
    summary: Get a random lesson
    description: Returns a randomly selected lesson.
    tags:
      - Lessons
    parameters:
      - in: path
        name: user_id
        required: true
        schema:
          type: integer
    responses:
      "200":
        description: A random lesson
        content:
          application/json:
            example:
              lesson_id: 1
              title: "Introduction to Spanish"
      "404":
        description: No lessons available
    """
    user_id = int(request.match_info["user_id"])

    async for session in get_session():
        stmt = select(Lesson).limit(10)
        result = await session.execute(stmt)
        lessons = result.scalars().all()

        if not lessons:
            return web.json_response({"error": "No lessons available"}, status=404)

        lesson = random.choice(lessons)
        return web.json_response({"lesson_id": lesson.id, "title": lesson.title}, status=200)


@lesson_routes.post("/lessons/answer")
async def check_answer_route(request):
    """
    ---
    summary: Check exercise answer
    description: Checks if a given answer to an exercise is correct.
    tags:
      - Lessons
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              exercise_id:
                type: integer
              answer:
                type: string
            required:
              - exercise_id
              - answer
    responses:
      "200":
        description: Answer checked
        content:
          application/json:
            example:
              correct: true
      "404":
        description: Exercise not found
    """
    async for session in get_session():
        data = await request.json()
        answer_data = AnswerSchema(**data)

        exercise = await get_exercise_by_id(answer_data.exercise_id, session)
        if not exercise:
            return web.json_response({"error": "Exercise not found"}, status=404)

        is_correct = exercise.correct_answer.strip().lower() == answer_data.answer.strip().lower()
        return web.json_response({"correct": is_correct}, status=200)


@lesson_routes.get("/lessons/{lesson_id}")
async def get_lesson_route(request):
    """
    ---
    summary: Get a specific lesson
    description: Returns a specific lesson by its ID with all related exercises.
    tags:
      - Lessons
    parameters:
      - in: path
        name: lesson_id
        required: true
        schema:
          type: integer
    responses:
      "200":
        description: A specific lesson with exercises
        content:
          application/json:
            example:
              lesson_id: 1
              title: "Introduction to Spanish"
              lesson_type: "Grammar"
              exercises:
                - id: 1
                  question: "What is the capital of Spain?"
                  correct_answer: "Madrid"
                - id: 2
                  question: "What is the capital of France?"
                  correct_answer: "Paris"
      "404":
        description: Lesson not found
    """
    lesson_id = int(request.match_info["lesson_id"])

    async for session in get_session():
        full_lesson = await get_full_lesson(lesson_id, session)

        if not full_lesson:
            return web.json_response({"error": "Lesson not found"}, status=404)

        return web.json_response(full_lesson, status=200)


@lesson_routes.put("/lessons/exercise/")
async def update_exercise_route(request):
    """
    ---
    summary: Update exercise question and answer
    description: Allows a teacher to update the question and correct answer of an exercise.
    tags:
      - Lessons
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              user_id:
                type: integer
              exercise_id:
                type: integer
              question:
                type: string
              correct_answer:
                type: string
            required:
              - user_id
              - exercise_id
              - question
              - correct_answer
    responses:
      "200":
        description: Exercise updated successfully
      "403":
        description: Only teachers can update exercises
      "404":
        description: Exercise not found
    """
    data = await request.json()
    update_data = UpdateExerciseSchema(**data)

    async for session in get_session():
        exercise = await get_exercise_by_id(update_data.exercise_id, session)

        if not exercise:
            return web.json_response({"error": "Exercise not found"}, status=404)

        user_id = update_data.user_id
        user = await get_user_by_id(user_id, session)

        if not user or user.role != "teacher":
            return web.json_response({"error": "Only teachers can update exercises"}, status=403)

        # Обновляем упражнение
        updated_exercise = await update_exercise(update_data.exercise_id, update_data.question,
                                                 update_data.correct_answer, session)

        if not updated_exercise:
            return web.json_response({"error": "Failed to update exercise"}, status=500)

        return web.json_response({"message": "Exercise updated successfully"}, status=200)


@lesson_routes.post("/lessons/complete")
async def complete_lesson_route(request):
    data = await request.json()
    user_id = data.get("user_id")
    lesson_id = data.get("lesson_id")
    if not user_id or not lesson_id:
        return web.json_response({"error": "Missing user_id or lesson_id"}, status=400)
    async for session in get_session():
        user = await session.get(User, int(user_id))
        lesson = await session.get(Lesson, int(lesson_id))
        if not user or not lesson:
            return web.json_response({"error": "User or Lesson not found"}, status=404)
        words_ids = lesson.words_to_learn or []
        if words_ids:
            stmt = select(UserWordProgress.word_id).where(
                (UserWordProgress.user_id == int(user_id)) &
                (UserWordProgress.learned == True) &
                (UserWordProgress.word_id.in_(words_ids))
            )
            result = await session.execute(stmt)
            learned_words = set(result.scalars().all())
            if len(learned_words) != len(words_ids):
                return web.json_response({"error": "Not all words learned"}, status=400)
        user_lesson_progress = await session.execute(
            select(UserLessonProgress).where(
                (UserLessonProgress.user_id == int(user_id)) &
                (UserLessonProgress.lesson_id == int(lesson_id))
            )
        )
        user_lesson_progress = user_lesson_progress.scalars().first()
        if not user_lesson_progress:
            user_lesson_progress = UserLessonProgress(
                user_id=int(user_id),
                lesson_id=int(lesson_id),
                completed=True,
                completed_at=datetime.utcnow(),
                progress=100.0
            )
            session.add(user_lesson_progress)
        else:
            user_lesson_progress.completed = True
            user_lesson_progress.completed_at = datetime.utcnow()
            user_lesson_progress.progress = 100.0
        user.experience += lesson.xp
        session.add_all([user_lesson_progress, user])
        await session.commit()
        return web.json_response({
            "message": "Lesson completed successfully!",
            "total_xp": user.experience
        }, status=200)


@lesson_routes.post("/add_word")
async def add_word_to_db(request):
    """
    ---
    summary: Add a word to the database
    description: Allows a teacher to add a word with its translation and language level to the database.
    tags:
      - Lessons
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              word:
                type: string
              translation:
                type: string
              language_level:
                type: string
              teacher_id:
                type: integer
            required:
              - word
              - translation
              - language_level
              - teacher_id
    responses:
      "200":
        description: Word added successfully
      "400":
        description: Invalid language level
    """
    data = await request.json()
    word = data.get("word")
    translation = data.get("translation")
    language_level = data.get("language_level")
    teacher_id = int(data.get("teacher_id"))

    if not word or not translation or not language_level or not teacher_id:
        return web.json_response({"error": "Missing required fields"}, status=400)

    try:
        async for session in get_session():
            new_word = await add_word(session, word, translation, language_level, teacher_id)
            return web.json_response({"message": "Word added successfully", "word": new_word.word}, status=200)
    except ValueError as e:
        return web.json_response({"error": str(e)}, status=400)


@lesson_routes.get("/random_word/{user_id}")
async def get_random_word_for_user(request):
    user_id = int(request.match_info["user_id"])

    async for session in get_session():
        stmt = select(User).filter(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return web.json_response({"error": "User not found"}, status=404)

        word = await get_random_word_for_level(session, user.language_level)

        if not word:
            return web.json_response({"error": "No words available"}, status=404)

        return web.json_response({
            "word": word.word,
            "level": str(word.language_level.value)
        }, status=200)


@lesson_routes.post("/check_word_answer")
async def check_word_answer(request):
    """
    ---
    summary: Check the answer to a word translation
    description: Checks if the user's translation of a word is correct and marks word as learned.
    tags:
      - Lessons
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              user_id:
                type: integer
              word_id:
                type: integer
              user_translation:
                type: string
            required:
              - user_id
              - word_id
              - user_translation
    responses:
      "200":
        description: Result of answer check
        content:
          application/json:
            example:
              correct: true
              total_xp: 15
      "400":
        description: Missing required fields
      "404":
        description: Word not found
    """
    try:
        data = await request.json()

        user_id = data.get("user_id")
        word_id = data.get("word_id")
        user_translation = data.get("user_translation")

        if not user_id or not word_id or not user_translation:
            return web.json_response({"error": "Missing required fields"}, status=400)

        async for session in get_session():
            word_record = await session.execute(
                select(Word).filter(Word.id == word_id).limit(1)
            )
            word_record = word_record.scalar_one_or_none()

            if not word_record:
                return web.json_response({"error": "Word not found"}, status=404)

            correct_translation = word_record.translation.strip().lower()
            user_translation = user_translation.strip().lower()

            is_correct = (correct_translation == user_translation)
            print("IS CORRECT", is_correct)

            if is_correct:
                user = await get_user_by_id(int(user_id), session)
                if user:
                    user.experience += 1
                    session.add(user)

                progress = await session.execute(
                    select(UserWordProgress).where(
                        (UserWordProgress.user_id == int(user_id)) &
                        (UserWordProgress.word_id == int(word_id))
                    )
                )
                progress = progress.scalars().first()

                if progress:
                    progress.learned = True
                    progress.last_reviewed_at = datetime.utcnow()
                else:
                    progress = UserWordProgress(
                        user_id=int(user_id),
                        word_id=int(word_id),
                        learned=True
                    )
                    session.add(progress)

                await session.commit()

                return web.json_response({
                    "correct": True,
                    "total_xp": user.experience
                }, status=200)
            else:
                return web.json_response({"correct": False}, status=200)

    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)


@lesson_routes.post("/lessons/generate_audio")
async def generate_audio_route(request):
    """
    ---
    summary: Generate audio for a word
    description: Generates an audio file for a word and returns the file name.
    tags:
      - Lessons
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              word:
                type: string
              word_id:
                type: integer
            required:
              - word
              - word_id
    responses:
      "200":
        description: Audio generated successfully
        content:
          application/json:
            example:
              audio_file: "12345.mp3"
      "400":
        description: Invalid data
    """
    data = await request.json()
    word = data.get("word")
    word_id = data.get("word_id")

    if not word or not word_id:
        return web.json_response({"error": "Missing required fields"}, status=400)

    file_name = generate_audio_for_word(word, word_id)

    return web.json_response({"audio_file": file_name}, status=200)


@lesson_routes.get("/lessons")
async def get_lessons_route(request):
    """
    ---
    summary: Get all available lessons
    description: Returns a list of all lessons, with completion status if user_id provided.
    tags:
      - Lessons
    responses:
      "200":
        description: A list of lessons
    """
    async for session in get_session():
        user_id = request.query.get("user_id")

        stmt = select(Lesson)
        result = await session.execute(stmt)
        lessons = result.scalars().all()

        if not lessons:
            return web.json_response({"message": "No lessons found"}, status=404)

        completed_lessons = set()
        if user_id:
            user_progress_stmt = select(UserLessonProgress).where(UserLessonProgress.user_id == int(user_id))
            user_progress = await session.execute(user_progress_stmt)
            completed_lessons = {progress.lesson_id for progress in user_progress.scalars().all() if progress.completed}

        lessons_data = [
            {
                "id": lesson.id,
                "title": lesson.title,
                "lesson_type": lesson.lesson_type,
                "xp": lesson.xp,
                "required_experience": lesson.required_experience,
                "completed": lesson.id in completed_lessons
            }
            for lesson in lessons
        ]

        return web.json_response(lessons_data, status=200)


@lesson_routes.delete("/lessons/{lesson_id}")
async def delete_lesson_route(request):
    """
    ---
    summary: Delete a lesson
    description: Allows a teacher to delete a lesson by its ID.
    tags:
      - Lessons
    parameters:
      - in: path
        name: lesson_id
        required: true
        schema:
          type: integer
    responses:
      "200":
        description: Lesson deleted successfully
      "404":
        description: Lesson not found
    """
    lesson_id = int(request.match_info["lesson_id"])

    async for session in get_session():
        await session.execute(delete(Exercise).where(Exercise.lesson_id == lesson_id))
        lesson = await get_lesson_by_id(lesson_id, session)

        if not lesson:
            return web.json_response({"error": "Lesson not found"}, status=404)

        await session.delete(lesson)
        await session.commit()

        return web.json_response({"message": "Lesson deleted successfully"}, status=200)


@lesson_routes.put("/lessons/{lesson_id}")
async def update_lesson_route(request):
    """
    ---
    summary: Update a lesson
    description: Allows a teacher to update a lesson with exercises.
    tags:
      - Lessons
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              title:
                type: string
              lesson_type:
                type: string
              xp:
                type: integer
              exercises:
                type: array
                items:
                  type: object
                  properties:
                    index:
                      type: integer
                    question:
                      type: string
                    correct_answer:
                      type: string
            required:
              - title
              - lesson_type
              - exercises
    responses:
      "200":
        description: Lesson updated successfully
      "404":
        description: Lesson not found
    """
    data = await request.json()
    lesson_id = int(request.match_info["lesson_id"])
    lesson_data = data  # Сохраняем все данные из запроса

    async for session in get_session():
        lesson = await get_lesson_by_id(lesson_id, session)

        if not lesson:
            return web.json_response({"error": "Lesson not found"}, status=404)

        lesson.title = lesson_data.get("title", lesson.title)
        lesson.lesson_type = lesson_data.get("lesson_type", lesson.lesson_type)
        lesson.xp = int(lesson_data.get("xp", lesson.xp))

        # Обновление упражнений по порядковому номеру
        for exercise_data in lesson_data.get("exercises", []):
            index = exercise_data.get("index")  # Извлекаем порядковый номер упражнения

            if index is not None:
                # Получаем упражнение по порядковому номеру
                exercise = await session.execute(
                    select(Exercise).filter(Exercise.lesson_id == int(lesson_id))
                    .order_by(Exercise.id).offset(index).limit(1)
                )
                exercise = exercise.scalars().first()

                if exercise:
                    exercise.question = exercise_data["question"]
                    exercise.correct_answer = exercise_data["correct_answer"]
                    session.add(exercise)
                else:
                    return web.json_response({"error": f"Exercise at index {index} not found"}, status=404)
            else:
                return web.json_response({"error": "Exercise index is missing"}, status=400)

        session.add(lesson)
        await session.commit()

        return web.json_response({"message": "Lesson updated successfully"}, status=200)


@lesson_routes.get("/lesson/{lesson_id}/words/{user_id}")
async def get_words_for_lesson(request):
    """
    ---
    summary: Get words to learn for a lesson
    description: Returns words that the user has not yet learned in the lesson.
    tags:
      - Lessons
    parameters:
      - in: path
        name: lesson_id
        required: true
        schema:
          type: integer
      - in: path
        name: user_id
        required: true
        schema:
          type: integer
    responses:
      "200":
        description: List of words to learn
        content:
          application/json:
            example:
              words:
                - id: 1
                  word: "apple"
                  translation: "яблоко"
      "404":
        description: Lesson not found
    """
    lesson_id = int(request.match_info["lesson_id"])
    user_id = int(request.match_info["user_id"])

    async for session in get_session():
        lesson = await session.get(Lesson, lesson_id)

        if not lesson:
            return web.json_response({"error": "Lesson not found"}, status=404)

        words_ids = lesson.words_to_learn or []

        learned_stmt = select(UserWordProgress.word_id).where(
            (UserWordProgress.user_id == user_id) &
            (UserWordProgress.learned == True)
        )
        result = await session.execute(learned_stmt)
        learned_words_ids = set(result.scalars().all())

        words_to_learn_ids = [wid for wid in words_ids if wid not in learned_words_ids]

        if not words_to_learn_ids:
            return web.json_response({"message": "All words learned"}, status=200)

        words_stmt = select(Word).where(Word.id.in_(words_to_learn_ids))
        result = await session.execute(words_stmt)
        words = result.scalars().all()

        words_data = [{"id": word.id, "word": word.word, "translation": word.translation} for word in words]
        print('WORDS DATA', words_data)

        return web.json_response({"words": words_data}, status=200)


def admin_only(handler):
    @wraps(handler)
    async def wrapper(request):
        user_id = int(request.headers.get("X-User-Id", 0))
        if not user_id:
            return web.json_response({"error": "Unauthorized"}, status=401)

        async for session in get_session():
            admin = await session.get(Admin, user_id)
            if not admin:
                return web.json_response({"error": "Admin rights required"}, status=403)

        return await handler(request)

    return wrapper


def super_admin_only(handler):
    @wraps(handler)
    async def wrapper(request):
        user_id = int(request.headers.get("X-User-Id", 0))
        if not user_id:
            return web.json_response({"error": "Unauthorized"}, status=401)

        async for session in get_session():
            admin = await session.get(Admin, user_id)
            if not admin or admin.level.name != "SUPER_ADMIN":
                return web.json_response({"error": "Super Admin rights required"}, status=403)

        return await handler(request)

    return wrapper


@lesson_routes.post("/admin/assign")
@super_admin_only
async def assign_admin_role(request):
    """
    ---
    summary: Assign admin or super-admin role to a user
    description: Allows a super-admin to assign roles to other users.
    tags:
      - Admin
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              user_id:
                type: integer
              level:
                type: string
                enum: ["admin", "super_admin"]
            required:
              - user_id
              - level
    responses:
      "200":
        description: Admin role assigned successfully
      "400":
        description: Missing fields or invalid role
      "404":
        description: User not found
      "403":
        description: No permission
    """
    data = await request.json()
    user_id = data.get("user_id")
    level = data.get("level")

    if not user_id or not level:
        return web.json_response({"error": "Missing user_id or level"}, status=400)

    if level not in ["admin", "super_admin"]:
        return web.json_response({"error": "Invalid role. Must be 'admin' or 'super_admin'"}, status=400)

    async for session in get_session():
        user = await session.get(User, user_id)
        if not user:
            return web.json_response({"error": "User not found"}, status=404)

        admin = await session.get(Admin, user_id)

        if admin:
            # Обновляем уровень
            admin.level = AdminLevel.ADMIN if level == "admin" else AdminLevel.SUPER_ADMIN
        else:
            # Создаём запись
            admin = Admin(
                id=user_id,
                permissions="",
                level=AdminLevel.ADMIN if level == "admin" else AdminLevel.SUPER_ADMIN
            )
            session.add(admin)

        await session.commit()

        return web.json_response({"message": f"Assigned role '{level}' to user {user_id}"}, status=200)
