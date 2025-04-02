from aiohttp import web

from auth.lessons.database import get_session
from auth.login.database import get_user_by_login
from auth.users.database import update_user_streaks

login_routes = web.RouteTableDef()

@login_routes.post("/login")
async def handle_login(request):
    """
    ---
    summary: User Login
    description: Authenticates a user and returns a success message if credentials are valid.
    tags:
      - Authentication
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              login:
                type: string
              password:
                type: string
            required:
              - login
              - password
    responses:
      "200":
        description: Login successful
        content:
          application/json:
            example:
              message: Login successful
              streak_days: 5  # Пример возвращаемых стриков
      "400":
        description: Invalid input
        content:
          application/json:
            example:
              error: Invalid input
      "401":
        description: Invalid credentials
        content:
          application/json:
            example:
              error: Invalid credentials
    """
    try:
        data = await request.json()
        login, password = data["login"], data["password"]
    except Exception:
        return web.json_response({"error": "Invalid input"}, status=400)

    user = await get_user_by_login(login)
    if not user or not user.verify_password(password):
        return web.json_response({"error": "Invalid credentials"}, status=401)

    async for session in get_session():
        streak_days = await update_user_streaks(session, user.id)

    return web.json_response({
        "message": "Login successful",
        "streak_days": streak_days
    })
