"""'Cérebro' do programa: divide o roteiro em cenas e cria prompts de imagem / busca."""
import base64
import re
from pathlib import Path

from .config import load_settings, VISUAL_STYLES
from .utils import http, extract_json


def llm_available(s=None) -> bool:
    s = s or load_settings()
    p = s.get("llm_provider", "nenhum")
    return (p == "anthropic" and s["anthropic_key"]) or (p == "openai_compat" and s["openai_compat_base"]) \
        or (p == "gemini" and s["gemini_key"])


def chat(prompt: str, system: str = "", images: list = None, max_tokens=4000, model: str = None,
         web_search: int = 0, timeout: int = 180) -> str:
    """Envia um prompt (e imagens opcionais, para revisão visual) ao provedor configurado."""
    s = load_settings()
    p = s.get("llm_provider", "nenhum")
    images = images or []
    if p == "anthropic":
        content = []
        for img in images:
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                         "data": base64.b64encode(Path(img).read_bytes()).decode()}})
        content.append({"type": "text", "text": prompt})
        msgs = [{"role": "user", "content": content}]
        body = {"model": model or s["anthropic_model"], "max_tokens": max_tokens, "messages": msgs}
        if system:
            body["system"] = system
        if web_search:
            body["tools"] = [{"type": "web_search_20250305", "name": "web_search", "max_uses": int(web_search)}]
        textos = []
        for _ in range(4):  # "pause_turn": a busca na web pode pedir para continuar
            r = http("POST", "https://api.anthropic.com/v1/messages", json=body, timeout=timeout,
                     headers={"x-api-key": s["anthropic_key"], "anthropic-version": "2023-06-01",
                              "content-type": "application/json"})
            d = r.json()
            textos.append("".join(b.get("text", "") for b in d["content"] if b.get("type") == "text"))
            if d.get("stop_reason") != "pause_turn":
                break
            msgs.append({"role": "assistant", "content": d["content"]})
        return "".join(textos)
    if p == "openai_compat":
        content = [{"type": "text", "text": prompt}]
        for img in images:
            b64 = base64.b64encode(Path(img).read_bytes()).decode()
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        msgs = ([{"role": "system", "content": system}] if system else []) + \
               [{"role": "user", "content": content if images else prompt}]
        headers = {"Content-Type": "application/json"}
        if s["openai_compat_key"]:
            headers["Authorization"] = f"Bearer {s['openai_compat_key']}"
        r = http("POST", s["openai_compat_base"].rstrip("/") + "/chat/completions", headers=headers, timeout=timeout,
                 json={"model": model or s["openai_compat_model"], "messages": msgs, "max_tokens": max_tokens})
        return r.json()["choices"][0]["message"]["content"]
    if p == "gemini":
        parts = [{"text": (system + "\n\n" if system else "") + prompt}]
        for img in images:
            parts.append({"inline_data": {"mime_type": "image/jpeg",
                                          "data": base64.b64encode(Path(img).read_bytes()).decode()}})
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/{model or s['gemini_model']}:generateContent"
               f"?key={s['gemini_key']}")
        gbody = {"contents": [{"parts": parts}], "generationConfig": {"maxOutputTokens": max_tokens}}
        if web_search:
            gbody["tools"] = [{"google_search": {}}]
        r = http("POST", url, json=gbody, timeout=timeout)
        return "".join(pt.get("text", "") for pt in r.json()["candidates"][0]["content"]["parts"])
    raise RuntimeError("Nenhuma IA de texto configurada.")


# ------------------------------------------------------------ divisão em cenas
def split_scenes(script: str, seconds_per_scene: float, words_per_sec: float = 2.6) -> list:
    """Divide o roteiro em cenas SEM alterar o texto (a narração fica idêntica ao roteiro)."""
    text = re.sub(r"\r", "", script).strip()
    target = max(6, int(seconds_per_scene * words_per_sec))
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    scenes = []
    for para in paragraphs:
        sentences = re.split(r"(?<=[.!?…;:])\s+", re.sub(r"\s+", " ", para))
        # quebra frases muito longas em vírgulas
        pieces = []
        for s in sentences:
            if len(s.split()) > target * 1.8:
                parts = re.split(r"(?<=,)\s+", s)
                buf = ""
                for part in parts:
                    if buf and len((buf + " " + part).split()) > target * 1.3:
                        pieces.append(buf)
                        buf = part
                    else:
                        buf = (buf + " " + part).strip()
                if buf:
                    pieces.append(buf)
            else:
                pieces.append(s)
        cur = ""
        for s in pieces:
            if not s.strip():
                continue
            if cur and len((cur + " " + s).split()) > target:
                scenes.append(cur.strip())
                cur = s
            else:
                cur = (cur + " " + s).strip()
        if cur:
            if scenes and len(cur.split()) < target * 0.35 and len(scenes[-1].split()) < target * 1.6:
                scenes[-1] = scenes[-1] + " " + cur
            else:
                scenes.append(cur.strip())
    return [{"id": i + 1, "texto": t} for i, t in enumerate(scenes)]


SYSTEM_PROMPTS = """You are a senior video director for faceless YouTube documentaries.
For each narrated scene you write:
- "image_prompt": a vivid, concrete English prompt for an AI image generator showing exactly what the narration describes
  (subject, setting, era, action, camera angle, lighting). Keep characters/places consistent across scenes. No text in images.
- "search_query": 2-4 English keywords to find a matching stock video/photo (generic, visual, e.g. "old sicilian village").
The "image_prompt" describes CONTENT only (who, what, where, composition). The visual style is fixed by the user and is
added automatically: never mention another medium or look (no "photo", "photorealistic", "painting", "3D render", "cartoon"
unless it matches the chosen style) and follow the style direction given below.
If a recurring main character is given, repeat its exact description in every scene where it appears.
Return ONLY a JSON array: [{"id": 1, "image_prompt": "...", "search_query": "..."}]."""


def make_prompts(scenes: list, title: str, style_name: str, custom_style: str, log=print, personagem: str = "",
                 direcao_ref: str = "") -> list:
    """Gera prompt de imagem e termo de busca para cada cena (em lotes)."""
    from .estilos import info as _info_estilo
    style = custom_style if style_name == "Personalizado" else VISUAL_STYLES.get(style_name, "")
    est = _info_estilo(style_name)
    personagem = (personagem or est.get("personagem", "")).strip()
    extra = ""
    if est.get("direcao"):
        extra += f"Style direction: {est['direcao']}\n"
    if direcao_ref:
        extra += f"Editing reference (copy this framing habit): {direcao_ref}\n"
    if personagem:
        extra += f"Recurring main character (use this exact description whenever they appear): {personagem}\n"
    if not llm_available():
        log("Sem IA de texto configurada: usando o próprio texto da cena como prompt (qualidade menor).")
        for sc in scenes:
            words = [w for w in re.findall(r"\w{5,}", sc["texto"])][:4]
            sc["image_prompt"] = sc["texto"]
            sc["search_query"] = " ".join(words) or title
        return scenes
    batch = 25
    for i in range(0, len(scenes), batch):
        part = scenes[i:i + batch]
        listing = "\n".join(f'{sc["id"]}. {sc["texto"]}' for sc in part)
        prompt = (f'Video title: "{title}"\nVisual style: {style_name} ({style})\n{extra}'
                  f"Scenes {part[0]['id']} to {part[-1]['id']} of {len(scenes)}:\n{listing}")
        for attempt in range(3):
            try:
                data = extract_json(chat(prompt, SYSTEM_PROMPTS))
                by_id = {int(d["id"]): d for d in data if "id" in d}
                for sc in part:
                    d = by_id.get(sc["id"], {})
                    sc["image_prompt"] = d.get("image_prompt") or sc["texto"]
                    sc["search_query"] = d.get("search_query") or title
                break
            except Exception as e:
                log(f"  tentativa {attempt + 1} de gerar prompts falhou: {e}")
                if attempt == 2:
                    for sc in part:
                        sc.setdefault("image_prompt", sc["texto"])
                        sc.setdefault("search_query", title)
        log(f"  prompts prontos: cenas {part[0]['id']}–{part[-1]['id']}")
    return scenes


def thumbnail_idea(title: str, script: str, style_name: str, personagem: str = "") -> dict:
    if not llm_available():
        return {"prompt": f"{title}, dramatic YouTube thumbnail, close-up, high contrast, vibrant", "texto": title[:30]}
    p = (f'YouTube video title: "{title}". Script start: "{script[:1200]}". Visual style: {style_name} ({VISUAL_STYLES.get(style_name, "")}).\n'
         + (f"Main character: {personagem}.\n" if personagem else "") +
         'Create a click-worthy thumbnail in exactly that visual style (the style is added automatically, do not name another look). Return ONLY JSON: {"prompt": "<English image prompt: one strong focal subject, '
         'dramatic emotion, high contrast, empty space on one side for text, no text in image>", '
         '"texto": "<2 to 4 punchy words for the thumbnail in the SAME language as the title, uppercase>"}')
    try:
        d = extract_json(chat(p))
        return {"prompt": d.get("prompt", title), "texto": d.get("texto", title[:30])}
    except Exception:
        return {"prompt": f"{title}, dramatic YouTube thumbnail", "texto": title[:30]}
