"""Abrir projeto: ver e editar, cena por cena, as imagens e clipes de um vídeo."""
import json
import random
import re
import time
from pathlib import Path

from .images import VIDEO_EXT, IMAGE_EXT

MIDIA_EXT = VIDEO_EXT | IMAGE_EXT


def _ler(job_dir: Path):
    job = json.loads((job_dir / "trabalho.json").read_text(encoding="utf-8"))
    cf = job_dir / "cenas.json"
    scenes = json.loads(cf.read_text(encoding="utf-8")) if cf.exists() else []
    return job, scenes


def _salvar_cenas(job_dir: Path, scenes: list):
    (job_dir / "cenas.json").write_text(json.dumps(scenes, ensure_ascii=False, indent=1), encoding="utf-8")


def carregar(job_dir) -> dict:
    """Junta texto, mídia já gerada (mesmo durante a geração), fonte, tempo e problemas de cada cena."""
    job_dir = Path(job_dir)
    job, scenes = _ler(job_dir)
    problemas = {}
    rel = job_dir / "relatorio.json"
    if rel.exists():
        for linha in json.loads(rel.read_text(encoding="utf-8")):
            m = re.match(r"(?:Áudio )?[Cc]ena (\d+): (.*)", linha)
            if m:
                problemas[int(m.group(1))] = [m.group(2)]  # mostra só o resultado mais recente
    pasta = job_dir / "midia"
    out = []
    for sc in scenes:
        midia = sc.get("midia")
        if not midia or not Path(midia).exists():  # durante a geração o cenas.json ainda não tem a mídia
            achados = sorted(pasta.glob(f"c{sc['id']:04d}.*")) if pasta.exists() else []
            achados = [a for a in achados if a.suffix.lower() in MIDIA_EXT]
            midia = str(achados[0]) if achados else None
        out.append({**sc, "midia": midia, "problemas": problemas.get(sc["id"], []),
                    "eh_video": bool(midia) and Path(midia).suffix.lower() in VIDEO_EXT})
    prontas = sum(1 for x in out if x["midia"])
    return {"job": job, "cenas": out, "prontas": prontas, "total": len(out)}


def _trocar_arquivo(job_dir: Path, sc: dict, novo: Path, scenes: list, manual: bool):
    antigo = sc.get("midia")
    if antigo and Path(antigo).exists() and Path(antigo) != novo:
        Path(antigo).unlink(missing_ok=True)
    sc["midia"] = str(novo)
    sc["manual"] = manual
    _salvar_cenas(job_dir, scenes)


def regenerar(job_dir, sid: int, prompt: str = None, fonte: str = None) -> Path:
    """Gera outra imagem (IA, com prompt opcional editado) ou busca outro clipe/foto no banco."""
    from . import images
    job_dir = Path(job_dir)
    job, scenes = _ler(job_dir)
    sc = next(x for x in scenes if x["id"] == sid)
    fonte = fonte or sc.get("fonte", "ia")
    base = job_dir / "midia" / f"c{sid:04d}_{int(time.time())}"
    if fonte == "banco":
        picker = images.StockPicker(job)
        picker.used = {x.get("banco_id") for x in scenes if x.get("banco_id")}
        novo = picker.pick(sc.get("search_query") or job["titulo"], base, exclude={sc.get("banco_id")})
        sc["banco_id"] = getattr(picker, "last_key", "")
    else:
        if prompt:
            sc["image_prompt"] = prompt
        novo = images.generate_ai(job["img_provider"], images.full_prompt(sc.get("image_prompt") or sc["texto"], job),
                                  base, seed=random.randint(1, 10**8))
    sc["fonte"] = fonte
    _trocar_arquivo(job_dir, sc, Path(novo), scenes, manual=True)
    return Path(novo)


def substituir(job_dir, sid: int, nome: str, dados: bytes) -> Path:
    """Troca a mídia da cena por um arquivo seu (imagem ou vídeo)."""
    job_dir = Path(job_dir)
    _, scenes = _ler(job_dir)
    sc = next(x for x in scenes if x["id"] == sid)
    ext = Path(nome).suffix.lower()
    if ext not in MIDIA_EXT:
        raise ValueError("Formato não suportado. Use JPG, PNG, WEBP, MP4, MOV, MKV ou WEBM.")
    novo = job_dir / "midia" / f"c{sid:04d}_{int(time.time())}{ext}"
    novo.write_bytes(dados)
    sc["fonte"] = "meu arquivo"
    _trocar_arquivo(job_dir, sc, novo, scenes, manual=True)
    return novo


def editado_depois_do_video(job_dir) -> bool:
    """True se alguma cena foi trocada depois do último vídeo montado."""
    job_dir = Path(job_dir)
    final = job_dir / "video_final.mp4"
    if not final.exists():
        return False
    t = final.stat().st_mtime
    _, scenes = _ler(job_dir)
    return any(sc.get("midia") and Path(sc["midia"]).exists() and Path(sc["midia"]).stat().st_mtime > t for sc in scenes)
