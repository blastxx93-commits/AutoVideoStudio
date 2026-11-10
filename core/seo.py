"""Descrição, hashtags e palavras-chave do vídeo (SEO para o YouTube).
Demanda: usa as sugestões de busca do próprio YouTube (o que as pessoas realmente digitam)
e, opcionalmente, a YouTube Data API para medir views dos vídeos recentes de cada hashtag."""
import json
import re
import statistics
from datetime import datetime, timedelta, timezone

import requests

from .config import load_settings
from .llm import chat, llm_available
from .utils import extract_json, http

IDIOMAS = {"Automático (mesmo do roteiro)": None, "Português": "pt", "English": "en", "Español": "es",
           "Deutsch": "de", "Polski": "pl", "Čeština": "cs", "Dansk": "da", "Norsk": "no"}
NOME_IDIOMA = {"pt": "Portuguese (Brazil)", "en": "English", "es": "Spanish", "de": "German", "pl": "Polish",
               "cs": "Czech", "da": "Danish", "no": "Norwegian"}
PAIS = {"pt": "BR", "en": "US", "es": "ES", "de": "DE", "pl": "PL", "cs": "CZ", "da": "DK", "no": "NO"}


def _ts(t: float) -> str:
    t = int(t)
    return f"{t // 3600}:{t % 3600 // 60:02d}:{t % 60:02d}" if t >= 3600 else f"{t // 60}:{t % 60:02d}"


def sugestoes_youtube(termo: str, lang: str = "pt") -> list:
    """O que as pessoas digitam na busca do YouTube (autocompletar). Grátis, sem chave."""
    try:
        r = requests.get("https://suggestqueries.google.com/complete/search",
                         params={"client": "firefox", "ds": "yt", "q": termo, "hl": lang, "gl": PAIS.get(lang, "US")},
                         headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        data = json.loads(r.content.decode("utf-8", errors="replace"))
        return [s for s in data[1] if isinstance(s, str)]
    except Exception:
        return []


def pesquisar_demanda(seeds: list, lang: str, log=print) -> dict:
    """Expande cada semente com o autocompletar. Retorna {sugestão: posição_média} (menor = mais buscado)."""
    pos = {}
    consultas = []
    for sd in seeds[:6]:
        consultas.append(sd)
        consultas += [f"{sd} {c}" for c in "abcdeimpst"[:4]]
    for q in consultas:
        for i, sug in enumerate(sugestoes_youtube(q, lang)):
            sug = sug.strip().lower()
            pos.setdefault(sug, []).append(i + 1)
    log(f"  {len(pos)} buscas reais encontradas no YouTube")
    # mais vezes sugerido e em posições mais altas = mais demanda
    return {k: round(sum(v) / len(v) - 0.6 * len(v), 2) for k, v in pos.items()}


def demanda_hashtag_api(tag: str, lang: str) -> dict:
    """Mede a hashtag na API do YouTube: vídeos recentes e views (custa ~101 unidades)."""
    s = load_settings()
    key = s.get("youtube_key")
    if not key:
        return {}
    after = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    r = http("GET", "https://www.googleapis.com/youtube/v3/search",
             params={"part": "id", "type": "video", "q": "#" + tag, "order": "viewCount", "publishedAfter": after,
                     "maxResults": 15, "relevanceLanguage": lang, "key": key}).json()
    ids = [i["id"]["videoId"] for i in r.get("items", []) if i.get("id", {}).get("videoId")]
    views = []
    if ids:
        v = http("GET", "https://www.googleapis.com/youtube/v3/videos",
                 params={"part": "statistics", "id": ",".join(ids), "key": key}).json()
        views = [int(x["statistics"].get("viewCount", 0)) for x in v.get("items", [])]
    return {"videos_30d": r.get("pageInfo", {}).get("totalResults", 0),
            "mediana_views_top": int(statistics.median(views)) if views else 0}


def _capitulos_padrao(scenes: list, total: float) -> list:
    if total < 120 or len(scenes) < 4:
        return []
    n = max(3, min(10, int(total // 90)))
    passo = total / n
    caps, alvo = [], 0.0
    for sc in scenes:
        if sc["inicio"] >= alvo - 0.01:
            caps.append({"tempo": sc["inicio"] if caps else 0.0, "titulo": " ".join(sc["texto"].split()[:6]) + "…"})
            alvo += passo
    return caps


def gerar(job: dict, scenes: list = None, total: float = 0.0, log=print) -> dict:
    """Gera descrição, hashtags e palavras-chave. scenes/total permitem capítulos com tempo."""
    titulo, roteiro = job["titulo"], job["roteiro"]
    lang = IDIOMAS.get(job.get("seo_idioma", ""), None)
    n_hash = int(job.get("seo_qtd_hashtags", 5))
    scenes = scenes or []

    # 1) sementes e idioma
    seeds = []
    if llm_available():
        try:
            d = extract_json(chat(
                f'Video title: "{titulo}"\nScript start: "{roteiro[:1500]}"\n'
                'Return ONLY JSON: {"lang": "<ISO 639-1 code of the script language>", '
                '"seeds": ["5 short search phrases (1-3 words) viewers would type on YouTube to find this video, '
                'in the script language, most generic first"]}', max_tokens=400))
            lang = lang or d.get("lang", "pt")
            seeds = [x for x in d.get("seeds", []) if isinstance(x, str)]
        except Exception as e:
            log(f"  sementes por IA falharam: {e}")
    lang = (lang or "pt")[:2]
    if not seeds:
        palavras = [w for w in re.findall(r"[\wÀ-ÿ]{4,}", titulo.lower())]
        seeds = [" ".join(palavras[:2])] + palavras[:4]

    # 2) demanda real (autocompletar do YouTube)
    log("  pesquisando o que as pessoas buscam no YouTube...")
    demanda = pesquisar_demanda(seeds, lang, log)
    top_buscas = sorted(demanda, key=demanda.get)[:60]

    # 3) capítulos
    lista_cenas = ""
    if scenes and total >= 120:
        passo = max(1, len(scenes) // 80)
        lista_cenas = "\n".join(f"[{_ts(sc['inicio'])}] {sc['texto'][:90]}" for sc in scenes[::passo])

    resultado = {"lang": lang}
    if llm_available():
        cta = job.get("seo_texto_fixo", "").strip()
        p = (f"You are a YouTube SEO expert for faceless documentary channels.\n"
             f'Title: "{titulo}"\nLanguage for ALL output: {NOME_IDIOMA.get(lang, lang)}\n'
             f'Script (start): "{roteiro[:3500]}"\n\n'
             f"REAL searches people type on YouTube about this topic (most searched first):\n- " + "\n- ".join(top_buscas[:45]) + "\n\n"
             + (f"Scene timeline (for chapters):\n{lista_cenas}\n\n" if lista_cenas else "")
             + "Return ONLY JSON with:\n"
             '"descricao": an engaging YouTube description: first 2 lines are a strong hook that includes the main search '
             "keyword naturally (they show before 'more'); then a 3-5 sentence summary that weaves in 3-5 of the real "
             "searches naturally; no hashtags inside; no emojis spam (max 3); do not invent facts not in the script.\n"
             + ('"capitulos": 4 to 10 chapters [{"tempo": "<m:ss from the timeline>", "titulo": "<short chapter title>"}], '
                'first one MUST be "0:00", each at least 30 seconds apart, using the real timeline times.\n' if lista_cenas else "")
             + f'"hashtags": exactly {n_hash} hashtags WITHOUT the # sign, no spaces, prefer ones based on the real searches, '
             "most relevant first (the first 3 appear above the title).\n"
             '"palavras_chave": 20 to 30 YouTube tags/keywords, prioritizing EXACT real searches from the list, then '
             "variations; most important first.\n")
        try:
            d = extract_json(chat(p, max_tokens=3000))
            resultado.update(d)
        except Exception as e:
            log(f"  IA falhou ao escrever a descrição: {e}")
    # fallbacks
    if not resultado.get("descricao"):
        frases = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", roteiro).strip())
        resultado["descricao"] = " ".join(frases[:3])
    if not resultado.get("hashtags"):
        resultado["hashtags"] = [re.sub(r"\W", "", b.title()) for b in top_buscas[:n_hash]] or \
                                [re.sub(r"\W", "", w.title()) for w in seeds[:n_hash]]
    if not resultado.get("palavras_chave"):
        resultado["palavras_chave"] = top_buscas[:25] or seeds
    if not resultado.get("capitulos") and scenes and total >= 120 and not llm_available():
        resultado["capitulos"] = [{"tempo": _ts(c["tempo"]), "titulo": c["titulo"]} for c in _capitulos_padrao(scenes, total)]

    # limpeza e regras do YouTube
    hs = []
    for h in resultado["hashtags"]:
        h = re.sub(r"[^\w]", "", str(h).lstrip("#"), flags=re.UNICODE)
        if h and h.lower() not in [x.lower() for x in hs]:
            hs.append(h)
    resultado["hashtags"] = hs[:min(15, n_hash)]  # mais de 15 o YouTube ignora todas
    kws, tamanho = [], 0
    for k in resultado["palavras_chave"]:
        k = re.sub(r"[<>,]", "", str(k)).strip()
        if k and k.lower() not in [x.lower() for x in kws] and tamanho + len(k) + 1 <= 495:  # limite de 500 letras
            kws.append(k)
            tamanho += len(k) + 1
    resultado["palavras_chave"] = kws
    resultado["buscadas"] = [k for k in kws if k.lower() in demanda]
    caps = resultado.get("capitulos") or []
    if caps:
        caps = [c for c in caps if isinstance(c, dict) and c.get("tempo") and c.get("titulo")]
        if caps and caps[0]["tempo"] not in ("0:00", "00:00", "0:00:00"):
            caps.insert(0, {"tempo": "0:00", "titulo": "Introdução" if lang == "pt" else "Intro"})
        resultado["capitulos"] = caps if len(caps) >= 3 else []

    # 4) demanda das hashtags pela API (opcional)
    if job.get("seo_checar_api") and load_settings().get("youtube_key"):
        log("  medindo hashtags na API do YouTube...")
        info = {}
        for h in resultado["hashtags"][:8]:
            try:
                info[h] = demanda_hashtag_api(h, lang)
            except Exception as e:
                log(f"  #{h}: {e}")
        resultado["demanda_hashtags"] = info
    fixo = job.get("seo_texto_fixo", "").strip()
    cred = job.get("_creditos_musica") or []
    if cred:
        fixo = (fixo + "\n\n" if fixo else "") + "🎵 Música:\n" + "\n".join(cred)
    resultado["texto_fixo"] = fixo
    resultado["incluir_capitulos"] = job.get("seo_capitulos", True)
    return resultado


def montar_descricao(r: dict) -> str:
    """Texto final pronto para colar no YouTube."""
    partes = [r.get("descricao", "").strip()]
    if r.get("incluir_capitulos", True) and r.get("capitulos"):
        partes.append("\n".join(f"{c['tempo']} {c['titulo']}" for c in r["capitulos"]))
    if r.get("texto_fixo", "").strip():
        partes.append(r["texto_fixo"].strip())
    if r.get("hashtags"):
        partes.append(" ".join("#" + h for h in r["hashtags"]))
    return "\n\n".join(p for p in partes if p)


def salvar(r: dict, pasta):
    from pathlib import Path
    pasta = Path(pasta)
    (pasta / "seo.json").write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    (pasta / "descricao.txt").write_text(montar_descricao(r), encoding="utf-8")
    (pasta / "palavras_chave.txt").write_text(", ".join(r.get("palavras_chave", [])), encoding="utf-8")
    (pasta / "hashtags.txt").write_text(" ".join("#" + h for h in r.get("hashtags", [])), encoding="utf-8")
