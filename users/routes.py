from aiohttp import web
from sqlalchemy import select
import boto3
import uuid
import os
from aiohttp.web import Response
from botocore.exceptions import ClientError
from botocore.config import Config
import base64
import io
from PIL import Image

from lessons.database import get_session
from models import User
from users.database import get_user_by_id, update_user, delete_user, get_teachers_by_filter
from auth.login.router import jwt_required

user_routes = web.RouteTableDef()

@user_routes.get("/profile")
@jwt_required
async def get_current_user_profile(request):
    """
    ---
    summary: Get current user profile
    description: Returns the profile information of the authenticated user.
    tags:
      - Users
    security:
      - bearerAuth: []
    responses:
      "200":
        description: User profile retrieved successfully
        content:
          application/json:
            example:
              id: 1
              name: "John Doe"
              login: "john_doe"
              email: "john.doe@example.com"
              streak_days: 7
              language_level: "B2"
              experience: 1200
              totalWords: 150
              completedLessons: 12
              testResults: 8
              streakDays: 7
      "401":
        description: Unauthorized
        content:
          application/json:
            example:
              error: "Token is missing or invalid"
      "404":
        description: User not found
        content:
          application/json:
            example:
              error: "User not found"
    """
    user_id = request['user_id']
    async for session in get_session():
        user = await get_user_by_id(session, int(user_id))
        if not user:
            return web.json_response({"error": "User not found"}, status=404)

        # Calculate additional stats (mock data for now)
        total_words = user.experience // 10  # Rough calculation
        completed_lessons = user.experience // 100
        test_results = user.experience // 150
        
        user_info = {
            "id": user.id,
            "name": user.login,  # Using login as name for now
            "login": user.login,
            "email": user.email,
            "streak_days": user.streak_days,
            "language_level": user.language_level.value,
            "experience": user.experience,
            "totalWords": total_words,
            "completedLessons": completed_lessons,
            "testResults": test_results,
            "streakDays": user.streak_days,
            "avatar_url": user.avatar_url,
            "profile_picture_s3_link": user.profile_picture_s3_link
        }
        return web.json_response(user_info, status=200)

@user_routes.get("/profile/{user_id}")
async def get_user_profile(request):
    """
    ---
    summary: Get user profile by ID
    description: Returns the profile information of a user by user_id.
    tags:
      - Users
    parameters:
      - in: path
        name: user_id
        required: true
        schema:
          type: integer
        description: The ID of the user whose profile is to be fetched
    responses:
      "200":
        description: User profile retrieved successfully
        content:
          application/json:
            example:
              id: 1
              login: "john_doe"
              email: "john.doe@example.com"
              streak_days: 7
              language_level: "B2"
              experience: 1200
      "404":
        description: User not found
        content:
          application/json:
            example:
              error: "User not found"
    """
    user_id = request.match_info["user_id"]
    async for session in get_session():
        user = await get_user_by_id(session, int(user_id))
        if not user:
            return web.json_response({"error": "User not found"}, status=404)

        user_info = {
            "id": user.id,
            "login": user.login,
            "email": user.email,
            "streak_days": user.streak_days,
            "language_level": user.language_level.value,
            "experience": user.experience,
            "avatar_url": user.avatar_url,
            "profile_picture_s3_link": user.profile_picture_s3_link
        }
        return web.json_response(user_info, status=200)

@user_routes.put("/profile")
@jwt_required
async def update_current_user_profile(request):
    """
    ---
    summary: Update current user profile
    description: Updates the profile information of the authenticated user.
    tags:
      - Users
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              name:
                type: string
                description: Display name
              email:
                type: string
                format: email
                description: Email address
              language:
                type: string
                description: Interface language
              level:
                type: string
                enum: ["A1", "A2", "B1", "B2", "C1", "C2"]
                description: Language proficiency level
    responses:
      "200":
        description: Profile updated successfully
        content:
          application/json:
            example:
              message: "Profile updated successfully"
              user:
                id: 1
                name: "John Doe"
                email: "john@example.com"
                language_level: "B2"
      "401":
        description: Unauthorized
        content:
          application/json:
            example:
              error: "Unauthorized"
      "404":
        description: User not found
        content:
          application/json:
            example:
              error: "User not found"
    """
    user_id = request['user_id']
    data = await request.json()

    # Prepare update data
    update_data = {
        'user_id': user_id
    }
    
    if 'name' in data:
        update_data['login'] = data['name']  # Using login field for name
    if 'email' in data:
        update_data['email'] = data['email']
    if 'level' in data:
        update_data['language_level'] = data['level']

    async for session in get_session():
        user = await update_user(session, user_id, update_data)
        if not user:
            return web.json_response({"error": "User not found"}, status=404)

        return web.json_response({
            "message": "Profile updated successfully",
            "user": {
                "id": user.id,
                "name": user.login,
                "email": user.email,
                "language_level": user.language_level.value if hasattr(user.language_level, 'value') else user.language_level
            }
        }, status=200)

# Обновление информации о пользователе
@user_routes.put("/profile/{user_id}")
async def update_user_profile(request):
    """
    ---
    summary: Update user profile
    description: Updates the profile information of a user.
    tags:
      - Users
    parameters:
      - in: path
        name: user_id
        required: true
        schema:
          type: integer
        description: The ID of the user to be updated
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              user_id:
                type: integer
              login:
                type: string
              email:
                type: string
              streak_days:
                type: integer
              language_level:
                type: string
              experience:
                type: integer
            required:
              - user_id
    responses:
      "200":
        description: Profile updated successfully
        content:
          application/json:
            example:
              message: "Profile updated successfully"
      "401":
        description: Unauthorized - user_id does not match
        content:
          application/json:
            example:
              error: "Unauthorized"
      "404":
        description: User not found
        content:
          application/json:
            example:
              error: "User not found"
    """
    user_id = int(request.match_info["user_id"])
    data = await request.json()

    session_user_id = data.get('user_id')

    if session_user_id != user_id:
        return web.json_response({"error": "Unauthorized"}, status=401)

    async for session in get_session():
        user = await update_user(session, user_id, data)
        if not user:
            return web.json_response({"error": "User not found"}, status=404)

        return web.json_response({"message": "Profile updated successfully"}, status=200)

@user_routes.delete("/profile/{user_id}")
async def delete_user_profile(request):
    """
    ---
    summary: Delete user profile
    description: Deletes the profile of a user by user_id.
    tags:
      - Users
    parameters:
      - in: path
        name: user_id
        required: true
        schema:
          type: integer
        description: The ID of the user to be deleted
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              user_id:
                type: integer
            required:
              - user_id
    responses:
      "200":
        description: Profile deleted successfully
        content:
          application/json:
            example:
              message: "Profile deleted successfully"
      "401":
        description: Unauthorized - user_id does not match
        content:
          application/json:
            example:
              error: "Unauthorized"
      "404":
        description: User not found
        content:
          application/json:
            example:
              error: "User not found"
    """
    user_id = int(request.match_info["user_id"])

    data = await request.json()
    session_user_id = data.get('user_id')

    if session_user_id != user_id:
        return web.json_response({"error": "Unauthorized"}, status=401)

    async for session in get_session():
        success = await delete_user(session, user_id)
        if not success:
            return web.json_response({"error": "User not found"}, status=404)

        return web.json_response({"message": "Profile deleted successfully"}, status=200)


@user_routes.get("/find-teacher")
async def find_teacher(request):
    """
    ---
    summary: Find a teacher for a user
    description: Searches for teachers based on provided filters such as language level or specialization.
    tags:
      - Users
    parameters:
      - in: query
        name: language_level
        schema:
          type: string
        description: Filter by language level
      - in: query
        name: specialization
        schema:
          type: string
        description: Filter by specialization
    responses:
      "200":
        description: Teachers found successfully
        content:
          application/json:
            example:
              teachers:
                - id: 1
                  name: "Jane Smith"
                  specialization: "English Grammar"
                  language_level: "C2"
                  rating: 4.8
      "404":
        description: No teachers found
        content:
          application/json:
            example:
              error: "No teachers found"
    """
    language_level = request.query.get("language_level")
    specialization = request.query.get("specialization")

    async for session in get_session():
        teachers = await get_teachers_by_filter(session, language_level, specialization)
        if not teachers:
            return web.json_response({"error": "No teachers found"}, status=404)

        teacher_list = [
            {
                "id": teacher.id,
                "name": teacher.login,
                "specialization": getattr(teacher, 'specialization', 'General'),
                "language_level": teacher.language_level.value,
                "rating": 4.5  # Mock rating
            }
            for teacher in teachers
        ]

        return web.json_response({"teachers": teacher_list}, status=200)

@user_routes.get("/top_users")
async def get_top_users(request):
    """
    ---
    summary: Get top users by experience
    description: Returns a list of top users ranked by their experience points.
    tags:
      - Users
    parameters:
      - in: query
        name: limit
        schema:
          type: integer
          default: 10
        description: Number of top users to return
    responses:
      "200":
        description: Top users retrieved successfully
        content:
          application/json:
            example:
              users:
                - id: 1
                  login: "top_learner"
                  experience: 2500
                  rank: 1
                - id: 2
                  login: "language_master"
                  experience: 2200
                  rank: 2
    """
    limit = int(request.query.get("limit", 10))
    
    async for session in get_session():
        result = await session.execute(
            select(User)
            .order_by(User.experience.desc())
            .limit(limit)
        )
        top_users = result.scalars().all()
        
        user_list = [
            {
                "id": user.id,
                "login": user.login,
                "experience": user.experience,
                "rank": idx + 1
            }
            for idx, user in enumerate(top_users)
        ]
        
        return web.json_response({"users": user_list}, status=200)

@user_routes.post("/upload-avatar")
@jwt_required
async def upload_avatar(request):
    """
    ---
    summary: Upload user avatar to S3
    description: Upload and resize user avatar image, store in S3 and update user profile
    tags:
      - Users
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              image_data:
                type: string
                description: Base64 encoded image data
                example: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQ..."
            required:
              - image_data
    responses:
      "200":
        description: Avatar uploaded successfully
        content:
          application/json:
            schema:
              type: object
              properties:
                success:
                  type: boolean
                  example: true
                avatar_url:
                  type: string
                  example: "https://s3.amazonaws.com/bucket/avatars/user_123_uuid.jpg"
                message:
                  type: string
                  example: "Avatar uploaded successfully"
      "400":
        description: Invalid image data or format
      "500":
        description: S3 upload failed
    """
    user_id = request['user_id']
    
    try:
        data = await request.json()
        image_data = data.get('image_data')
        
        if not image_data:
            return web.json_response({"error": "No image data provided"}, status=400)
        
        # Parse base64 image data
        if image_data.startswith('data:image/'):
            # Remove data URL prefix
            image_data = image_data.split(',')[1]
        
        # Decode base64
        try:
            image_bytes = base64.b64decode(image_data)
        except Exception as e:
            return web.json_response({"error": "Invalid base64 image data"}, status=400)
        
        # Process image with PIL
        try:
            image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary (removes alpha channel)
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Resize image to 300x300 for avatars
            image = image.resize((300, 300), Image.Resampling.LANCZOS)
            
            # Save to bytes buffer
            buffer = io.BytesIO()
            image.save(buffer, format='JPEG', quality=85, optimize=True)
            processed_image_bytes = buffer.getvalue()
            buffer.close()
            
        except Exception as e:
            return web.json_response({"error": f"Invalid image format: {str(e)}"}, status=400)
        
        # Generate unique filename
        file_extension = 'jpg'
        filename = f"avatars/user_{user_id}_{uuid.uuid4().hex}.{file_extension}"
        
        # Upload to S3 (MinIO)
        try:
            # Use MinIO configuration from other parts of the project
            MINIO_ENDPOINT = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
            MINIO_BUCKET = os.getenv("S3_BUCKET_NAME", "audio-files")
            MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
            MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
            MINIO_REGION = os.getenv("MINIO_REGION", "us-east-1")
            
            s3_client = boto3.client(
                's3',
                endpoint_url=MINIO_ENDPOINT,
                aws_access_key_id=MINIO_ACCESS_KEY,
                aws_secret_access_key=MINIO_SECRET_KEY,
                region_name=MINIO_REGION,
                config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
                use_ssl=MINIO_ENDPOINT.startswith("https")
            )
            
            s3_client.put_object(
                Bucket=MINIO_BUCKET,
                Key=filename,
                Body=processed_image_bytes,
                ContentType='image/jpeg'
            )
            
            # Generate S3 URL
            avatar_url = f"{MINIO_ENDPOINT}/{MINIO_BUCKET}/{filename}"
            
        except ClientError as e:
            return web.json_response({"error": f"S3 upload failed: {str(e)}"}, status=500)
        except Exception as e:
            return web.json_response({"error": f"Upload error: {str(e)}"}, status=500)
        
        # Update user profile in database
        async for session in get_session():
            user_stmt = select(User).where(User.id == user_id)
            result = await session.execute(user_stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                return web.json_response({"error": "User not found"}, status=404)
            
            # Update both fields for compatibility
            user.avatar_url = avatar_url
            user.profile_picture_s3_link = avatar_url
            
            await session.commit()
        
        return web.json_response({
            "success": True,
            "avatar_url": avatar_url,
            "message": "Avatar uploaded successfully"
        })
        
    except Exception as e:
        return web.json_response({"error": f"Unexpected error: {str(e)}"}, status=500)

@user_routes.post("/make-admin/{user_id}")
@jwt_required
async def make_admin(request):
    """
    ---
    summary: Make user an administrator
    description: Grant administrator privileges to a user (super admin only)
    tags:
      - Users
    security:
      - bearerAuth: []
    parameters:
      - in: path
        name: user_id
        required: true
        schema:
          type: integer
        description: The ID of the user to make admin
    responses:
      "200":
        description: User successfully made admin
        content:
          application/json:
            example:
              message: "User successfully made admin"
      "401":
        description: Unauthorized
      "403":
        description: Insufficient permissions
      "404":
        description: User not found
    """
    current_user_id = request['user_id']
    target_user_id = request.match_info["user_id"]
    
    async for session in get_session():
        # Check if current user is super admin (assuming user with ID 1 is super admin)
        current_user = await get_user_by_id(session, int(current_user_id))
        if not current_user or current_user.id != 1:  # Only super admin (ID=1) can make other admins
            return web.json_response({"error": "Insufficient permissions"}, status=403)
        
        # Get target user
        target_user = await get_user_by_id(session, int(target_user_id))
        if not target_user:
            return web.json_response({"error": "User not found"}, status=404)
        
        # Update user to admin
        target_user.is_admin = True
        await session.commit()
        
        return web.json_response({"message": "User successfully made admin"}, status=200)
