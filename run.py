from aiohttp import web
from aiohttp_swagger3 import SwaggerDocs, SwaggerUiSettings
from auth.login.router import login_routes
from auth.registration.router import registration_routes
from auth.tests.routes import test_routes
from auth.lessons.routes import lesson_routes


def create_app():
    app = web.Application()

    app.add_routes(login_routes)
    app.add_routes(registration_routes)
    app.add_routes(test_routes)
    app.add_routes(lesson_routes)

    swagger = SwaggerDocs(
        app,
        title="Language Learning API",
        version="1.0.0",
        description="API для веб-приложения изучения языков",
        swagger_ui_settings=SwaggerUiSettings(path="/swagger")
    )

    swagger.add_routes(login_routes)
    swagger.add_routes(registration_routes)
    swagger.add_routes(test_routes)
    swagger.add_routes(lesson_routes)

    return app

if __name__ == "__main__":
    app = create_app()
    web.run_app(app, host="127.0.0.1", port=8080)
