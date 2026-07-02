import base64
import io
import os

import numpy as np
import soundfile as sf

pipeline = None
if os.getenv("ENABLE_TTS", "false").lower() in {"1", "true", "yes", "on"}:
    from kokoro import KPipeline

    pipeline = KPipeline(lang_code="a")


def text_to_speech(text: str) -> str:
    """
    Converts Clara's response text to audio format in memory.
    Returns a Base64-encoded string of the WAV audio data.
    """
    if not text or pipeline is None:
        return ""

    cleaned_text = text.replace("*", "").replace("#", "").strip()
    if not cleaned_text:
        return ""

    generator = pipeline(cleaned_text, voice="af_heart")
    audio_chunks = [audio for _, _, audio in generator]

    if not audio_chunks:
        return ""

    full_audio = np.concatenate(audio_chunks)
    byte_io = io.BytesIO()
    sf.write(byte_io, full_audio, 24000, format="WAV")
    byte_io.seek(0)
    audio_bytes = byte_io.read()
    return base64.b64encode(audio_bytes).decode("utf-8")
