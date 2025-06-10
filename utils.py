from google.cloud import speech

def assess_with_confidence(reference_text: str, audio_path: str):
    client = speech.SpeechClient()
    with open(audio_path, 'rb') as f:
        audio_data = f.read()

    audio = speech.RecognitionAudio(content=audio_data)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
        enable_word_confidence=True
    )

    response = client.recognize(config=config, audio=audio)
    confidences = []
    for result in response.results:
        for word_info in result.alternatives[0].words:
            confidences.append(word_info.confidence)
    avg_conf = sum(confidences)/len(confidences) if confidences else 0
    return {"average_confidence": avg_conf, "per_word": confidences}
