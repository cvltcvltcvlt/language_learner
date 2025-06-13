import datetime
import jwt
from functools import wraps
from aiohttp import web
from sqlalchemy import select

from lessons.database import get_session
from auth.login.database import get_user_by_login
from models import Admin, User
from users.database import update_user_streaks

login_routes = web.RouteTableDef()

SECRET_KEY = "supersecretkey"
TOKEN_EXPIRATION_DAYS = 7

def jwt_required(f):
    """Decorator for JWT authentication"""
    @wraps(f)
    async def decorated_function(request):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                token = auth_header.split(" ")[1]  # Bearer <token>
            except IndexError:
                return web.json_response({"error": "Invalid token format"}, status=401)
        
        if not token:
            return web.json_response({"error": "Token is missing"}, status=401)
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request['user_id'] = payload['user_id']
        except jwt.ExpiredSignatureError:
            return web.json_response({"error": "Token has expired"}, status=401)
        except jwt.InvalidTokenError:
            return web.json_response({"error": "Invalid token"}, status=401)
        
        return await f(request)
    return decorated_function

@login_routes.post("/login")
async def handle_login(request):
    """
    ---
    summary: User Login
    description: Authenticates a user and returns a JWT token if credentials are valid.
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
              token: "jwt_token_here"
              user:
                id: 1
                login: "admin"
                email: "admin@example.com"
                language_level: "B2"
                streak_days: 5
                experience: 1200
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
        "token": token,
        "user": {
            "id": user.id,
            "login": user.login,
            "email": user.email,
            "language_level": user.language_level.value,
            "streak_days": streak_days,
            "experience": user.experience,
            "is_admin": is_admin
        }
    })

@login_routes.post("/verify-token")
async def verify_token(request):
    """
    ---
    summary: Verify JWT Token
    description: Verifies if the provided JWT token is valid
    tags:
      - Authentication
    security:
      - bearerAuth: []
    responses:
      "200":
        description: Token verification result
        content:
          application/json:
            schema:
              type: object
              properties:
                valid:
                  type: boolean
                  description: Whether the token is valid
                user_id:
                  type: integer
                  description: User ID if token is valid
              example:
                valid: true
                user_id: 1
      "401":
        description: Invalid or missing token
        content:
          application/json:
            example:
              error: "Invalid token"
    """
    token = None
    auth_header = request.headers.get('Authorization')
    
    if auth_header:
        try:
            token = auth_header.split(" ")[1]  # Bearer <token>
        except IndexError:
            return web.json_response({"valid": False, "error": "Invalid token format"}, status=401)
    
    if not token:
        return web.json_response({"valid": False, "error": "Token missing"}, status=401)
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user_id = payload.get("user_id")
        
        if not user_id:
            return web.json_response({"valid": False, "error": "Invalid token payload"}, status=401)
        
        # Check if user still exists
        async for session in get_session():
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return web.json_response({"valid": False, "error": "User not found"}, status=401)
        
        return web.json_response({
            "valid": True,
            "user_id": user_id
        })
        
    except jwt.ExpiredSignatureError:
        return web.json_response({"valid": False, "error": "Token expired"}, status=401)
    except jwt.InvalidTokenError:
        return web.json_response({"valid": False, "error": "Invalid token"}, status=401)
    except Exception as e:
        return web.json_response({"valid": False, "error": "Token verification failed"}, status=500)
