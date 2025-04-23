import datetime

from aiohttp import web
import jwt
from sqlalchemy import select

from lessons.database import get_session
from auth.login.database import get_user_by_login
from models import Admin
from users.database import update_user_streaks

login_routes = web.RouteTableDef()


SECRET_KEY = "supersecretkey"
TOKEN_EXPIRATION_DAYS = 7


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
              streak_days: 5
              token: "jwt_token_here"
              user:
                id: 1
                login: "admin"
                email: "admin@example.com"
                language_level: "B2"
                is_admin: true
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
        streak_days = await update_user_streaks(session, int(user.id))

        admin = await session.execute(
            select(Admin).where(Admin.id == int(user.id))
        )
        admin = admin.scalar_one_or_none()
        is_admin = bool(admin)
    payload = {
        "user_id": user.id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=TOKEN_EXPIRATION_DAYS)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return web.json_response({
        "message": "Login successful",
        "streak_days": streak_days,
        "token": token,
        "user": {
            "id": user.id,
            "login": user.login,
            "email": user.email,
            "language_level": user.language_level.value,
            "is_admin": is_admin
        }
    })
