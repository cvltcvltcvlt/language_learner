from aiohttp import web
from sqlalchemy.future import select
from sqlalchemy import func, and_
from datetime import datetime, timedelta

from models import (
    User, Achievement, UserAchievement, AchievementType,
    UserLessonProgress, UserWordProgress, Lesson, Word
)
from lessons.database import get_session
from auth.login.router import jwt_required

achievement_routes = web.RouteTableDef()


@achievement_routes.get("/achievements")
@jwt_required
async def get_achievements(request):
    """
    ---
    summary: Get all achievements with user progress
    description: Returns all available achievements and user's progress towards them
    tags:
      - Achievements
    responses:
      "200":
        description: List of achievements with progress
        content:
          application/json:
            example:
              achievements: [
                {
                  "id": 1,
                  "name": "Перший урок",
                  "description": "Завершіть свій перший урок",
                  "type": "lessons_completed",
                  "target_value": 1,
                  "xp_reward": 50,
                  "icon": "🎓",
                  "unlocked": true,
                  "current_progress": 1,
                  "unlocked_at": "2025-06-13T10:30:00"
                }
              ]
    """
    user_id = request['user_id']
    
    async for session in get_session():
        # Get all achievements
        achievements_stmt = select(Achievement).order_by(Achievement.target_value)
        achievements_result = await session.execute(achievements_stmt)
        achievements = achievements_result.scalars().all()
        
        # Get user's achievement progress
        user_achievements_stmt = select(UserAchievement).where(
            UserAchievement.user_id == user_id
        )
        user_achievements_result = await session.execute(user_achievements_stmt)
        user_achievements = {ua.achievement_id: ua for ua in user_achievements_result.scalars().all()}
        
        # Calculate current progress for each achievement type
        progress_data = await calculate_user_progress(session, user_id)
        
        achievements_data = []
        for achievement in achievements:
            user_achievement = user_achievements.get(achievement.id)
            current_progress = progress_data.get(achievement.achievement_type, 0)
            
            achievement_data = {
                "id": achievement.id,
                "name": achievement.name,
                "description": achievement.description,
                "type": achievement.achievement_type.value,
                "target_value": achievement.target_value,
                "xp_reward": achievement.xp_reward,
                "icon": achievement.icon,
                "unlocked": user_achievement is not None,
                "current_progress": current_progress,
                "unlocked_at": user_achievement.unlocked_at.isoformat() if user_achievement else None
            }
            achievements_data.append(achievement_data)
        
        return web.json_response({"achievements": achievements_data})


@achievement_routes.get("/progress")
@jwt_required
async def get_user_progress(request):
    """
    ---
    summary: Get user's learning progress
    description: Returns detailed progress statistics for the user
    tags:
      - Progress
    responses:
      "200":
        description: User progress data
        content:
          application/json:
            example:
              progress:
                lessons_completed: 5
                total_lessons: 10
                words_learned: 25
                total_words: 100
                experience: 350
                streak_days: 7
                tests_passed: 12
                avg_pronunciation_score: 85
                recent_activity: []
    """
    user_id = request['user_id']
    
    async for session in get_session():
        # Get user data
        user_stmt = select(User).where(User.id == user_id)
        user_result = await session.execute(user_stmt)
        user = user_result.scalar_one_or_none()
        
        if not user:
            return web.json_response({"error": "User not found"}, status=404)
        
        # Calculate progress statistics
        progress_data = await calculate_detailed_progress(session, user_id)
        
        return web.json_response({"progress": progress_data})


@achievement_routes.post("/check-achievements")
@jwt_required
async def check_and_unlock_achievements(request):
    """
    ---
    summary: Check and unlock new achievements
    description: Checks user's progress and unlocks any new achievements
    tags:
      - Achievements
    responses:
      "200":
        description: Newly unlocked achievements
        content:
          application/json:
            example:
              new_achievements: [
                {
                  "id": 1,
                  "name": "Перший урок",
                  "xp_reward": 50
                }
              ]
    """
    user_id = request['user_id']
    
    async for session in get_session():
        new_achievements = await check_and_unlock_user_achievements(session, user_id)
        
        return web.json_response({"new_achievements": new_achievements})


async def calculate_user_progress(session, user_id):
    """Calculate current progress for all achievement types"""
    progress = {}
    
    # Lessons completed
    lessons_completed_stmt = select(func.count(UserLessonProgress.id)).where(
        and_(UserLessonProgress.user_id == user_id, UserLessonProgress.completed == True)
    )
    lessons_completed = await session.execute(lessons_completed_stmt)
    progress[AchievementType.LESSONS_COMPLETED] = lessons_completed.scalar() or 0
    
    # Words learned
    words_learned_stmt = select(func.count(UserWordProgress.id)).where(
        and_(UserWordProgress.user_id == user_id, UserWordProgress.learned == True)
    )
    words_learned = await session.execute(words_learned_stmt)
    progress[AchievementType.WORDS_LEARNED] = words_learned.scalar() or 0
    
    # Get user data for other metrics
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if user:
        progress[AchievementType.EXPERIENCE_GAINED] = user.experience
        progress[AchievementType.STREAK_DAYS] = user.streak_days
    
    return progress


async def calculate_detailed_progress(session, user_id):
    """Calculate detailed progress statistics"""
    # Lessons progress
    lessons_completed_stmt = select(func.count(UserLessonProgress.id)).where(
        and_(UserLessonProgress.user_id == user_id, UserLessonProgress.completed == True)
    )
    lessons_completed = await session.execute(lessons_completed_stmt)
    lessons_completed_count = lessons_completed.scalar() or 0
    
    total_lessons_stmt = select(func.count(Lesson.id))
    total_lessons = await session.execute(total_lessons_stmt)
    total_lessons_count = total_lessons.scalar() or 0
    
    # Words progress
    words_learned_stmt = select(func.count(UserWordProgress.id)).where(
        and_(UserWordProgress.user_id == user_id, UserWordProgress.learned == True)
    )
    words_learned = await session.execute(words_learned_stmt)
    words_learned_count = words_learned.scalar() or 0
    
    total_words_stmt = select(func.count(Word.id))
    total_words = await session.execute(total_words_stmt)
    total_words_count = total_words.scalar() or 0
    
    # User stats
    user_stmt = select(User).where(User.id == user_id)
    user_result = await session.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    # Recent activity (last 7 days)
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent_lessons_stmt = select(UserLessonProgress).where(
        and_(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.completed == True,
            UserLessonProgress.completed_at >= week_ago
        )
    ).order_by(UserLessonProgress.completed_at.desc()).limit(10)
    
    recent_lessons = await session.execute(recent_lessons_stmt)
    recent_activity = []
    
    for lesson_progress in recent_lessons.scalars().all():
        lesson_stmt = select(Lesson).where(Lesson.id == lesson_progress.lesson_id)
        lesson_result = await session.execute(lesson_stmt)
        lesson = lesson_result.scalar_one_or_none()
        
        if lesson:
            recent_activity.append({
                "type": "lesson_completed",
                "title": lesson.title,
                "xp": lesson.xp,
                "completed_at": lesson_progress.completed_at.isoformat()
            })
    
    return {
        "lessons_completed": lessons_completed_count,
        "total_lessons": total_lessons_count,
        "lessons_progress_percentage": round((lessons_completed_count / max(total_lessons_count, 1)) * 100, 1),
        "words_learned": words_learned_count,
        "total_words": total_words_count,
        "words_progress_percentage": round((words_learned_count / max(total_words_count, 1)) * 100, 1),
        "experience": user.experience if user else 0,
        "streak_days": user.streak_days if user else 0,
        "recent_activity": recent_activity
    }


async def check_and_unlock_user_achievements(session, user_id):
    """Check and unlock new achievements for user"""
    # Get current progress
    progress_data = await calculate_user_progress(session, user_id)
    
    # Get all achievements
    achievements_stmt = select(Achievement)
    achievements_result = await session.execute(achievements_stmt)
    achievements = achievements_result.scalars().all()
    
    # Get already unlocked achievements
    user_achievements_stmt = select(UserAchievement.achievement_id).where(
        UserAchievement.user_id == user_id
    )
    user_achievements_result = await session.execute(user_achievements_stmt)
    unlocked_achievement_ids = {row[0] for row in user_achievements_result.fetchall()}
    
    new_achievements = []
    
    for achievement in achievements:
        if achievement.id in unlocked_achievement_ids:
            continue
            
        current_progress = progress_data.get(achievement.achievement_type, 0)
        
        if current_progress >= achievement.target_value:
            # Unlock achievement
            user_achievement = UserAchievement(
                user_id=user_id,
                achievement_id=achievement.id,
                current_progress=current_progress
            )
            session.add(user_achievement)
            
            # Award XP to user
            if achievement.xp_reward > 0:
                user_stmt = select(User).where(User.id == user_id)
                user_result = await session.execute(user_stmt)
                user = user_result.scalar_one_or_none()
                if user:
                    user.experience += achievement.xp_reward
            
            new_achievements.append({
                "id": achievement.id,
                "name": achievement.name,
                "description": achievement.description,
                "icon": achievement.icon,
                "xp_reward": achievement.xp_reward
            })
    
    await session.commit()
    return new_achievements 