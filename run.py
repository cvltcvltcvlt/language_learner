from aiohttp import web
from aiohttp_swagger3 import SwaggerDocs, SwaggerUiSettings, SwaggerInfo
from aiohttp_middlewares import cors_middleware
import os

from auth.login.router import login_routes
from auth.registration.router import registration_routes
from auth.oauth_router import oauth_routes
from tests.routes import test_routes
from lessons.routes import lesson_routes
from users.routes import user_routes
from ai.router import ai_routes
from achievements.routes import achievement_routes


def create_app():
    # 1) Создаем приложение с CORS
    app = web.Application(middlewares=[cors_middleware(allow_all=True)])

    # 2) Инициализируем Swagger ДО регистрации маршрутов
    swagger = SwaggerDocs(
        app,
        info=SwaggerInfo(
            title="Language Learning API",
            version="1.0.1",
            description="API для веб-приложения изучения языков"
        ),
        swagger_ui_settings=SwaggerUiSettings(path="/swagger")
    )

    # 3) Добавляем securitySchemes в спецификацию
    swagger.spec["components"] = {
        "securitySchemes": {
            "bearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT"
            }
        }
    }

    # 4) Регистрируем handler для multipart/form-data
    async def multipart_handler(request):
        print(">> in multipart_handler, content_type=", request.content_type)
        raw = await request.post()
        # превратите MultiDict в обычный dict, чтобы не было подводных типов
        data = dict(raw)
        return data, True  # <-- вот тут отключаем валидацию

    swagger.register_media_type_handler(
        "multipart/form-data",
        multipart_handler
    )

    # 5) Добавляем ваши маршруты в Swagger
    swagger.add_routes(login_routes)
    swagger.add_routes(registration_routes)
    swagger.add_routes(oauth_routes)
    app.add_routes(test_routes)
    swagger.add_routes(lesson_routes)
    swagger.add_routes(user_routes)
    swagger.add_routes(ai_routes)
    swagger.add_routes(achievement_routes)

    # 6) Добавляем статические файлы фронтенда
    frontend_path = os.path.join(os.path.dirname(__file__), 'frontend')
    app.router.add_static('/', frontend_path, name='frontend')

    # 7) (Опционально) Если вы хотите, чтобы часть маршрутов
    # была доступна без Swagger — добавьте их отдельно:
    # app.add_routes(ai_routes)

    return app


if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="127.0.0.1", port=8080)
