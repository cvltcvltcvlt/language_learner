from aiohttp import web
from auth.lessons.database import get_session
from auth.users.database import get_user_by_id, update_user, delete_user, get_teachers_by_filter

user_routes = web.RouteTableDef()

@user_routes.get("/profile/{user_id}")
async def get_user_profile(request):
    """
    ---
    summary: Get user profile
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
    user_id = int(request.match_info["user_id"])

    async for session in get_session():
        user = await get_user_by_id(session, user_id)
        if not user:
            return web.json_response({"error": "User not found"}, status=404)

        user_info = {
            "id": user.id,
            "login": user.login,
            "email": user.email,
            "streak_days": user.streak_days,
            "language_level": user.language_level,
            "experience": user.experience
        }
        return web.json_response(user_info, status=200)

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
    responses:
      "200":
        description: List of teachers found
        content:
          application/json:
            example:
              teachers: [
                {"id": 1, "name": "Alice", "language_level": "B2", "specialization": "English", "timezone": "UTC"},
                {"id": 2, "name": "Bob", "language_level": "A1", "specialization": "Math", "timezone": "GMT+3"}
              ]
      "404":
        description: No teachers found
        content:
          application/json:
            example:
              error: "No teachers found"
    """
    async for session in get_session():
        teachers = await get_teachers_by_filter(session)

        if not teachers:
            return web.json_response({"error": "No teachers found"}, status=404)

        teachers_info = [{"id": teacher.id, "name": teacher.login, "language_level": teacher.language_level,
                          "timezone": teacher.timezone} for teacher in teachers]

        return web.json_response({"teachers": teachers_info}, status=200)
