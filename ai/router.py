from aiohttp import web
import aiohttp

ai_routes = web.RouteTableDef()

@ai_routes.post("/ai_chat")
async def ai_chat_handler(request):
    data = await request.json()
    message = data.get("message")
    if not message:
        return web.json_response({"error": "Message is required"}, status=400)

    payload = {
          "model": "mistral:instruct",
          "messages": [
            {
              "role": "system",
              "content": "Ви дружній, розмовний репетитор англійської мови, який підтримує короткі діалоги рідною мовою користувача та поступово спрямовує їх до практики й вивчення англійської. Форматуйте кожен урок в HTML, використовуючи такі розділи:\n\n<h2>🎯 Словник</h2>\n<table>\n  <thead><tr><th>Слово/Фраза</th><th>Переклад</th><th>Транскрипція</th></tr></thead>\n  <tbody>\n    <!-- rows here -->\n  </tbody>\n</table>\n\n<h2>💬 Приклади</h2>\n<blockquote>\n  <!-- example sentences here -->\n</blockquote>\n\n<h2>✏️ Практичні вправи</h2>\n<ol>\n  <li><code><!-- exercise a --></code></li>\n  <li><code><!-- exercise b --></code></li>\n</ol>\n\n<h2>👍 Поради та мотивація</h2>\n<ul>\n  <li><!-- tip here --></li>\n</ul>\n\nЗавжди визначайте мову користувача та відповідайте нею для ведення діалогу. Коли ви навчаєте чи ілюструєте англійську лексику, речення чи вправи, подавайте англійський контент у наведених вище HTML-розділах. Заохочуйте користувача питаннями та підказками його мовою, щоб підтримувати діалог і практику нових матеріалів."
            },
            {
              "role": "user",
              "content": "<!-- сюди вставте повідомлення користувача -->"
            }
          ],
          "stream": False,
          "temperature": 0.6,
          "top_p": 0.9
        }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post("http://localhost:11434/api/chat", json=payload) as resp:
                if resp.status != 200:
                    return web.json_response({"error": "Ollama error"}, status=500)
                result = await resp.json()
                ai_message = result["message"]["content"]
                return web.json_response({"response": ai_message})
    except Exception as e:
        return web.json_response({"error": str(e)}, status=500)
