"""Prévias ("slides de exemplo") de cada opção: movimento, transição, legenda e template.
Tudo é gerado no seu PC com cenas de exemplo e fica guardado em cache (só demora na primeira vez)."""
import hashlib
import json
import math
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

from .config import DATA_DIR, TRANSITIONS, RANDOM_POOL
from .utils import run

PASTA = DATA_DIR / "previas"
PW, PH, PFPS = 640, 360, 24


def _cache(*partes, ext=".mp4") -> Path:
    PASTA.mkdir(parents=True, exist_ok=True)
    h = hashlib.md5(json.dumps(partes, ensure_ascii=False).encode()).hexdigest()[:12]
    return PASTA / f"p_{h}{ext}"


def _paisagem(tipo: int) -> Image.Image:
    """Cenas de exemplo desenhadas por código (montanhas, mar, floresta)."""
    W, H = 1920, 1080
    rnd = random.Random(tipo)
    paletas = [((18, 26, 64), (92, 60, 120)), ((250, 140, 60), (120, 40, 70)), ((30, 48, 44), (120, 140, 120))]
    c1, c2 = paletas[tipo % 3]
    im = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(im)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=tuple(int(c1[i] + (c2[i] - c1[i]) * k) for i in range(3)))
    if tipo % 3 == 0:  # lua e estrelas
        for _ in range(180):
            x, y = rnd.randrange(W), rnd.randrange(int(H * .55))
            d.point((x, y), fill=(230, 230, 255))
        d.ellipse([1350, 140, 1530, 320], fill=(240, 236, 210))
    elif tipo % 3 == 1:  # sol
        d.ellipse([820, 420, 1100, 700], fill=(255, 214, 120))
    else:  # neblina
        n = Image.new("RGB", (W, H), (200, 210, 200))
        im = Image.blend(im, n, 0.15)
        d = ImageDraw.Draw(im)
    for camada in range(3):
        base = H * (0.55 + 0.13 * camada)
        cor = tuple(max(0, int(c2[i] * (0.55 - 0.17 * camada))) for i in range(3))
        pts = [(0, H)]
        for x in range(0, W + 80, 80):
            pts.append((x, base - 140 * math.sin(x / (230 + 60 * camada) + camada * 2 + tipo) - rnd.randrange(0, 60)))
        pts.append((W, H))
        d.polygon(pts, fill=cor)
    if tipo % 3 == 1:  # mar
        d.rectangle([0, int(H * .78), W, H], fill=(60, 30, 60))
        for y in range(int(H * .78), H, 14):
            d.line([(rnd.randrange(0, 600), y), (rnd.randrange(1200, W), y)], fill=(250, 170, 110), width=2)
    return im.filter(ImageFilter.GaussianBlur(1))


def cena_exemplo(tipo: int) -> Path:
    PASTA.mkdir(parents=True, exist_ok=True)
    p = PASTA / f"cena_exemplo_{tipo}.jpg"
    if not p.exists():
        _paisagem(tipo).save(p, quality=92)
    return p


def movimento(mov: str, intensidade: str = "Média") -> Path:
    from .render import render_scene
    out = _cache("mov", mov, intensidade)
    if not out.exists():
        render_scene(cena_exemplo(0), 3.5, out, mov, intensidade, PW, PH, PFPS)
    return out


def transicao(escolha: str, dur: float = 0.5) -> Path:
    from .render import render_scene
    out = _cache("trans", escolha, round(dur, 2))
    if out.exists():
        return out
    nome = TRANSITIONS.get(escolha)
    n = 3 if nome == "random" else 2
    trans = random.sample(RANDOM_POOL, n - 1) if nome == "random" else [nome] * (n - 1)
    seg = 1.8
    clips = []
    for i in range(n):
        c = _cache("seg", i, seg + (dur if nome else 0))
        if not c.exists():
            render_scene(cena_exemplo(i), seg + (dur if (nome and i < n - 1) else 0), c, "Zoom in", "Suave", PW, PH, PFPS)
        clips.append(c)
    if not nome:
        lst = out.with_suffix(".txt")
        lst.write_text("".join(f"file '{c.resolve().as_posix()}'\n" for c in clips), encoding="utf-8")
        run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])
        return out
    cmd = ["ffmpeg", "-y"]
    for c in clips:
        cmd += ["-i", c]
    fc, prev = [], "[0:v]"
    for k in range(n - 1):
        lab = f"[v{k}]"
        fc.append(f"{prev}[{k + 1}:v]xfade=transition={trans[k]}:duration={dur}:offset={seg * (k + 1):.3f}{lab}")
        prev = lab
    cmd += ["-filter_complex", ";".join(fc), "-map", prev, "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
            "-pix_fmt", "yuv420p", out]
    run(cmd)
    return out


def legenda(estilo: str, override: dict = None, texto="Ninguém sabia o seu nome verdadeiro") -> Path:
    from . import subtitles
    out = _cache("leg", estilo, override or {}, texto, ext=".png")
    if out.exists():
        return out
    ass = out.with_suffix(".ass")
    subtitles.build([{"id": 1, "texto": texto, "inicio": 0.0, "dur_audio": 3.0}], estilo, ass, override=override)
    run(["ffmpeg", "-y", "-loop", "1", "-t", "2", "-i", cena_exemplo(2), "-vf", f"subtitles={ass.name},scale={PW * 2}:-2",
         "-ss", "1.4", "-frames:v", "1", out.name], cwd=str(PASTA))
    return out


def template(nome: str, titulo: str = "O Último Chefão de Palermo", rotulo: str = "DOCUMENTÁRIO · EP. 01",
             estilo_legenda: str = "Clássica (branca, contorno preto)") -> Path:
    """Mini-vídeo de ~7s: abertura → cena → transição → cena com legenda → encerramento."""
    from . import render, subtitles, templates
    out = _cache("tpl", nome, titulo, rotulo, estilo_legenda)
    if out.exists():
        return out
    tmp = PASTA / f"tpl_{out.stem}"
    tmp.mkdir(parents=True, exist_ok=True)
    a, b = tmp / "a.mp4", tmp / "b.mp4"
    render.render_scene(cena_exemplo(0), 4.0, a, "Zoom in", "Média", 1920, 1080, 24)
    render.render_scene(cena_exemplo(1), 3.5, b, "Pan esquerda→direita", "Média", 1920, 1080, 24)
    v = tmp / "video.mp4"
    run(["ffmpeg", "-y", "-i", a, "-i", b, "-filter_complex", "[0:v][1:v]xfade=transition=fade:duration=0.5:offset=3.5[v]",
         "-map", "[v]", "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-pix_fmt", "yuv420p", v])
    au = tmp / "audio.m4a"
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", "7", "-c:a", "aac", au])
    tpl = templates.preparar(nome, tmp, titulo, rotulo, "Obrigado por assistir", "Inscreva-se no canal") if nome != "Nenhum" else {}
    if tpl:
        tpl.update(previa=True, dur_abertura=2.2, dur_encerramento=1.6)
    ass = tmp / "leg.ass"
    over = templates.legenda_override(nome) if nome != "Nenhum" else None
    subtitles.build([{"id": 1, "texto": "Mas por trás daquele silêncio havia um império", "inicio": 2.4, "dur_audio": 3.0}],
                    estilo_legenda, ass, override=over)
    final = tmp / "final.mp4"
    render.final_mux(v, au, final, ass, 7.0, tpl)
    run(["ffmpeg", "-y", "-i", final, "-vf", f"scale={PW * 2}:-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
         "-an", "-movflags", "+faststart", out])
    return out
