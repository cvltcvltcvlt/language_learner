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
                description: Username for the account
              email:
                type: string
                format: email
                description: Email address
              password:
                type: string
                description: Password for the account
              confirm-password:
                type: string
                description: Password confirmation (must match password)
              language_level:
                type: string
                enum: ["A1", "A2", "B1", "B2", "C1", "C2"]
                description: Language proficiency level
                default: "A1"
            required:
              - login
              - email
              - password
              - confirm-password
    responses:
      "201":
        description: User registered successfully
        content:
          application/json:
            example:
              message: User registered successfully
              user:
                id: 1
                login: "john_doe"
                email: "john@example.com"
                language_level: "A1"
      "400":
        description: Invalid input or user already exists
        content:
          application/json:
            examples:
              invalid_input:
                summary: Invalid input data
                value:
                  error: Invalid input data
              passwords_mismatch:
                summary: Passwords don't match
                value:
                  error: Passwords do not match
              user_exists:
                summary: User already exists
                value:
                  error: User already exists
    """
    try:
        data = await request.json()
        
        # Validate required fields
        required_fields = ["login", "email", "password", "confirm-password"]
        for field in required_fields:
            if field not in data or not data[field].strip():
                return web.json_response({"error": f"Field '{field}' is required"}, status=400)
        
        login = data["login"].strip()
        email = data["email"].strip()
        password = data["password"]
        confirm_password = data["confirm-password"]
        language_level = data.get("language_level", "A1")
        
        # Validate email format
        if "@" not in email or "." not in email:
            return web.json_response({"error": "Invalid email format"}, status=400)
        
        # Validate password match
        if password != confirm_password:
            return web.json_response({"error": "Passwords do not match"}, status=400)
        
        # Validate password strength
        if len(password) < 6:
            return web.json_response({"error": "Password must be at least 6 characters long"}, status=400)
        
        # Validate language level
        valid_levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
        if language_level not in valid_levels:
            language_level = "A1"  # Default fallback
        
        print(f'Registration attempt: login={login}, email={email}, language_level={language_level}')

    except Exception as e:
        print(f'Registration error: {e}')
        return web.json_response({"error": "Invalid input data"}, status=400)

    # Try to create the user
    new_user = await insert_user(login, password, email, language_level=language_level, role='1')
    if not new_user:
        return web.json_response({"error": "User already exists"}, status=400)

    return web.json_response({
        "message": "User registered successfully",
        "user": {
            "id": new_user.id,
            "login": new_user.login,
            "email": new_user.email,
            "language_level": new_user.language_level.value if hasattr(new_user.language_level, 'value') else new_user.language_level
        }
    }, status=201)
