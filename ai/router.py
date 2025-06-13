import re
import json
from datetime import datetime
from aiohttp import web
import aiohttp
import logging

from auth.login.router import jwt_required

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MODEL_NAME = "deepseek-r1"
SYSTEM_PROMPT = (
    "You are an English tutor. Always reply in the user's language and try to get him to learning english. If user is asking how to say something in english tell him the english phrase and swith back to users language"
)

ai_routes = web.RouteTableDef()

# In-memory storage for chat history (in production, use a database)
chat_history = {}

@ai_routes.post('/chat')
@jwt_required
async def ai_chat_handler(request: web.Request) -> web.Response:
    """
    ---
    summary: AI Chat
    description: Send a message to the AI tutor and get a response
    tags:
      - AI Chat
    security:
      - bearerAuth: []
    requestBody:
      required: true
      content:
        application/json:
          schema:
            type: object
            properties:
              message:
                type: string
                description: The message to send to the AI
            required:
              - message
    responses:
      "200":
        description: AI response received successfully
        content:
          application/json:
            example:
              response: "Hello! I'm here to help you learn English. What would you like to practice today?"
              timestamp: "2024-01-15T10:30:00Z"
      "400":
        description: Invalid input
        content:
          application/json:
            example:
              error: "Message is required"
      "401":
        description: Unauthorized
        content:
          application/json:
            example:
              error: "Token is missing or invalid"
      "500":
        description: AI service error
        content:
          application/json:
            example:
              error: "AI service temporarily unavailable"
    """
    try:
        data = await request.json()
        user_message = (data.get("message") or "").strip()
        user_id = request['user_id']
        
        if not user_message:
            return web.json_response({"error": "Message is required"}, status=400)

        # Store user message in history
        if user_id not in chat_history:
            chat_history[user_id] = []
        
        chat_history[user_id].append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().isoformat()
        })

        # Prepare conversation context (last 10 messages)
        recent_messages = chat_history[user_id][-10:]
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        
        for msg in recent_messages:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        payload = {
            "model": MODEL_NAME,
            "messages": messages,
            "stream": False,
            "temperature": 0.4,
            "top_p": 0.8
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("http://localhost:11434/api/chat", json=payload) as resp:
                    if resp.status != 200:
                        txt = await resp.text()
                        logger.error(f"Ollama error {resp.status}: {txt}")
                        # Fallback response
                        ai_response = "Вибачте, зараз у мене технічні проблеми. Спробуйте пізніше."
                    else:
                        result = await resp.json()
                        ai_response = result["message"]["content"]
                        # Clean up thinking tags
                        ai_response = re.sub(r"<think>.*?</think>", "", ai_response, flags=re.DOTALL)
                        ai_response = ai_response.strip()
        except Exception as e:
            logger.error(f"Error connecting to Ollama: {e}")
            ai_response = "Вибачте, зараз у мене технічні проблеми. Спробуйте пізніше."

        # Store AI response in history
        chat_history[user_id].append({
            "role": "assistant",
            "content": ai_response,
            "timestamp": datetime.now().isoformat()
        })

        logger.info(f"→ AI response for user {user_id}: {ai_response!r}")
        
        return web.json_response({
            "response": ai_response,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Chat handler error: {e}")
        return web.json_response({"error": "Internal server error"}, status=500)

@ai_routes.get('/chat/history')
@jwt_required
async def get_chat_history(request: web.Request) -> web.Response:
    """
    ---
    summary: Get Chat History
    description: Retrieve the chat history for the authenticated user
    tags:
      - AI Chat
    security:
      - bearerAuth: []
    parameters:
      - in: query
        name: limit
        schema:
          type: integer
          default: 50
        description: Number of recent messages to return
    responses:
      "200":
        description: Chat history retrieved successfully
        content:
          application/json:
            example:
              history:
                - id: "session_1"
                  title: "English Grammar Help"
                  date: "2024-01-15T10:30:00Z"
                  messages:
                    - role: "user"
                      content: "How do I use Present Perfect?"
                      timestamp: "2024-01-15T10:30:00Z"
                    - role: "assistant"
                      content: "Present Perfect is used for actions that happened at an unspecified time..."
                      timestamp: "2024-01-15T10:30:15Z"
      "401":
        description: Unauthorized
        content:
          application/json:
            example:
              error: "Token is missing or invalid"
    """
    user_id = request['user_id']
    limit = int(request.query.get("limit", 50))
    
    if user_id not in chat_history:
        return web.json_response({"history": []})
    
    messages = chat_history[user_id][-limit:]
    
    # Group messages into sessions (simplified)
    sessions = []
    if messages:
        # Create a single session for now
        first_message = messages[0] if messages else None
        title = "Чат з AI помічником"
        if first_message and len(first_message["content"]) > 0:
            # Use first few words as title
            words = first_message["content"].split()[:4]
            title = " ".join(words) + ("..." if len(words) == 4 else "")
        
        sessions.append({
            "id": f"session_{user_id}",
            "title": title,
            "date": messages[0]["timestamp"] if messages else datetime.now().isoformat(),
            "messages": messages
        })
    
    return web.json_response({"history": sessions})

@ai_routes.delete('/chat/history')
@jwt_required
async def clear_chat_history(request: web.Request) -> web.Response:
    """
    ---
    summary: Clear Chat History
    description: Clear all chat history for the authenticated user
    tags:
      - AI Chat
    security:
      - bearerAuth: []
    responses:
      "200":
        description: Chat history cleared successfully
        content:
          application/json:
            example:
              message: "Chat history cleared successfully"
      "401":
        description: Unauthorized
        content:
          application/json:
            example:
              error: "Token is missing or invalid"
    """
    user_id = request['user_id']
    
    if user_id in chat_history:
        del chat_history[user_id]
    
    return web.json_response({"message": "Chat history cleared successfully"})

# Legacy endpoint for backward compatibility
@ai_routes.post('/ai_chat')
async def ai_chat_handler_legacy(request: web.Request) -> web.Response:
    """Legacy endpoint - redirects to new /chat endpoint"""
    return await ai_chat_handler(request)
