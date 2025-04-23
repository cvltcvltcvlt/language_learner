from aiohttp import web
from auth.registration.database import insert_user

registration_routes = web.RouteTableDef()


@registration_routes.post("/register")
async def handle_registration(request):
    """
    ---
    summary: User Registration
    description: Registers a new user in the system
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
              email:
                type: string
              role:
                type: string
                enum: ["student", "teacher"]
              language_level:
                type: string
            required:
              - login
              - password
    responses:
      "201":
        description: User registered successfully
        content:
          application/json:
            example:
              message: User registered successfully
      "400":
        description: Invalid input or user already exists
        content:
          application/json:
            example:
              error: User already exists
    """
    try:
        data = await request.json()
        login = data["login"]
        password = data["password"]
        email = data.get("email", None)
        language_level = data.get("language_level", "A1")

    except Exception:
        return web.json_response({"error": "Invalid input"}, status=400)

    new_user = await insert_user(login, password, email, language_level)
    if not new_user:
        return web.json_response({"error": "User already exists"}, status=400)

    return web.json_response({"message": "User registered successfully"}, status=201)
