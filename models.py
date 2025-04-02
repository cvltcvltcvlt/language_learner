import enum

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, Enum
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
from passlib.context import CryptContext

Base = declarative_base()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LanguageLevel(enum.Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"
    C2 = "C2"


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow)
    learned_words = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)
    timezone = Column(String, default="UTC")
    role = Column(String, default="student")
    assigned_lessons = relationship("AssignedLesson", back_populates="student")
    language_level = Column(String, default='A1')
    experience = Column(Integer, default=0)
    lessons_progress = relationship("UserLessonProgress", back_populates="user")
    words = relationship("Word", back_populates="user")
    last_active = Column(DateTime, default=datetime.utcnow)

    def set_password(self, password: str):
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password_hash)


class Word(Base):
    __tablename__ = "words"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String, index=True)
    translation = Column(String)
    language_level = Column(Enum(LanguageLevel))

    # Связь с учителем, кто добавил это слово (если нужно)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship("User", back_populates="words")

    def __repr__(self):
        return f"<Word(id={self.id}, word={self.word}, level={self.language_level})>"


class Lesson(Base):
    __tablename__ = "lesson"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True)
    lesson_type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    xp = Column(Integer, default=10)
    teacher_id = Column(Integer)
    exercises = relationship("Exercise", back_populates="lesson")
    users = relationship("UserLessonProgress", back_populates="lesson")


class Exercise(Base):
    __tablename__ = "exercise"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lesson.id", ondelete="CASCADE"), index=True)
    question = Column(Text)
    correct_answer = Column(String)

    lesson = relationship("Lesson", back_populates="exercises")


class UserLessonProgress(Base):
    __tablename__ = "user_lesson_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), index=True)
    lesson_id = Column(Integer, ForeignKey("lesson.id", ondelete="CASCADE"), index=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    progress = Column(Float, default=0.0)

    user = relationship("User", back_populates="lessons_progress")
    lesson = relationship("Lesson", back_populates="users")


class AssignedLesson(Base):
    __tablename__ = "assigned_lesson"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lesson.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", back_populates="assigned_lessons")
    lesson = relationship("Lesson")
