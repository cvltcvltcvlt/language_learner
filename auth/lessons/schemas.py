from pydantic import BaseModel
from typing import List

class ExerciseSchema(BaseModel):
    question: str
    correct_answer: str

class LessonCreateSchema(BaseModel):
    teacher_id: int
    title: str
    lesson_type: str
    xp: int
    exercises: List[ExerciseSchema]

class AssignLessonSchema(BaseModel):
    teacher_id: int
    student_id: int
    lesson_id: int

class AnswerSchema(BaseModel):
    exercise_id: int
    answer: str

class UpdateExerciseSchema(BaseModel):
    user_id: int
    exercise_id: int
    question: str
    correct_answer: str
