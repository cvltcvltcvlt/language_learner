from aiohttp import web
from tests.service import get_words_for_test, check_user_answers, update_user_progress
from tests.schemas import AnswerSchema

test_routes = web.RouteTableDef()

@test_routes.get("/test/words")
async def handle_get_words(request):
    """
    ---
    summary: Get words for testing
    description: Returns a list of words for the user to translate.
    tags:
      - Tests
    responses:
      "200":
        description: List of words retrieved successfully
        content:
          application/json:
            example:
              words: [
                {"id": 1, "word": "apple", "translation": "яблоко"},
                {"id": 2, "word": "table", "translation": "стол"}
              ]
    """
    words = await get_words_for_test()
    return web.json_response({"words": words})

@test_routes.post("/test/check")
async def handle_check_answers(request):
    """
    ---
    summary: Check user answers
    description: Validates user's translations and updates progress.
    tags:
      - Tests
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              user_id:
                type: integer
              answers:
                type: array
                items:
                  type: object
                  properties:
                    word_id:
                      type: integer
                    translation:
                      type: string
            required:
              - user_id
              - answers
    responses:
      "200":
        description: Test results
        content:
          application/json:
            example:
              correct: 3
              incorrect: 2
    """
    data = await request.json()
    answers = [AnswerSchema(**ans) for ans in data.get("answers", [])]
    user_id = data.get("user_id")

    results = await check_user_answers(answers)
    await update_user_progress(int(user_id), results["correct"])

    return web.json_response(results)
