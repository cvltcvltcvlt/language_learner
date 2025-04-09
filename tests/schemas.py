from pydantic import BaseModel
from typing import List

class WordSchema(BaseModel):
    id: int
    word: str
    translation: str

class AnswerSchema(BaseModel):
    word_id: int
    translation: str

class TestResultSchema(BaseModel):
    correct: int
    incorrect: int
