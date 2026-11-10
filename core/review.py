"""Agente de revisão: imagens repetidas, defeituosas, tela preta, problemas de áudio e legendas."""
import re
import tempfile
from pathlib import Path

from PIL import Image, ImageStat

from .images import VIDEO_EXT
from .utils import run, duration, has_video_stream


def _frame(media: Path, t=None) -> Image.Image:
    if media.suffix.lower() not in VIDEO_EXT:
        return Image.open(media).convert("RGB")
    t = t if t is not None else min(1.0, max(0.0, duration(media) / 2))
    tmp = Path(tempfile.mkstemp(suffix=".jpg")[1])
    run(["ffmpeg", "-y", "-ss", f"{t:.2f}", "-i", media, "-frames:v", "1", "-q:v", "3", tmp])
    im = Image.open(tmp).convert("RGB")
    im.load()
    tmp.unlink(missing_ok=True)
    return im


def dhash(im: Image.Image, size=12) -> int:
    g = im.convert("L").resize((size + 1, size), Image.LANCZOS)
    px = list(g.getdata())
    bits = 0
    for r in range(size):
        for c in range(size):
            bits = (bits << 1) | (px[r * (size + 1) + c] > px[r * (size + 1) + c + 1])
    return bits


def _ham(a, b):
    return bin(a ^ b).count("1")


def check_media(media: Path) -> list:
    """Problemas de uma imagem/clipe: arquivo corrompido, tela preta/branca, imagem 'lisa', resolução baixa."""
    probs = []
    try:
        if media.suffix.lower() in VIDEO_EXT:
            if not has_video_stream(media) or duration(media) < 0.5:
                return ["clipe corrompido ou curto demais"]
            frames = [_frame(media, t) for t in (0.2, max(0.3, duration(media) * 0.5))]
        else:
            frames = [_frame(media)]
            if frames[0].width < 800:
                probs.append(f"resolução baixa ({frames[0].width}px)")
    except Exception as e:
        return [f"arquivo ilegível ({str(e)[:80]})"]
    for im in frames:
        st = ImageStat.Stat(im.convert("L"))
        mean, std = st.mean[0], st.stddev[0]
        if mean < 12:
            probs.append("tela preta")
            break
        if mean > 247:
            probs.append("tela branca")
            break
        if std < 6:
            probs.append("imagem sem detalhe (cor lisa/defeito)")
            break
    return probs


def review_scenes(scenes: list, log=print, dup_threshold=10) -> dict:
    """Retorna {id_cena: [problemas]}."""
    issues, hashes = {}, []
    for sc in scenes:
        m = Path(sc["midia"])
        probs = check_media(m)
        try:
            h = dhash(_frame(m))
            for other_id, oh in hashes:
                if _ham(h, oh) <= dup_threshold:
                    probs.append(f"repetida/igual à cena {other_id}")
                    break
            hashes.append((sc["id"], h))
        except Exception:
            pass
        if probs:
            issues[sc["id"]] = probs
    return issues


def ai_vision_check(scenes: list, log=print) -> dict:
    """Revisão opcional com IA de visão (gasta créditos da API de texto)."""
    from .llm import chat, llm_available
    out = {}
    if not llm_available():
        log("  revisão por IA de visão pulada: nenhuma IA de texto configurada.")
        return out
    for sc in scenes:
        try:
            im = _frame(Path(sc["midia"]))
            im.thumbnail((768, 768))
            tmp = Path(tempfile.mkstemp(suffix=".jpg")[1])
            im.save(tmp, quality=85)
            ans = chat(f'Narration of this scene: "{sc["texto"]}".\nDoes this image have visible defects (deformed '
                       'faces/hands, garbled text, watermark, glitches) or clearly NOT match the narration? '
                       'Answer exactly "OK" or "PROBLEMA: <short reason in Portuguese>".', images=[tmp], max_tokens=100)
            tmp.unlink(missing_ok=True)
            if "PROBLEMA" in ans.upper():
                out[sc["id"]] = [ans.strip()[:150]]
        except Exception as e:
            log(f"  visão falhou na cena {sc['id']}: {e}")
    return out


def check_scene_audio(sc) -> list:
    probs = []
    words = len(sc["texto"].split())
    d = sc.get("dur_audio", 0)
    if d < 0.4:
        return ["áudio vazio"]
    wps = words / max(0.1, d - 0.25)
    if wps > 5.0:
        probs.append(f"narração rápida demais/cortada ({wps:.1f} palavras/s)")
    elif wps < 1.0 and words > 3:
        probs.append(f"narração lenta demais/com silêncio ({wps:.1f} palavras/s)")
    try:
        p = run(["ffmpeg", "-i", sc["wav"], "-af", "silencedetect=n=-45dB:d=2.0", "-f", "null", "-"])
        if "silence_start" in p.stderr:
            probs.append("silêncio longo dentro da narração")
    except Exception:
        pass
    return probs


def review_final(video: Path, expected: float, events: list = None, log=print) -> list:
    rep = []
    d = duration(video)
    if abs(d - expected) > 1.5:
        rep.append(f"duração do vídeo ({d:.1f}s) diferente da narração ({expected:.1f}s)")
    p = run(["ffmpeg", "-i", video, "-vf", "blackdetect=d=1.0:pix_th=0.08", "-af", "volumedetect",
             "-f", "null", "-"])
    for m in re.finditer(r"black_start:([\d.]+) black_end:([\d.]+)", p.stderr):
        a, b = float(m.group(1)), float(m.group(2))
        if a > 1.0 and b < d - 1.5:
            rep.append(f"tela preta de {a:.1f}s a {b:.1f}s")
    mx = re.search(r"max_volume: ([-\d.]+) dB", p.stderr)
    mean = re.search(r"mean_volume: ([-\d.]+) dB", p.stderr)
    if mx and float(mx.group(1)) > -0.1:
        rep.append(f"áudio pode estar estourando (pico {mx.group(1)} dB)")
    if mean and float(mean.group(1)) < -35:
        rep.append(f"áudio muito baixo (média {mean.group(1)} dB)")
    if events is not None:
        if not events:
            rep.append("legendas ativadas mas nenhuma legenda foi gerada")
        else:
            if events[-1][1] > d + 0.5:
                rep.append("legendas passam do fim do vídeo")
            empty = sum(1 for e in events if not e[2].strip())
            if empty:
                rep.append(f"{empty} legendas vazias")
            for i in range(len(events) - 1):
                if events[i][1] - events[i + 1][0] > 0.05:
                    rep.append("legendas sobrepostas")
                    break
    return rep
