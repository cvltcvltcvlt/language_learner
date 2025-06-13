import enum

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Float, Enum as PgEnum, ARRAY, UUID, JSON
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
    password_hash = Column(String, nullable=True)  # Made nullable for OAuth users
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    timezone = Column(String, default="UTC")
    profile_picture_s3_link = Column(String)
    
    # Additional user info fields
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    username = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # OAuth providers info stored as JSON
    oauth_providers = Column(JSON, nullable=True)

    language_level = Column(PgEnum(LanguageLevel), default=LanguageLevel.A1)
    experience = Column(Integer, default=0)
    learned_words = Column(Integer, default=0)
    streak_days = Column(Integer, default=0)

    lessons_progress = relationship("UserLessonProgress", back_populates="user", cascade="all, delete")
    assigned_lessons = relationship("AssignedLesson", back_populates="student", cascade="all, delete")
    words = relationship("Word", back_populates="user", cascade="all, delete")

    def set_password(self, password: str):
        if password:
            self.password_hash = pwd_context.hash(password)

    def verify_password(self, password: str) -> bool:
        if not self.password_hash:
            return False
        return pwd_context.verify(password, self.password_hash)
    
    def has_oauth_provider(self, provider: str) -> bool:
        """Check if user has connected OAuth provider"""
        if not self.oauth_providers:
            return False
        return provider in self.oauth_providers


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
    words_to_learn = Column(Text, nullable=True)
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


class AudioFiles(Base):
    __tablename__ = "audio_files"

    id = Column(UUID, primary_key=True, index=True)
    word = Column(String, nullable=False)
    s3_link = Column(String, nullable=False)


class AchievementType(enum.Enum):
    LESSONS_COMPLETED = "lessons_completed"
    WORDS_LEARNED = "words_learned"
    STREAK_DAYS = "streak_days"
    EXPERIENCE_GAINED = "experience_gained"
    TESTS_PASSED = "tests_passed"
    PRONUNCIATION_SCORE = "pronunciation_score"


class Achievement(Base):
    __tablename__ = "achievement"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    achievement_type = Column(PgEnum(AchievementType), nullable=False)
    target_value = Column(Integer, nullable=False)  # Required value to unlock
    xp_reward = Column(Integer, default=0)
    icon = Column(String, nullable=True)  # Emoji or icon name
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Achievement(id={self.id}, name={self.name}, type={self.achievement_type.value})>"


class UserAchievement(Base):
    __tablename__ = "user_achievement"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True)
    achievement_id = Column(Integer, ForeignKey("achievement.id", ondelete="CASCADE"), nullable=False, index=True)
    unlocked_at = Column(DateTime, default=datetime.utcnow)
    current_progress = Column(Integer, default=0)  # Current progress towards achievement

    user = relationship("User")
    achievement = relationship("Achievement")

    def __repr__(self):
        return f"<UserAchievement(user_id={self.user_id}, achievement_id={self.achievement_id})>"
