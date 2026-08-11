import asyncio
import hashlib
import os
import threading
import time
from pathlib import Path

CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "tts_cache"
VOICE = os.environ.get("PATTYDOC_TTS_VOICE", "es-MX-DaliaNeural")

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

_mixer_ready = False
_lock = threading.Lock()


def _preferred_backend() -> str:
    return os.environ.get("PATTYDOC_TTS", "gtts").lower()


def _hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:16]


def _cache(text: str, tag: str = "") -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / f"{tag}{_hash(text)}.mp3"


def _synthesize_gtts(text: str) -> Path:
    from gtts import gTTS
    path = _cache(text)
    if not path.exists():
        gTTS(text, lang="es").save(str(path))
    return path


def _synthesize_edge(text: str) -> Path:
    import edge_tts
    path = _cache(text, tag="edge_")
    if not path.exists():
        asyncio.run(edge_tts.Communicate(text, voice=VOICE).save(str(path)))
    return path


def _play(path: Path) -> bool:
    global _mixer_ready
    import pygame
    if not _mixer_ready:
        try:
            pygame.mixer.pre_init(44100, -16, 2, 512)
            pygame.mixer.init()
            _mixer_ready = True
        except Exception as e:
            print(f"[TTS] Audio no disponible: {e}")
            return False
    pygame.mixer.music.load(str(path))
    pygame.mixer.music.play()
    while pygame.mixer.music.get_busy():
        time.sleep(0.05)
    return True


def _speak_pyttsx3(text: str, rate: int):
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty("rate", rate)
    engine.setProperty("volume", 0.9)
    voices = engine.getProperty("voices") or []
    for voice in voices:
        if "spanish" in voice.id.lower() or "es_" in voice.id.lower():
            engine.setProperty("voice", voice.id)
            break
    engine.say(text)
    engine.runAndWait()


def speak(text: str, rate: int = 150):
    """Reproduce un texto en español con una voz natural.

    Backends (orden por preferencia, configurable con PATTYDOC_TTS):
      - gtts     → voz de Google (natural, requiere internet)
      - edge     → voz neural de Microsoft (natural, requiere internet)
      - pyttsx3  → voz offline del sistema (último recurso)
    """
    if not text:
        return
    order = {
        "gtts": ["gtts", "edge", "pyttsx3"],
        "edge": ["edge", "gtts", "pyttsx3"],
        "pyttsx3": ["pyttsx3"],
    }.get(_preferred_backend(), ["gtts", "edge", "pyttsx3"])

    with _lock:
        for backend in order:
            try:
                if backend == "gtts":
                    if _play(_synthesize_gtts(text)):
                        return
                elif backend == "edge":
                    if _play(_synthesize_edge(text)):
                        return
                else:
                    _speak_pyttsx3(text, rate)
                    return
            except Exception as e:
                print(f"[TTS] backend {backend} falló: {e}")
        print("[TTS] No se pudo reproducir la voz")
