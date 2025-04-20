import enum

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, Enum as PgEnum, ARRAY
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


class MaterialType(enum.Enum):
    VIDEO = "video"
    ARTICLE = "article"
    PDF = "pdf"
    OTHER = "other"


class AdminLevel(enum.Enum):
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=False)
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    timezone = Column(String, default="UTC")

    language_level = Column(PgEnum(LanguageLevel), default=LanguageLevel.A1)
    experience = Column(Integer, default=0)
    learned_words = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)

    lessons_progress = relationship("UserLessonProgress", back_populates="user", cascade="all, delete")
    assigned_lessons = relationship("AssignedLesson", back_populates="student", cascade="all, delete")
    words = relationship("Word", back_populates="user", cascade="all, delete")

    def set_password(self, password: str):
        self.password_hash = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password_hash)


class Admin(User):
    __tablename__ = "admin"

    id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), primary_key=True)
    permissions = Column(Text)
    level = Column(PgEnum(AdminLevel), default=AdminLevel.ADMIN)


class Word(Base):
    __tablename__ = "word"

    id = Column(Integer, primary_key=True, index=True)
    word = Column(String, nullable=False, index=True)
    translation = Column(String, nullable=False)
    language_level = Column(PgEnum(LanguageLevel), nullable=False)

    user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="words")

    def __repr__(self):
        return f"<Word(id={self.id}, word={self.word}, level={self.language_level.value})>"


class Lesson(Base):
    __tablename__ = "lesson"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, nullable=False, index=True)
    lesson_type = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    theory = Column(Text)
    xp = Column(Integer, default=10)
    required_experience = Column(Integer, default=0, nullable=False)
    words_to_learn = Column(ARRAY(Integer), nullable=True)
    exercises = relationship("Exercise", back_populates="lesson", cascade="all, delete")
    materials = relationship("Material", back_populates="lesson", cascade="all, delete")

    def __repr__(self):
        return f"<Lesson(id={self.id}, title={self.title}, type={self.lesson_type})>"


class Material(Base):
    __tablename__ = "material"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False, unique=True, index=True)
    content_type = Column(PgEnum(MaterialType), nullable=False)
    content_url = Column(Text, nullable=False)

    lesson_id = Column(Integer, ForeignKey("lesson.id", ondelete="CASCADE"), nullable=False)
    lesson = relationship("Lesson", back_populates="materials")

    def __repr__(self):
        return f"<Material(id={self.id}, title={self.title}, type={self.content_type.value})>"


class Exercise(Base):
    __tablename__ = "exercise"

    id = Column(Integer, primary_key=True, index=True)
    lesson_id = Column(Integer, ForeignKey("lesson.id", ondelete="CASCADE"), nullable=False, index=True)
    question = Column(Text, nullable=False)
    correct_answer = Column(String, nullable=False)

    lesson = relationship("Lesson", back_populates="exercises")


class UserLessonProgress(Base):
    __tablename__ = "user_lesson_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    lesson_id = Column(Integer, ForeignKey("lesson.id", ondelete="CASCADE"), nullable=False, index=True)
    completed = Column(Boolean, default=False)
    completed_at = Column(DateTime, nullable=True)
    progress = Column(Float, default=0.0)

    user = relationship("User", back_populates="lessons_progress")
    lesson = relationship("Lesson")


class AssignedLesson(Base):
    __tablename__ = "assigned_lesson"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False)
    lesson_id = Column(Integer, ForeignKey("lesson.id", ondelete="CASCADE"), nullable=False)
    assigned_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("User", back_populates="assigned_lessons")
    lesson = relationship("Lesson")


class UserWordProgress(Base):
    __tablename__ = "user_word_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete="CASCADE"), nullable=False)
    word_id = Column(Integer, ForeignKey('word.id', ondelete="CASCADE"), nullable=False)
    learned = Column(Boolean, default=False)
    last_reviewed_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", backref="word_progress")
    word = relationship("Word")
