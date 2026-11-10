"""Legendas sincronizadas com a narração (ASS para queimar no vídeo + SRT opcional)."""
import re
from pathlib import Path

from .config import SUBTITLE_STYLES, WIDTH, HEIGHT


def _ts_ass(t):
    t = max(0, t)
    h, m = int(t // 3600), int(t % 3600 // 60)
    return f"{h}:{m:02d}:{t % 60:05.2f}"


def _ts_srt(t):
    t = max(0, t)
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d},{ms % 1000:03d}"


def _word_times(text, start, dur, wav=None):
    """Tempos por palavra. Usa faster-whisper se instalado; senão distribui pelo nº de letras."""
    words = text.split()
    if not words:
        return []
    if wav:
        try:
            from faster_whisper import WhisperModel  # opcional
            global _WHISPER
            if "_WHISPER" not in globals():
                _WHISPER = WhisperModel("small", device="cpu", compute_type="int8")
            segs, _ = _WHISPER.transcribe(str(wav), word_timestamps=True)
            wt = [(w.start, w.end) for s in segs for w in s.words]
            if len(wt) == len(words):
                return [(w, start + a, start + b) for w, (a, b) in zip(words, wt)]
        except Exception:
            pass
    speech = max(0.1, dur - 0.25)  # descontar o respiro final
    weights = [len(re.sub(r"\W", "", w)) + 2 + (4 if re.search(r"[.!?…,;:]$", w) else 0) for w in words]
    tot = sum(weights)
    out, t = [], start
    for w, wgt in zip(words, weights):
        d = speech * wgt / tot
        out.append((w, t, t + d))
        t += d
    return out


def build(scenes: list, style_name: str, ass_path: Path, srt_path: Path = None, use_whisper=False, override: dict = None):
    st = dict(SUBTITLE_STYLES[style_name])
    if override:
        if st.get("karaoke"):  # no karaokê mantém a cor de destaque, troca fonte/contorno
            override = {k: v for k, v in override.items() if k not in ("primary",)}
        st.update(override)
    events, srt_items = [], []
    per = st["words"]
    for sc in scenes:
        wts = _word_times(sc["texto"], sc["inicio"], sc["dur_audio"], sc.get("wav") if use_whisper else None)
        for i in range(0, len(wts), per):
            chunk = wts[i:i + per]
            a, b = chunk[0][1], chunk[-1][2]
            txt_plain = " ".join(w for w, _, _ in chunk)
            if st.get("upper"):
                txt_plain = txt_plain.upper()
            if st.get("karaoke"):
                parts = []
                for w, ws, we in chunk:
                    cs = max(1, int(round((we - ws) * 100)))
                    parts.append(f"{{\\k{cs}}}{w.upper() if st.get('upper') else w}")
                txt = " ".join(parts)
            else:
                txt = txt_plain
            # quebra em 2 linhas se for longo
            if not st.get("karaoke") and len(txt) > 42:
                ws = txt.split()
                mid = len(ws) // 2
                txt = " ".join(ws[:mid]) + "\\N" + " ".join(ws[mid:])
            events.append((a, b, txt))
            srt_items.append((a, b, txt_plain))

    # evita sobreposição
    for i in range(len(events) - 1):
        if events[i][1] > events[i + 1][0]:
            events[i] = (events[i][0], events[i + 1][0], events[i][2])
            srt_items[i] = (srt_items[i][0], srt_items[i + 1][0], srt_items[i][2])

    primary = st["primary"]
    secondary = st.get("secondary", st["primary"])
    if st.get("karaoke"):  # no karaokê: Secondary = antes de falar, Primary = palavra falada
        primary, secondary = st["primary"], st["secondary"]
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {WIDTH}
PlayResY: {HEIGHT}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{st['font']},{st['size']},{primary},{secondary},{st['outline_c']},{st['back']},{-1 if st.get('bold') else 0},{-1 if st.get('italic') else 0},0,0,100,100,0,0,{st['border_style']},{st['outline']},{st['shadow']},{st['align']},80,80,{st['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    lines = [f"Dialogue: 0,{_ts_ass(a)},{_ts_ass(b)},Default,,0,0,0,,{t}" for a, b, t in events]
    ass_path.write_text(header + "\n".join(lines) + "\n", encoding="utf-8")
    if srt_path:
        srt = [f"{i}\n{_ts_srt(a)} --> {_ts_srt(b)}\n{t}\n" for i, (a, b, t) in enumerate(srt_items, 1)]
        srt_path.write_text("\n".join(srt), encoding="utf-8")
    return events
