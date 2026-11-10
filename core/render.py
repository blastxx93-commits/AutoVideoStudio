"""Montagem com FFmpeg: movimento nas imagens, transições, efeitos sonoros, música, legendas."""
import random
from pathlib import Path

from .config import WIDTH, HEIGHT, FPS, SFX_DIR, TRANSITIONS, RANDOM_POOL, MUSIC_DIR
from .images import VIDEO_EXT
from .utils import run, duration

ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "19", "-pix_fmt", "yuv420p", "-r", str(FPS)]
INTENSITY = {"Suave": 0.08, "Média": 0.15, "Forte": 0.25}


def render_scene(media: Path, seconds: float, out: Path, motion: str, intensity: str = "Média",
                 w: int = WIDTH, h: int = HEIGHT, fps: int = FPS) -> Path:
    """Gera o trecho de vídeo (sem áudio) de uma cena. w/h/fps menores servem para as prévias."""
    n = max(1, int(round(seconds * fps)))
    enc = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "19" if w >= 1280 else "26", "-pix_fmt", "yuv420p",
           "-r", str(fps)]
    if media.suffix.lower() in VIDEO_EXT:
        vf = (f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},"
              f"fps={fps},setsar=1,format=yuv420p")
        run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", media, "-t", f"{seconds:.3f}", "-vf", vf, "-an",
             "-frames:v", n, *enc, out])
        return out

    if motion == "Aleatório":
        motion = random.choice(["Zoom in", "Zoom out", "Pan esquerda→direita", "Pan direita→esquerda", "Zoom in"])
    a = INTENSITY.get(intensity, 0.15)
    big_w, big_h = w * 3, h * 3
    pre = f"scale={big_w}:{big_h}:force_original_aspect_ratio=increase,crop={big_w}:{big_h},setsar=1"
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if motion == "Zoom in":
        z, x, y = f"1+{a}*on/{n}", cx, cy
    elif motion == "Zoom out":
        z, x, y = f"{1 + a}-{a}*on/{n}", cx, cy
    elif motion == "Pan esquerda→direita":
        z, x, y = f"{1 + a}", f"(iw-iw/zoom)*on/{n}", cy
    elif motion == "Pan direita→esquerda":
        z, x, y = f"{1 + a}", f"(iw-iw/zoom)*(1-on/{n})", cy
    elif motion == "Pan cima→baixo":
        z, x, y = f"{1 + a}", cx, f"(ih-ih/zoom)*on/{n}"
    else:  # Estático
        vf = f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},setsar=1,format=yuv420p"
        run(["ffmpeg", "-y", "-loop", "1", "-framerate", fps, "-i", media, "-t", f"{seconds:.3f}", "-vf", vf,
             "-frames:v", n, *enc, out])
        return out
    vf = f"{pre},zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={w}x{h}:fps={fps},format=yuv420p"
    run(["ffmpeg", "-y", "-i", media, "-vf", vf, "-frames:v", n, *enc, out])
    return out


def transitions_for(n_bound: int, choice: str) -> list:
    name = TRANSITIONS.get(choice)
    if name is None:
        return [None] * n_bound
    if name == "random":
        return [random.choice(RANDOM_POOL) for _ in range(n_bound)]
    return [name] * n_bound


def _concat_copy(paths, out: Path):
    lst = out.with_suffix(".txt")
    lst.write_text("".join(f"file '{Path(p).resolve().as_posix()}'\n" for p in paths), encoding="utf-8")
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out])
    return out


def merge(items: list, T: float, out: Path, chunk=12, log=print) -> Path:
    """items = [(arquivo, duração_da_narração, transição_depois_ou_None)].
    Transições CENTRADAS na troca de narração: cada trecho tem T/2 extra antes (menos o 1º) e T/2 depois (menos o último),
    então a imagem nova fica 100% visível exatamente meia transição depois de a frase dela começar."""
    if all(t is None for _, _, t in items[:-1]) or T <= 0:
        return _concat_copy([p for p, _, _ in items], out)
    # (arquivo, conteúdo, transição, tem_pre)
    items = [(p, c, t, i > 0) for i, (p, c, t) in enumerate(items)]
    level = 0
    while len(items) > 1:
        groups = [items[i:i + chunk] for i in range(0, len(items), chunk)]
        new_items = []
        for gi, g in enumerate(groups):
            gout = out.parent / f"_merge_{level}_{gi}.mp4"
            if len(g) == 1:
                new_items.append(g[0])
                continue
            cmd = ["ffmpeg", "-y"]
            for p, *_ in g:
                cmd += ["-i", p]
            parts, prev, acc = [], "[0:v]", (T / 2 if g[0][3] else 0.0)
            for k in range(len(g) - 1):
                acc += g[k][1]
                tr = g[k][2] or "fade"
                lab = f"[v{k + 1}]"
                parts.append(f"{prev}[{k + 1}:v]xfade=transition={tr}:duration={T}:offset={acc - T / 2:.3f}{lab}")
                prev = lab
            cmd += ["-filter_complex", ";".join(parts), "-map", prev, *ENC, gout]
            run(cmd)
            new_items.append((gout, sum(x[1] for x in g), g[-1][2], g[0][3]))
        log(f"  juntando trechos: nível {level + 1} ({len(items)} → {len(new_items)})")
        items, level = new_items, level + 1
    Path(items[0][0]).replace(out)
    return out


# ------------------------------------------------------------- áudio
def ensure_default_sfx():
    if any(p.suffix.lower() in (".wav", ".mp3", ".ogg") for p in SFX_DIR.iterdir()):
        return
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=d=0.8:c=pink:a=0.7", "-af",
         "highpass=f=250,lowpass=f=2800,afade=t=in:d=0.4:curve=qsin,afade=t=out:st=0.4:d=0.4:curve=qsin,volume=0.9",
         "-ar", "48000", "-ac", "2", SFX_DIR / "whoosh_padrao.wav"])
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", "anoisesrc=d=0.6:c=brown:a=0.8", "-af",
         "lowpass=f=1200,afade=t=in:d=0.3,afade=t=out:st=0.3:d=0.3,volume=1.2",
         "-ar", "48000", "-ac", "2", SFX_DIR / "whoosh_grave.wav"])


def concat_audio(wavs: list, out: Path) -> Path:
    return _concat_copy(wavs, out) if out.suffix == ".wav" else None


def music_files(path_str: str) -> list:
    p = Path(path_str.strip().strip('"')) if path_str else MUSIC_DIR
    if p.is_file():
        return [p]
    if p.is_dir():
        fs = [f for f in p.iterdir() if f.suffix.lower() in (".mp3", ".wav", ".m4a", ".ogg", ".flac")]
        random.shuffle(fs)
        return fs
    return []


def mix_audio(narration: Path, total: float, out: Path, job: dict, sfx_times: list, musics: list = None) -> Path:
    cmd = ["ffmpeg", "-y", "-i", narration]
    filt, mix = [], ["[nar]"]
    filt.append("[0:a]aresample=48000,asplit=2[nar][key]")
    idx = 1
    if musics is None:  # compatibilidade: arquivo/pasta em job["musica"]
        musics = music_files(job.get("musica", "")) if job.get("musica") else []
    if musics:
        vol = float(job.get("volume_musica", 0.12))
        labs = []
        for k, m in enumerate(musics):
            d = max(3.0, duration(m))
            cmd += ["-i", m]
            fo = min(2.5, d / 4)
            filt.append(f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo:sample_fmts=fltp,"
                        f"afade=t=in:d={min(1.5, d / 4):.2f},afade=t=out:st={d - fo:.2f}:d={fo:.2f}[m{k}]")
            labs.append(f"[m{k}]")
            idx += 1
        filt.append("".join(labs) + f"concat=n={len(labs)}:v=0:a=1,apad,atrim=0:{total:.3f},"
                    f"volume={vol},afade=t=in:d=1.5,afade=t=out:st={max(0, total - 3):.3f}:d=3[mus0]")
        filt.append("[mus0][key]sidechaincompress=threshold=0.04:ratio=6:attack=30:release=500[mus]")
        mix.append("[mus]")
    else:
        filt.append("[key]anullsink")
    sfx_files = [f for f in SFX_DIR.iterdir() if f.suffix.lower() in (".wav", ".mp3", ".ogg")] \
        if job.get("efeitos_sonoros") else []
    if sfx_times and sfx_files:
        vol = float(job.get("volume_sfx", 0.35))
        chosen = [random.choice(sfx_files) for _ in sfx_times]
        uniq = sorted(set(chosen))
        for f in uniq:
            cmd += ["-i", f]
        counts = {f: chosen.count(f) for f in uniq}
        labels = {}
        for j, f in enumerate(uniq):
            n = counts[f]
            outs = "".join(f"[s{j}_{k}]" for k in range(n))
            filt.append(f"[{idx + j}:a]aresample=48000,aformat=channel_layouts=stereo,volume={vol},asplit={n}{outs}")
            labels[f] = [f"[s{j}_{k}]" for k in range(n)]
        delayed = []
        for t, f in zip(sfx_times, chosen):
            lab = labels[f].pop()
            ms = max(0, int((t - 0.2) * 1000))
            dl = f"[d{len(delayed)}]"
            filt.append(f"{lab}adelay={ms}|{ms}{dl}")
            delayed.append(dl)
        filt.append("".join(delayed) + f"amix=inputs={len(delayed)}:normalize=0:dropout_transition=0[sfx]")
        mix.append("[sfx]")
    filt.append("".join(mix) + f"amix=inputs={len(mix)}:normalize=0:duration=first,"
                f"alimiter=limit=0.95,atrim=0:{total:.3f}[out]")
    cmd += ["-filter_complex", ";".join(filt), "-map", "[out]", "-c:a", "aac", "-b:a", "192k", out]
    run(cmd)
    return out


def final_mux(video: Path, audio: Path, out: Path, subs_ass: Path = None, total: float = None, tpl: dict = None,
              size: tuple = (WIDTH, HEIGHT)):
    """Junta vídeo + áudio aplicando: cor do template, moldura, legenda, abertura, encerramento e fades."""
    tpl = tpl or {}
    cmd = ["ffmpeg", "-y", "-i", video.name, "-i", audio.name]
    fc, cur, idx = [], "[0:v]", 2
    if tpl.get("cor"):
        fc.append(f"{cur}{tpl['cor']}[vc]")
        cur = "[vc]"
    if tpl.get("moldura"):
        cmd += ["-loop", "1", "-t", f"{(total or 1) + 1:.2f}", "-i", str(Path(tpl["moldura"]).resolve())]
        fc.append(f"[{idx}:v]scale={size[0]}:{size[1]}[mo]")
        fc.append(f"{cur}[mo]overlay=0:0:shortest=1[vm]")
        cur, idx = "[vm]", idx + 1
    if subs_ass:
        fc.append(f"{cur}subtitles={subs_ass.name}[vs]")
        cur = "[vs]"
    previa = tpl.get("previa", False)
    if tpl.get("abertura") and total and (total > 12 or previa):
        da = float(tpl.get("dur_abertura", 4.0))
        cmd += ["-loop", "1", "-t", f"{da:.2f}", "-i", str(Path(tpl["abertura"]).resolve())]
        fc.append(f"[{idx}:v]scale={size[0]}:{size[1]},format=rgba,fade=t=out:st={da - 0.7:.2f}:d=0.7:alpha=1[ab]")
        fc.append(f"{cur}[ab]overlay=0:0:eof_action=pass[va]")
        cur, idx = "[va]", idx + 1
    if tpl.get("encerramento") and total and (total > 20 or previa):
        de = float(tpl.get("dur_encerramento") or min(5.0, total * 0.15))
        st0 = max(0.0, total - de)
        cmd += ["-loop", "1", "-t", f"{de:.2f}", "-i", str(Path(tpl["encerramento"]).resolve())]
        fc.append(f"[{idx}:v]scale={size[0]}:{size[1]},format=rgba,fade=t=in:st=0:d=0.7:alpha=1,setpts=PTS+{st0:.3f}/TB[en]")
        fc.append(f"{cur}[en]overlay=0:0:eof_action=pass[ve]")
        cur, idx = "[ve]", idx + 1
    if total:
        fc.append(f"{cur}fade=t=in:st=0:d=0.6,fade=t=out:st={max(0, total - 1.0):.3f}:d=1.0,format=yuv420p[vout]")
        cur = "[vout]"
    if fc:
        cmd += ["-filter_complex", ";".join(fc), "-map", cur, "-map", "1:a",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p"]
    else:
        cmd += ["-map", "0:v", "-map", "1:a", "-c:v", "copy"]
    cmd += ["-c:a", "copy", "-shortest", "-movflags", "+faststart", str(out.resolve())]
    run(cmd, cwd=str(video.parent))
    return out
