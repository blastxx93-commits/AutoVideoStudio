"""Narração: ElevenLabs e Fish Audio."""
from pathlib import Path

from .config import load_settings
from .utils import http, run, duration


def list_voices(provider: str, search: str = "") -> list:
    """Retorna [(nome, id)] das vozes disponíveis."""
    s = load_settings()
    if provider == "ElevenLabs":
        if not s["elevenlabs_key"]:
            raise RuntimeError("Coloque a chave da ElevenLabs em Configurações.")
        r = http("GET", "https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": s["elevenlabs_key"]})
        return [(f"{v['name']} ({v.get('category', '')})", v["voice_id"]) for v in r.json().get("voices", [])]
    if provider == "Fish Audio":
        if not s["fishaudio_key"]:
            raise RuntimeError("Coloque a chave da Fish Audio em Configurações.")
        h = {"Authorization": f"Bearer {s['fishaudio_key']}"}
        out = []
        r = http("GET", "https://api.fish.audio/model", headers=h, params={"page_size": 50, "self": "true"})
        out += [(f"[minha] {m.get('title')}", m["_id"]) for m in r.json().get("items", [])]
        if search:
            r = http("GET", "https://api.fish.audio/model", headers=h,
                     params={"page_size": 30, "title": search, "sort_by": "score"})
            out += [(m.get("title"), m["_id"]) for m in r.json().get("items", [])]
        return out
    return []


def synth(provider: str, text: str, voice_id: str, out_mp3: Path, job: dict, prev_text="", next_text="") -> Path:
    s = load_settings()
    if not voice_id:
        raise RuntimeError("Escolha uma voz (ID) para a narração.")
    if provider == "ElevenLabs":
        body = {"text": text, "model_id": job.get("eleven_model", "eleven_multilingual_v2"),
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75, "style": 0.0, "use_speaker_boost": True}}
        if body["model_id"] != "eleven_v3":
            if prev_text:
                body["previous_text"] = prev_text[-300:]
            if next_text:
                body["next_text"] = next_text[:300]
        r = http("POST", f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128",
                 headers={"xi-api-key": s["elevenlabs_key"], "Content-Type": "application/json"}, json=body, timeout=300)
        out_mp3.write_bytes(r.content)
    elif provider == "Fish Audio":
        body = {"text": text, "reference_id": voice_id, "format": "mp3", "mp3_bitrate": 128,
                "normalize": True, "latency": "normal"}
        r = http("POST", "https://api.fish.audio/v1/tts", json=body, timeout=300,
                 headers={"Authorization": f"Bearer {s['fishaudio_key']}", "Content-Type": "application/json",
                          "model": job.get("fish_model", "s1")})
        out_mp3.write_bytes(r.content)
    else:
        raise RuntimeError(f"Provedor de voz desconhecido: {provider}")
    if out_mp3.stat().st_size < 1000:
        raise RuntimeError(f"Áudio vazio retornado pela {provider}: {out_mp3.read_bytes()[:200]!r}")
    return out_mp3


def to_wav(mp3: Path, wav: Path, speed: float = 1.0) -> float:
    """Converte para WAV 48k, corta silêncio das pontas, ajusta velocidade e devolve a duração."""
    filt = ("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,"
            "areverse,silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,areverse,"
            "apad=pad_dur=0.25")
    if abs(speed - 1.0) > 0.01:
        filt += f",atempo={speed:.2f}"
    run(["ffmpeg", "-y", "-i", mp3, "-af", filt, "-ar", "48000", "-ac", "2", wav])
    return duration(wav)
