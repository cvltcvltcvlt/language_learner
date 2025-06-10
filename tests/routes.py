import os
import uuid
from uuid import uuid4

from aiohttp import web
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from botocore.client import Config

from models import Word, AudioFiles
from tests.service import get_words_for_test, check_user_answers, update_user_progress
from tests.schemas import AnswerSchema
import tempfile
import subprocess
from pathlib import Path
import boto3

from vosk import Model, KaldiRecognizer
import wave
import json

from lessons.database import get_session

test_routes = web.RouteTableDef()

VOSK_MODEL = Model("models/vosk-model-small-en-us-0.15")

S3_ENDPOINT = os.getenv("S3_ENDPOINT_URL", "http://localhost:9000")
S3_BUCKET   = os.getenv("S3_BUCKET_NAME",  "audio-files")

s3 = boto3.client(
    "s3",
    endpoint_url           = S3_ENDPOINT,
    aws_access_key_id      = os.getenv("MINIO_ACCESS_KEY", os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")),
    aws_secret_access_key  = os.getenv("MINIO_SECRET_KEY", os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")),
    region_name            = os.getenv("AWS_REGION", "us-east-1"),
    config                 = Config(signature_version="s3v4")
)


async def fetch_word_from_db(word_id: int, session: AsyncSession) -> Word:
    stmt = select(Word).where(Word.id == word_id)
    result = await session.execute(stmt)
    word_obj = result.scalar_one_or_none()
    if word_obj is None:
        raise web.HTTPNotFound(text=f"Word with id={word_id} not found")
    return word_obj


def assess_with_vosk(reference_text: str, wav_path: str):
    wf = wave.open(wav_path, "rb")
    rec = KaldiRecognizer(VOSK_MODEL, wf.getframerate())
    rec.SetWords(True)

    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        rec.AcceptWaveform(data)

    final = json.loads(rec.FinalResult())
    confidences = [w.get("conf", 0.0) for w in final.get("result", [])]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    return {"average_confidence": avg_conf, "per_word": confidences}


@test_routes.get("/test/words")
async def handle_get_words(request):
    """
    ---
    summary: Get words for testing
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
    summary: Check user answers and optionally pronunciation
    description: |
      Приходит либо JSON, либо multipart/form-data:
      - JSON: {"user_id": int, "answers": [{word_id, translation}, ...]}
      - multipart/form-data: user_id, optional answers (как JSON-строка), optional word_id, optional audio-бинарник
      Возвращает:
        correct, incorrect — если были переводы
        average_confidence, per_word — если было аудио
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
        multipart/form-data:
          schema:
            type: object
            properties:
              user_id:
                type: integer
              answers:
                type: string
                description: JSON-строка с массивом {word_id, translation}
              word_id:
                type: integer
              audio:
                type: string
                format: binary
            required:
              - user_id
    responses:
      "200":
        description: Test results (translations + optional pronunciation)
        content:
          application/json:
            schema:
              type: object
              properties:
                correct:
                  type: integer
                incorrect:
                  type: integer
                average_confidence:
                  type: number
                per_word:
                  type: array
                  items:
                    type: number
    """
    results = {}
    audio_file = None
    word_id = None

    async for session in get_session():
        if request.content_type.startswith("multipart/"):
            data = await request.post()
            user_id = int(data["user_id"])

            if "answers" in data:
                raw = data["answers"]
                answers_list = json.loads(raw)
                answers = [AnswerSchema(**ans) for ans in answers_list]
                results = await check_user_answers(answers)
                await update_user_progress(user_id, results["correct"])

            if "audio" in data and data["audio"].file:
                word_id = int(data.get("word_id"))
                audio_file = data["audio"].file

        else:
            payload = await request.json()
            user_id = int(payload["user_id"])
            answers = [AnswerSchema(**ans) for ans in payload.get("answers", [])]
            results = await check_user_answers(answers)
            await update_user_progress(user_id, results["correct"])

        if audio_file and word_id is not None:
            tmp_webm = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
            tmp_webm.write(audio_file.read())
            tmp_webm.close()
            word_test_id = uuid.uuid4()
            key = f"user/{user_id}/pron_{word_id}_{word_test_id}.webm"
            await session.commit()

            wav_path = tmp_webm.name.replace(".webm", ".wav")
            subprocess.run(
                ["ffmpeg", "-i", tmp_webm.name, "-ar", "16000", "-ac", "1", wav_path],
                check=True
            )

            word_obj = await fetch_word_from_db(word_id, session)
            pron = assess_with_vosk(word_obj.word, wav_path)

            Path(tmp_webm.name).unlink()
            Path(wav_path).unlink()

            results.update(pron)

        return web.json_response(results)
