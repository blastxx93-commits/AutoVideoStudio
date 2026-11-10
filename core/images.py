"""Imagens: geradores por IA, bancos de imagens/clipes (Pexels, Pixabay) e pasta local."""
import base64
import random
import re
import time
import urllib.parse
from pathlib import Path

from PIL import Image

from .config import load_settings, VISUAL_STYLES, NEGATIVE_HINT, WIDTH, HEIGHT
from .utils import http, download

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def full_prompt(prompt: str, job: dict) -> str:
    st = job.get("estilo_visual", "")
    style = job.get("estilo_personalizado", "") if st == "Personalizado" else VISUAL_STYLES.get(st, "")
    if not style:
        return f"{prompt}, {NEGATIVE_HINT}".strip(", ")
    # O estilo vai no começo (os geradores dão mais peso ao início) e completo no fim,
    # para que TODAS as imagens saiam no estilo escolhido, mesmo se o prompt da cena puxar para outro lado.
    cabeca = ", ".join(style.split(", ")[:2])
    return f"{cabeca}: {prompt.strip().rstrip('.')}. Art style: {style}. {NEGATIVE_HINT}"


def _save_b64(b64: str, dest: Path) -> Path:
    dest.write_bytes(base64.b64decode(b64))
    return dest


def _normalize(path: Path) -> Path:
    """Converte qualquer imagem para JPG RGB."""
    im = Image.open(path).convert("RGB")
    out = path.with_suffix(".jpg")
    im.save(out, quality=93)
    if out != path:
        path.unlink(missing_ok=True)
    return out


def generate_ai(provider: str, prompt: str, dest: Path, w=WIDTH, h=HEIGHT, seed=None) -> Path:
    s = load_settings()
    dest = dest.with_suffix(".png")
    seed = seed if seed is not None else random.randint(1, 10**8)
    if provider.startswith("Pollinations"):
        url = (f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt[:1500])}"
               f"?width={w}&height={h}&seed={seed}&nologo=true&model=flux")
        download(url, dest)
    elif provider.startswith("Replicate"):
        r = http("POST", f"https://api.replicate.com/v1/models/{s['replicate_model']}/predictions",
                 headers={"Authorization": f"Bearer {s['replicate_key']}", "Prefer": "wait"},
                 json={"input": {"prompt": prompt, "aspect_ratio": "16:9" if w > h else "9:16",
                                 "output_format": "png", "seed": seed}})
        data = r.json()
        while data.get("status") in ("starting", "processing"):
            time.sleep(2)
            data = http("GET", data["urls"]["get"], headers={"Authorization": f"Bearer {s['replicate_key']}"}).json()
        out = data.get("output")
        if not out:
            raise RuntimeError(f"Replicate não gerou imagem: {data.get('error')}")
        download(out[0] if isinstance(out, list) else out, dest)
    elif provider.startswith("fal.ai"):
        r = http("POST", f"https://fal.run/{s['fal_model']}", headers={"Authorization": f"Key {s['fal_key']}"},
                 json={"prompt": prompt, "image_size": "landscape_16_9" if w > h else "portrait_16_9", "seed": seed})
        download(r.json()["images"][0]["url"], dest)
    elif provider.startswith("Together"):
        r = http("POST", "https://api.together.xyz/v1/images/generations",
                 headers={"Authorization": f"Bearer {s['together_key']}"},
                 json={"model": s["together_model"], "prompt": prompt, "width": 1344 if w > h else 768,
                       "height": 768 if w > h else 1344, "n": 1, "seed": seed, "response_format": "b64_json"})
        _save_b64(r.json()["data"][0]["b64_json"], dest)
    elif provider.startswith("Black Forest"):
        r = http("POST", f"https://api.bfl.ai/v1/{s['bfl_model']}", headers={"x-key": s["bfl_key"]},
                 json={"prompt": prompt, "width": 1344 if w > h else 768, "height": 768 if w > h else 1344, "seed": seed})
        poll = r.json()["polling_url"]
        for _ in range(120):
            time.sleep(1.5)
            d = http("GET", poll, headers={"x-key": s["bfl_key"]}).json()
            if d.get("status") == "Ready":
                download(d["result"]["sample"], dest)
                break
            if d.get("status") in ("Error", "Failed", "Content Moderated", "Request Moderated"):
                raise RuntimeError(f"BFL: {d.get('status')}")
        else:
            raise RuntimeError("BFL demorou demais.")
    elif provider.startswith("OpenAI") or provider.startswith("ChatGPT"):
        r = http("POST", "https://api.openai.com/v1/images/generations",
                 headers={"Authorization": f"Bearer {s['openai_images_key']}"},
                 json={"model": s["openai_images_model"], "prompt": prompt,
                       "size": "1536x1024" if w > h else "1024x1536", "n": 1,
                       "quality": s.get("openai_images_quality", "medium")}, timeout=300)
        d = r.json()["data"][0]
        _save_b64(d["b64_json"], dest) if d.get("b64_json") else download(d["url"], dest)
    elif provider.startswith("Google Imagen"):
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/{s['imagen_model']}:predict"
               f"?key={s['gemini_key']}")
        r = http("POST", url, json={"instances": [{"prompt": prompt}],
                                    "parameters": {"sampleCount": 1, "aspectRatio": "16:9" if w > h else "9:16"}})
        _save_b64(r.json()["predictions"][0]["bytesBase64Encoded"], dest)
    elif provider.startswith("Gerador personalizado"):
        base = s["custom_img_base"].rstrip("/")
        if not base:
            raise RuntimeError("Configure a URL do gerador personalizado.")
        r = http("POST", base + "/images/generations", headers={"Authorization": f"Bearer {s['custom_img_key']}"},
                 json={"model": s["custom_img_model"], "prompt": prompt, "size": f"{w}x{h}", "n": 1,
                       "response_format": "b64_json"}, timeout=300)
        d = r.json()["data"][0]
        _save_b64(d["b64_json"], dest) if d.get("b64_json") else download(d["url"], dest)
    else:
        raise RuntimeError(f"Gerador desconhecido: {provider}")
    return _normalize(dest)


# ------------------------------------------------------------------ bancos
class StockPicker:
    """Busca clipes/fotos e evita repetir o mesmo arquivo no vídeo."""

    def __init__(self, job: dict):
        self.job = job
        self.s = load_settings()
        self.used = set()
        self.local_files = []
        folder = job.get("pasta_midia_local", "").strip().strip('"')
        if "Pasta do meu PC" in job.get("banco_fontes", []) and folder and Path(folder).is_dir():
            self.local_files = [p for p in Path(folder).rglob("*") if p.suffix.lower() in VIDEO_EXT | IMAGE_EXT]

    def _want(self):
        t = self.job.get("banco_tipo", "Misto")
        if t.startswith("Clipes"):
            return ["video"]
        if t.startswith("Fotos"):
            return ["photo"]
        return ["video", "photo"] if random.random() < 0.7 else ["photo", "video"]

    def _pexels(self, q, kind):
        if not self.s["pexels_key"]:
            return []
        h = {"Authorization": self.s["pexels_key"]}
        if kind == "video":
            r = http("GET", "https://api.pexels.com/videos/search", headers=h,
                     params={"query": q, "orientation": "landscape", "per_page": 20, "size": "medium"})
            res = []
            for v in r.json().get("videos", []):
                files = [f for f in v.get("video_files", []) if (f.get("width") or 0) >= 1280 and f.get("link")]
                if files:
                    f = min(files, key=lambda f: abs((f.get("width") or 0) - 1920))
                    res.append((f"pexels_v{v['id']}", f["link"], "video"))
            return res
        r = http("GET", "https://api.pexels.com/v1/search", headers=h,
                 params={"query": q, "orientation": "landscape", "per_page": 20})
        return [(f"pexels_p{p['id']}", p["src"].get("large2x") or p["src"]["original"], "photo")
                for p in r.json().get("photos", [])]

    def _pixabay(self, q, kind):
        if not self.s["pixabay_key"]:
            return []
        if kind == "video":
            r = http("GET", "https://pixabay.com/api/videos/",
                     params={"key": self.s["pixabay_key"], "q": q[:100], "per_page": 20, "safesearch": "true"})
            res = []
            for v in r.json().get("hits", []):
                vids = v.get("videos", {})
                best = vids.get("large") if vids.get("large", {}).get("url") else vids.get("medium")
                if best and best.get("url") and (best.get("width") or 0) >= 1280:
                    res.append((f"pixabay_v{v['id']}", best["url"], "video"))
            return res
        r = http("GET", "https://pixabay.com/api/", params={"key": self.s["pixabay_key"], "q": q[:100],
                                                             "image_type": "photo", "orientation": "horizontal",
                                                             "per_page": 20, "safesearch": "true"})
        return [(f"pixabay_p{h['id']}", h.get("largeImageURL"), "photo") for h in r.json().get("hits", [])]

    def _local(self, q):
        words = set(re.findall(r"\w{3,}", q.lower()))
        free = [p for p in self.local_files if str(p) not in self.used]
        if not free:
            return []
        scored = sorted(free, key=lambda p: -len(words & set(re.findall(r"\w{3,}", p.stem.lower()))))
        top = scored[0]
        return [(str(top), str(top), "video" if top.suffix.lower() in VIDEO_EXT else "photo")]

    def pick(self, query: str, dest_base: Path, exclude=()) -> Path:
        fontes = self.job.get("banco_fontes", ["Pexels"])
        queries = [query, " ".join(query.split()[:2]), query.split()[0] if query.split() else "landscape"]
        for q in queries:
            for kind in self._want():
                cands = []
                for f in fontes:
                    try:
                        if f == "Pexels":
                            cands += self._pexels(q, kind)
                        elif f == "Pixabay":
                            cands += self._pixabay(q, kind)
                    except Exception as e:
                        print(f"  aviso {f}: {e}")
                if "Pasta do meu PC" in fontes:
                    cands = self._local(q) + cands
                cands = [c for c in cands if c[0] not in self.used and c[0] not in exclude]
                if not cands:
                    continue
                key, url, k = random.choice(cands[:6])
                self.used.add(key)
                self.last_key = key
                if Path(url).exists():  # arquivo local
                    ext = Path(url).suffix.lower()
                    dest = dest_base.with_suffix(ext)
                    dest.write_bytes(Path(url).read_bytes())
                else:
                    dest = dest_base.with_suffix(".mp4" if k == "video" else ".jpg")
                    download(url, dest)
                    if k == "photo":
                        dest = _normalize(dest)
                return dest
        raise RuntimeError(f"Nada encontrado no banco para: {query}")
