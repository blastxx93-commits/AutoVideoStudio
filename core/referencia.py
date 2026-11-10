"""Referência de edição: analisa um vídeo de exemplo e copia o JEITO de editar (não o conteúdo).

Mede com o FFmpeg: ritmo de cortes, duração dos planos, tipo de transição, quantidade de movimento,
brilho e saturação. Depois a IA olha alguns quadros e reconhece o estilo visual, as legendas,
o tipo de imagem (banco ou IA) e o clima da trilha. O resultado vira configurações do Novo vídeo.

O vídeo do YouTube é baixado em baixa resolução só para a análise e apagado em seguida.
"""
import json
import re
import shutil
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

from .config import (DATA_DIR, MOTIONS, SUBTITLE_STYLES, TRANSITIONS, VISUAL_STYLES, ffmpeg_bin)
from .utils import duration, extract_json, run, CREATE_NO_WINDOW

LIMITE_SEG = 600
LIM_SUAVE, LIM_MEDIA = 0.8, 1.4   # movimento médio por quadro (níveis de cinza), calibrado com o próprio render   # analisa no máximo os 10 primeiros minutos
FPS = 10


# ------------------------------------------------------------------ obter o vídeo
def _yt_dlp(log):
    try:
        import yt_dlp  # noqa
        return yt_dlp
    except ImportError:
        log("Instalando o componente de download (yt-dlp), só na primeira vez...")
        py = Path(sys.executable)
        if py.name.lower() == "pythonw.exe":
            py = py.with_name("python.exe")
        subprocess.run([str(py), "-m", "pip", "install", "-q", "yt-dlp"], capture_output=True,
                       creationflags=CREATE_NO_WINDOW)
        import importlib
        importlib.invalidate_caches()
        import yt_dlp  # noqa
        return yt_dlp


def obter_video(entrada: str, pasta: Path, log=print) -> tuple:
    """Retorna (caminho_do_video, info). Aceita link (YouTube e outros) ou arquivo no PC."""
    entrada = entrada.strip().strip('"')
    p = Path(entrada)
    if p.exists():
        return p, {"titulo": p.stem, "link": ""}
    if not re.match(r"https?://", entrada):
        raise RuntimeError("Cole um link de vídeo ou o caminho de um arquivo de vídeo do seu PC.")
    yt_dlp = _yt_dlp(log)
    log("Baixando uma cópia em baixa resolução só para a análise...")
    opts = {"format": "worst[height>=240][ext=mp4]/worst[ext=mp4]/worst", "outtmpl": str(pasta / "ref.%(ext)s"),
            "quiet": True, "no_warnings": True, "noplaylist": True,
            "ffmpeg_location": str(Path(ffmpeg_bin("ffmpeg")).parent) if Path(ffmpeg_bin("ffmpeg")).exists() else None}
    try:
        opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(0, LIMITE_SEG)])
    except Exception:
        pass
    opts = {k: v for k, v in opts.items() if v is not None}
    try:
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(entrada, download=True)
    except Exception as e:
        raise RuntimeError(f"Não consegui baixar esse vídeo. Se preferir, baixe-o e cole o caminho do arquivo. "
                           f"Detalhe: {str(e)[:200]}")
    arq = next((f for f in pasta.glob("ref.*") if f.suffix in (".mp4", ".webm", ".mkv")), None)
    if not arq:
        raise RuntimeError("O download terminou mas o arquivo não apareceu.")
    return arq, {"titulo": info.get("title", ""), "link": entrada, "canal": info.get("uploader", ""),
                 "duracao_total": info.get("duration")}


# ------------------------------------------------------------------ medições
def _frames(video: Path, seg: float):
    """Quadros pequenos em tons de cinza (64x36) a 10 por segundo, para medir cortes e movimento."""
    import numpy as np
    cmd = [ffmpeg_bin("ffmpeg"), "-hide_banner", "-loglevel", "error", "-t", f"{seg:.1f}", "-i", str(video), "-an",
           "-vf", f"fps={FPS},scale=64:36,format=gray", "-f", "rawvideo", "-"]
    p = subprocess.run(cmd, capture_output=True, creationflags=CREATE_NO_WINDOW)
    a = np.frombuffer(p.stdout, dtype=np.uint8)
    n = len(a) // (64 * 36)
    return a[: n * 64 * 36].reshape(n, 36, 64).astype(np.float32)


def _cores(video: Path, seg: float) -> dict:
    p = run(["ffmpeg", "-hide_banner", "-t", f"{seg:.1f}", "-i", str(video), "-an",
             "-vf", "fps=1,scale=160:-2,signalstats,metadata=print", "-f", "null", "-"])
    y = [float(x) for x in re.findall(r"signalstats\.YAVG=([\d.]+)", p.stderr)]
    s = [float(x) for x in re.findall(r"signalstats\.SATAVG=([\d.]+)", p.stderr)]
    return {"brilho": round(statistics.mean(y)) if y else None, "saturacao": round(statistics.mean(s)) if s else None}


def _pretos_ffmpeg(video: Path, seg: float) -> int:
    p = run(["ffmpeg", "-hide_banner", "-t", f"{seg:.1f}", "-i", str(video), "-an",
             "-vf", "blackdetect=d=0.12:pix_th=0.10", "-f", "null", "-"])
    return len(re.findall(r"black_start", p.stderr))


def medir(video: Path, log=print) -> dict:
    import numpy as np
    total = duration(video)
    seg = min(total, LIMITE_SEG)
    log(f"Medindo cortes e transições ({seg / 60:.1f} min analisados)...")
    F = _frames(video, seg)
    n = len(F)
    if n < FPS * 3:
        raise RuntimeError("Vídeo curto demais para analisar.")
    d1 = np.zeros(n)
    d1[1:] = np.abs(F[1:] - F[:-1]).mean(axis=(1, 2))           # mudança quadro a quadro
    k = FPS                                                        # 1 segundo
    dk = np.zeros(n)
    dk[k:] = np.abs(F[k:] - F[:-k]).mean(axis=(1, 2))             # mudança em 1 segundo
    bril = F.mean(axis=(1, 2))
    base = float(np.median(dk[k:])) if n > k else 0
    lim = max(14.0, base * 4)
    acima = dk > lim
    eventos = []   # (inicio, fim) em quadros
    i = k
    while i < n:
        if acima[i]:
            j = i
            while j < n and acima[j]:
                j += 1
            eventos.append((i - k, j))
            i = j + k // 2
        else:
            i += 1
    # junta eventos muito próximos (ex.: fade para o preto + fade de volta = uma transição só)
    juntos = []
    for e in eventos:
        if juntos and e[0] - juntos[-1][1] < int(FPS * 1.2) and \
                bril[juntos[-1][0]:e[1] + 1].min() < 12:
            juntos[-1] = (juntos[-1][0], e[1])
        else:
            juntos.append(e)
    eventos = juntos
    mov_base = float(np.median(d1[1:]))
    cortes = dissolves = pretos = 0
    durs, tempos = [], []
    for a_, b_ in eventos:
        trecho = d1[a_ + 1:b_ + 1]
        if not len(trecho):
            continue
        tempos.append((a_ + b_) / 2 / FPS)
        if bril[a_:b_ + 1].min() < 12 and bril[a_:b_ + 1].max() > 30:
            pretos += 1
        elif trecho.max() >= 0.55 * trecho.sum():
            cortes += 1
        else:
            dissolves += 1
            ativos = int((trecho > max(1.0, mov_base * 2.5)).sum())
            if ativos:
                durs.append(ativos / FPS)
    planos = [b_ - a_ for a_, b_ in zip([0.0] + tempos, tempos + [seg]) if b_ - a_ > 0.4]
    plano_med = statistics.median(planos) if planos else seg
    prim = [p for p, a_ in zip(planos, [0.0] + tempos) if a_ < 60]
    cores = _cores(video, seg)
    return {
        "segundos_analisados": round(seg), "duracao_total": round(total),
        "cortes_secos": cortes, "dissolves": dissolves, "fades_preto": pretos,
        "plano_medio": round(plano_med, 1), "plano_medio_1min": round(statistics.median(prim), 1) if prim else None,
        "cortes_por_minuto": round(len(tempos) / (seg / 60), 1) if seg else 0,
        "duracao_dissolve": round(statistics.median(durs), 2) if durs else None,
        "movimento": round(mov_base, 2), **cores,
    }


def quadros(video: Path, pasta: Path, seg: float, n: int = 8) -> list:
    """Extrai quadros espalhados (2 do primeiro minuto) para a IA olhar."""
    seg = min(seg, LIMITE_SEG)
    tempos = [min(8, seg * 0.05), min(35, seg * 0.15)] + [seg * (k + 1) / (n - 1) for k in range(n - 2)]
    out = []
    for k, t in enumerate(tempos):
        f = pasta / f"q{k:02d}.jpg"
        try:
            run(["ffmpeg", "-y", "-hide_banner", "-ss", f"{max(0, t - 0.5):.2f}", "-i", str(video), "-frames:v", "1",
                 "-vf", "scale=768:-2", "-q:v", "4", str(f)])
            if f.exists():
                out.append(f)
        except Exception:
            pass
    return out


# ------------------------------------------------------------------ IA de visão
def olhar_com_ia(imgs: list, info: dict, log=print) -> dict:
    from .llm import chat, llm_available
    from .templates import TEMPLATES
    from .trilha import TEMAS
    if not imgs or not llm_available():
        return {}
    log("A IA está olhando os quadros do vídeo...")
    p = (
        "These are frames sampled from a YouTube video (first two are from the first minute). "
        f'Title: "{info.get("titulo", "")}".\n'
        "Describe HOW it is edited so another video can copy the editing style (not the content). "
        "Reply ONLY with JSON:\n"
        "{\n"
        f' "estilo_visual": one of {json.dumps(list(VISUAL_STYLES), ensure_ascii=False)} or "Outro",\n'
        ' "estilo_descricao": "if Outro, an English image-generation style description (medium, palette, light, texture); else empty",\n'
        ' "origem_imagens": "banco" (real stock photos/footage) | "ia" (AI images/illustrations) | "misto",\n'
        ' "pct_banco": 0-100 estimated share of real stock footage/photos,\n'
        ' "legendas": true/false (burned-in subtitles visible),\n'
        f' "estilo_legenda": closest of {json.dumps(list(SUBTITLE_STYLES), ensure_ascii=False)},\n'
        f' "template": closest look of {json.dumps(list(TEMPLATES), ensure_ascii=False)} ("Nenhum" if plain full-screen images),\n'
        f' "trilha_tema": most likely music mood among {json.dumps(list(TEMAS), ensure_ascii=False)},\n'
        ' "personagem_fixo": "English description of a recurring main character if the same one appears in several frames, else empty",\n'
        ' "direcao_cenas": "one English sentence on framing/composition habits to copy (e.g. close-ups, maps, archive photos)",\n'
        ' "observacoes": ["3 to 6 short notes in Brazilian Portuguese about the editing: text on screen, color, pace, overlays"]\n'
        "}"
    )
    try:
        r = extract_json(chat(p, images=[str(i) for i in imgs], max_tokens=1500))
        return r if isinstance(r, dict) else {}
    except Exception as e:
        log(f"A IA não conseguiu analisar os quadros ({str(e)[:120]}). Sigo só com as medições.")
        return {}


def ritmo_fala(link: str, dur: float) -> int:
    """Palavras por minuto da narração (pela transcrição pública), se houver."""
    if not link or "youtu" not in link or not dur:
        return 0
    try:
        from .adaptar import transcricao
        texto = transcricao(link).get("texto", "")
        if texto:
            return int(len(texto.split()) / (dur / 60))
    except Exception:
        pass
    return 0


# ------------------------------------------------------------------ transformar em configurações
def sugerir(m: dict, ia: dict, wpm: int = 0) -> list:
    """Lista de (campo, valor, explicação) para aplicar no Novo vídeo."""
    s = []
    plano = m["plano_medio"]
    s.append(("segundos_por_cena", int(max(3, min(15, round(plano)))),
              f"Planos de ~{plano}s ({m['cortes_por_minuto']} trocas por minuto)"
              + (f"; no 1º minuto ~{m['plano_medio_1min']}s" if m.get("plano_medio_1min") else "")))
    tot = m["cortes_secos"] + m["dissolves"] + m["fades_preto"]
    if tot:
        if m["fades_preto"] >= max(3, 0.25 * tot):
            tr, why = "Fade pelo preto", f"{m['fades_preto']} passagens pelo preto"
        elif m["dissolves"] >= 0.35 * tot:
            tr, why = "Fade (dissolver)", f"{m['dissolves']} dissolves de {tot} trocas"
        else:
            tr, why = "Corte seco (sem transição)", f"{m['cortes_secos']} cortes secos de {tot} trocas"
        s.append(("transicao", tr, why))
        if tr != "Corte seco (sem transição)" and m.get("duracao_dissolve"):
            s.append(("duracao_transicao", round(max(0.2, min(1.5, m["duracao_dissolve"])), 1),
                      f"Transições de ~{m['duracao_dissolve']}s"))
    mv = m["movimento"]
    if mv < 0.15:
        s.append(("movimento", "Estático", "Imagens quase paradas"))
    else:
        s.append(("movimento", "Aleatório", "Imagens com zoom/pan"))
        s.append(("intensidade_movimento", "Suave" if mv < LIM_SUAVE else ("Média" if mv < LIM_MEDIA else "Forte"),
                  f"Quantidade de movimento medida: {mv}"))
    if ia:
        ev = ia.get("estilo_visual")
        if ev in VISUAL_STYLES and ev != "Personalizado":
            s.append(("estilo_visual", ev, "Estilo visual reconhecido nos quadros"))
        elif ia.get("estilo_descricao"):
            s.append(("estilo_visual", "Personalizado", "Estilo próprio (descrito pela IA)"))
            s.append(("estilo_personalizado", ia["estilo_descricao"], "Receita do estilo"))
        if isinstance(ia.get("pct_banco"), (int, float)):
            s.append(("pct_banco", int(round(ia["pct_banco"] / 10) * 10), f"Imagens: {ia.get('origem_imagens', '?')}"))
        if isinstance(ia.get("legendas"), bool):
            s.append(("legendas", ia["legendas"], "Legenda na tela" if ia["legendas"] else "Sem legenda na tela"))
            if ia["legendas"] and ia.get("estilo_legenda") in SUBTITLE_STYLES:
                s.append(("estilo_legenda", ia["estilo_legenda"], "Estilo de legenda mais parecido"))
        from .templates import TEMPLATES
        if ia.get("template") in TEMPLATES:
            s.append(("template", ia["template"], "Visual de tela mais parecido"))
        from .trilha import TEMAS
        if ia.get("trilha_tema") in TEMAS:
            s.append(("trilha_modo", "Tema", "Trilha pelo clima do vídeo"))
            s.append(("trilha_tema", ia["trilha_tema"], "Clima da música"))
        if ia.get("personagem_fixo"):
            s.append(("personagem_fixo", ia["personagem_fixo"], "Personagem que se repete"))
        if ia.get("direcao_cenas"):
            s.append(("ref_direcao", ia["direcao_cenas"], "Jeito de enquadrar as cenas"))
    if wpm:
        vel = round(max(0.85, min(1.2, wpm / 150)) * 20) / 20
        s.append(("velocidade_voz", vel, f"Narração com ~{wpm} palavras por minuto"))
    return s


def analisar(entrada: str, log=print) -> dict:
    pasta = Path(tempfile.mkdtemp(prefix="avref_"))
    try:
        video, info = obter_video(entrada, pasta, log)
        m = medir(video, log)
        imgs = quadros(video, pasta, m["segundos_analisados"])
        ia = olhar_com_ia(imgs, info, log)
        wpm = ritmo_fala(info.get("link", ""), info.get("duracao_total") or 0)
        sug = sugerir(m, ia, wpm)
        # guarda os quadros (pequenos) para mostrar na tela
        destino = DATA_DIR / "referencias" / re.sub(r"\W+", "_", (info.get("titulo") or "ref"))[:50]
        destino.mkdir(parents=True, exist_ok=True)
        salvos = []
        for f in imgs:
            alvo = destino / f.name
            shutil.copy(f, alvo)
            salvos.append(str(alvo))
        res = {"info": info, "medidas": m, "ia": ia, "wpm": wpm, "sugestoes": sug, "quadros": salvos}
        (destino / "analise.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
        log("Análise pronta.")
        return res
    finally:
        shutil.rmtree(pasta, ignore_errors=True)
