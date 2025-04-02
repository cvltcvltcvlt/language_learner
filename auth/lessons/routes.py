from aiohttp import web
from auth.lessons.schemas import LessonCreateSchema, AssignLessonSchema, AnswerSchema, UpdateExerciseSchema
from auth.lessons.database import create_lesson, assign_lesson_to_student, get_exercise_by_id, get_session, \
    get_user_by_id, get_lesson_by_id, get_full_lesson, update_exercise, calculate_language_level, add_word, \
    get_random_word_for_level, generate_audio_for_word
import random
from sqlalchemy.future import select
from models import Lesson, Word, User

lesson_routes = web.RouteTableDef()

@lesson_routes.post("/lessons")
async def create_lesson_route(request):
    """
    ---
    summary: Create a new lesson
    description: Allows a teacher to create a lesson with exercises.
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
              teacher_id:
                type: integer
              xp:
                type: integer
              exercises:
                type: array
                items:
                  type: object
                  properties:
                    question:
                      type: string
                    correct_answer:
                      type: string
            required:
              - title
              - lesson_type
              - teacher_id
              - exercises
    responses:
      "201":
        description: Lesson created successfully
      "403":
        description: Only teachers can create lessons
    """
    async for session in get_session():
        data = await request.json()
        lesson_data = LessonCreateSchema(**data)

        teacher = await get_user_by_id(lesson_data.teacher_id, session)
        if not teacher or teacher.role != "teacher":
            return web.json_response({"error": "Only teachers can create lessons"}, status=403)

        new_lesson = await create_lesson(lesson_data.title, lesson_data.lesson_type, lesson_data.exercises, lesson_data.xp, session)
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
    """
    ---
    summary: Complete a lesson and gain XP
    description: Allows a student to complete a lesson and gain XP points based on the lesson.
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
              lesson_id:
                type: integer
            required:
              - user_id
              - lesson_id
    responses:
      "200":
        description: XP gained successfully
      "404":
        description: Lesson or user not found
    """
    data = await request.json()
    user_id = data.get("user_id")
    lesson_id = data.get("lesson_id")

    async for session in get_session():
        user = await get_user_by_id(user_id, session)
        lesson = await get_lesson_by_id(lesson_id, session)

        if not user:
            return web.json_response({"error": "User not found"}, status=404)

        if not lesson:
            return web.json_response({"error": "Lesson not found"}, status=404)

        user.experience += lesson.xp

        user.language_level = calculate_language_level(user.experience)

        session.add(user)
        await session.commit()

        return web.json_response({"message": "XP gained successfully", "total_xp": user.experience}, status=200)


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
    teacher_id = data.get("teacher_id")

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
    """
    ---
    summary: Get a random word based on user's language level
    description: Returns a random word based on the user's current language level.
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
        description: A random word for the user
        content:
          application/json:
            example:
              word: "dog"
              translation: "собака"
              level: "A1"
      "404":
        description: No words available
    """
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
    description: Checks if the user's translation of a word is correct.
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
        description: Answer checked successfully
        content:
          application/json:
            example:
              correct: true
      "404":
        description: Word not found
      "400":
        description: Missing required fields
    """
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

        is_correct = correct_translation == user_translation

        if is_correct:
            user = await get_user_by_id(user_id, session)
            if user:
                user.experience += 1
                session.add(user)
                await session.commit()
                return web.json_response({
                    "correct": True,
                    "total_xp": user.experience
                }, status=200)

        return web.json_response({"correct": False}, status=200)


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
