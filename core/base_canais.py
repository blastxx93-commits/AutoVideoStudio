"""Base de canais do Buscador de Nichos.

Todo canal promissor achado nas buscas fica guardado aqui, com os 3 vídeos de mais views,
números, % faceless e nicho (estimados pela IA), status (Explodindo, Subindo rápido...) e nota de 0 a 100.
As fotos de crescimento (inscritos e views ao longo dos dias) ficam no radar (core/nichos.py).
"""
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA_DIR
from . import nichos as N

BASE = DATA_DIR / "nichos" / "base.json"
THUMBS = DATA_DIR / "nichos" / "thumbs"

STATUS = ["Explodindo Agora", "Subindo Rápido", "Alta Tração", "Tração Recente", "Poucos Inscritos, Muitas Views"]
ICONES = {"Explodindo Agora": "🔥", "Subindo Rápido": "↗", "Alta Tração": "⚡", "Tração Recente": "〰",
          "Poucos Inscritos, Muitas Views": "✧"}
CURTO = {"Explodindo Agora": "Explodindo", "Subindo Rápido": "Subindo rápido", "Alta Tração": "Alta tração",
         "Tração Recente": "Tração recente", "Poucos Inscritos, Muitas Views": "Poucos inscritos"}
IDIOMAS = {"pt": "Português", "en": "Inglês", "es": "Espanhol", "de": "Alemão", "pl": "Polonês", "cs": "Tcheco",
           "da": "Dinamarquês", "no": "Norueguês", "it": "Italiano", "fr": "Francês"}
PAIS_IDIOMA = {"BR": "pt", "PT": "pt", "US": "en", "GB": "en", "AU": "en", "CA": "en", "ES": "es", "MX": "es",
               "AR": "es", "CO": "es", "CL": "es", "DE": "de", "AT": "de", "PL": "pl", "CZ": "cs", "DK": "da",
               "NO": "no", "IT": "it", "FR": "fr"}


def bandeira(pais: str) -> str:
    pais = (pais or "").upper()
    if len(pais) != 2 or not pais.isalpha():
        return ""
    return chr(0x1F1E6 + ord(pais[0]) - 65) + chr(0x1F1E6 + ord(pais[1]) - 65)


def ler() -> dict:
    try:
        return json.loads(BASE.read_text(encoding="utf-8"))
    except Exception:
        return {"canais": {}, "ultima_atualizacao": None}


def gravar(d: dict):
    BASE.parent.mkdir(parents=True, exist_ok=True)
    tmp = BASE.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    tmp.replace(BASE)


# ------------------------------------------------------------------ métricas
def _dias_postando(c: dict) -> int:
    ref = c.get("primeiro_video") or c.get("criado")
    if not ref:
        return 0
    return max(1, (datetime.now(timezone.utc) - datetime.fromisoformat(ref)).days)


def recalcular(c: dict, radar: dict = None):
    dias = _dias_postando(c)
    c["dias_postando"] = dias
    meses = max(dias / 30, 0.5)
    c["vids_mes"] = round(c.get("videos", 0) / meses, 1)
    c["views_mes"] = int(c.get("views", 0) / meses)
    snaps = (radar or {}).get(c["id"], {}).get("snaps", [])
    cr = N.crescimento(snaps)
    c["inscritos_dia"], c["views_dia"] = (cr[0], cr[1]) if cr else (None, None)
    subs = max(c.get("inscritos", 0), 10)
    razao = c.get("views", 0) / subs
    st = []
    if c.get("vel_max", 0) >= 300 or any(v.get("views", 0) >= max(50_000, 20 * subs) for v in c.get("top", [])[:1]) \
            and dias <= 45:
        st.append("Explodindo Agora")
    if (c.get("inscritos_dia") or 0) >= 50 or (c.get("aceleracao") or 0) >= 2:
        st.append("Subindo Rápido")
    if c["views_mes"] >= 1_000_000:
        st.append("Alta Tração")
    if dias <= 60 and c["views_mes"] >= 200_000:
        st.append("Tração Recente")
    if razao >= 100:
        st.append("Poucos Inscritos, Muitas Views")
    c["status"] = st
    # nota do canal (0–100): outlier, ritmo, juventude, crescimento
    p = min(30, math.log10(c["views_mes"] + 1) * 4.6)               # views por mês
    p += min(20, math.log10(razao + 1) * 8)                          # views muito acima dos inscritos
    p += max(0, 1 - dias / 180) * 20                                  # canal jovem
    p += min(15, math.log10(c.get("vel_max", 0) + 1) * 5)            # velocidade agora
    p += min(15, max(0, math.log2(max(c.get("aceleracao") or 1, 1))) * 5
             + (math.log10(c["inscritos_dia"] + 1) * 3 if (c.get("inscritos_dia") or 0) > 0 else 0))
    c["nota"] = round(min(100, p))


# ------------------------------------------------------------------ gravação vinda das buscas
def registrar(chans: dict, momento: dict, info: dict):
    """chans = canais da API; momento = N.momento_canais; info = cid -> {nicho, termo, lang}."""
    d = ler()
    radar = N._radar_ler()["canais"]
    agora = time.time()
    for cid, ch in chans.items():
        m = momento.get(cid) or {}
        sn, stt = ch.get("snippet", {}), ch.get("statistics", {})
        c = d["canais"].get(cid) or {"id": cid, "adicionado": agora, "favorito": False, "excluido": False,
                                     "faceless": None, "nicho_ia": "", "palavras": ""}
        if c.get("excluido"):
            continue
        th = sn.get("thumbnails", {})
        pais = sn.get("country", "") or c.get("pais", "")
        inf = info.get(cid, {})
        c.update({
            "nome": sn.get("title", c.get("nome", "")),
            "avatar": (th.get("default") or th.get("medium") or {}).get("url", c.get("avatar", "")),
            "pais": pais,
            "idioma": c.get("idioma") or PAIS_IDIOMA.get(pais) or inf.get("lang", ""),
            "criado": sn.get("publishedAt", "").replace("Z", "+00:00") or c.get("criado"),
            "inscritos": int(stt.get("subscriberCount", 0)), "views": int(stt.get("viewCount", 0)),
            "videos": int(stt.get("videoCount", 0)),
            "nicho_busca": c.get("nicho_busca") or inf.get("nicho", ""), "termo": c.get("termo") or inf.get("termo", ""),
            "atualizado": agora,
        })
        if m:
            c.update({"top": m.get("top", c.get("top", [])), "vel_max": m.get("vel_max", 0),
                      "aceleracao": m.get("aceleracao"),
                      "primeiro_video": m.get("primeiro_dt") if m.get("completo") else c.get("primeiro_video")})
        recalcular(c, radar)
        d["canais"][cid] = c
    gravar(d)


def classificar_ia(limite: int = 40, log=print) -> int:
    """Estima % faceless, nicho e palavras-chave dos canais novos olhando as 3 thumbs + títulos (1 imagem por canal)."""
    from .llm import chat, llm_available
    from .utils import download, extract_json
    if not llm_available():
        return 0
    d = ler()
    pend = [c for c in d["canais"].values() if c.get("faceless") is None and c.get("top") and not c.get("excluido")]
    pend.sort(key=lambda c: -c.get("nota", 0))
    THUMBS.mkdir(parents=True, exist_ok=True)
    feitos = 0
    from PIL import Image
    for c in pend[:limite]:
        try:
            imgs = []
            for v in c["top"][:3]:
                f = THUMBS / f"{v['id']}.jpg"
                if not f.exists() and v.get("thumb"):
                    download(v["thumb"], f)
                if f.exists():
                    imgs.append(Image.open(f).convert("RGB").resize((320, 180)))
            if not imgs:
                continue
            col = Image.new("RGB", (320 * len(imgs), 180))
            for i, im in enumerate(imgs):
                col.paste(im, (320 * i, 0))
            fc = THUMBS / f"col_{c['id']}.jpg"
            col.save(fc, quality=80)
            titulos = " | ".join(v.get("titulo", "") for v in c["top"][:3])
            r = extract_json(chat(
                f'YouTube channel "{c["nome"]}". Top video titles: {titulos}\n'
                "The image shows its top 3 thumbnails. Reply ONLY JSON: "
                '{"faceless": 0-100 (probability the channel is faceless: no host/creator showing their face on camera; '
                'AI images, stock footage, animation or narration only = high), '
                '"nicho": "short niche in Brazilian Portuguese, 1-2 words (ex.: História, True Crime, Finanças)", '
                '"palavras": "1-2 main topic keywords in Brazilian Portuguese"}',
                images=[str(fc)], max_tokens=150))
            c["faceless"] = int(r.get("faceless", 0))
            c["nicho_ia"] = str(r.get("nicho", ""))[:30]
            c["palavras"] = str(r.get("palavras", ""))[:40]
            feitos += 1
        except Exception as e:
            log(f"  não consegui classificar {c.get('nome')}: {str(e)[:100]}")
    if feitos:
        gravar(d)
        log(f"IA estimou faceless e nicho de {feitos} canais.")
    return feitos


def atualizar_todos(log=print) -> tuple:
    """Relê inscritos/views de todos os canais da base (1 unidade a cada 50 canais) e recalcula status e nota."""
    d = ler()
    ids = [cid for cid, c in d["canais"].items() if not c.get("excluido")]
    key = N._key()
    chans, gasto = {}, 0
    for ch in N._chunks(ids):
        r = N.http("GET", f"{N.API}/channels", params={"part": "snippet,statistics", "id": ",".join(ch),
                                                      "key": key}).json()
        gasto += 1
        for c in r.get("items", []):
            chans[c["id"]] = c
    N.radar_registrar(chans)
    radar = N._radar_ler()["canais"]
    agora = time.time()
    for cid, ch in chans.items():
        c = d["canais"][cid]
        stt = ch.get("statistics", {})
        c.update({"inscritos": int(stt.get("subscriberCount", 0)), "views": int(stt.get("viewCount", 0)),
                  "videos": int(stt.get("videoCount", 0)), "atualizado": agora})
        recalcular(c, radar)
    d["ultima_atualizacao"] = {"quando": agora, "canais": len(chans), "gasto": gasto}
    gravar(d)
    return len(chans), gasto


def favoritar(cid: str, sim: bool):
    d = ler()
    c = d["canais"].get(cid)
    if c:
        c["favorito"] = sim
        gravar(d)
        N.radar_seguir(cid, c.get("nome", ""), f"https://www.youtube.com/channel/{cid}", c.get("nicho_busca", ""), sim)


def excluir(cids: list):
    d = ler()
    for cid in cids:
        if cid in d["canais"]:
            d["canais"][cid]["excluido"] = True
    gravar(d)


# ------------------------------------------------------------------ consulta com filtros
def consultar(texto="", aba="Todos", categoria="", idioma="", status="", foco="", ordem="nota",
              data_campo="adicionado", periodo="Todos", dia=None, so_favoritos=False) -> tuple:
    """Retorna (lista_filtrada, contagem_por_aba) — a contagem considera os outros filtros, como no print."""
    d = ler()
    agora = time.time()
    base = []
    for c in d["canais"].values():
        if c.get("excluido"):
            continue
        if so_favoritos and not c.get("favorito"):
            continue
        if texto:
            alvo = (c.get("nome", "") + " " + " ".join(v.get("titulo", "") for v in c.get("top", []))).lower()
            if texto.lower() not in alvo:
                continue
        if categoria and categoria not in (c.get("nicho_ia"), c.get("nicho_busca")):
            continue
        if idioma and c.get("idioma") != idioma:
            continue
        if status and status not in c.get("status", []):
            continue
        if foco == "Faceless (70%+)" and (c.get("faceless") or 0) < 70:
            continue
        if foco == "Com rosto" and (c.get("faceless") is None or c["faceless"] >= 40):
            continue
        if foco == "Favoritos" and not c.get("favorito"):
            continue
        ts = c.get(data_campo) or 0
        if periodo == "Hoje" and datetime.fromtimestamp(ts).date() != datetime.now().date():
            continue
        if periodo in ("Últimos 3 dias", "Últimos 7 dias", "Últimos 30 dias"):
            n = int(periodo.split()[1])
            if agora - ts > n * 86400:
                continue
        if periodo == "Data específica" and dia and datetime.fromtimestamp(ts).date() != dia:
            continue
        base.append(c)
    contagem = {"Todos": len(base)}
    for s in STATUS:
        contagem[s] = sum(1 for c in base if s in c.get("status", []))
    lst = base if aba == "Todos" else [c for c in base if aba in c.get("status", [])]
    chave = {"nota": lambda c: -c.get("nota", 0), "views_mes": lambda c: -c.get("views_mes", 0),
             "inscritos": lambda c: -c.get("inscritos", 0), "recente": lambda c: -c.get("adicionado", 0),
             "crescimento": lambda c: -(c.get("inscritos_dia") or 0), "jovem": lambda c: c.get("dias_postando", 9999),
             "faceless": lambda c: -(c.get("faceless") or 0)}[ordem]
    return sorted(lst, key=chave), contagem


def categorias() -> list:
    d = ler()
    return sorted({c.get("nicho_ia") or c.get("nicho_busca") for c in d["canais"].values()
                   if not c.get("excluido") and (c.get("nicho_ia") or c.get("nicho_busca"))})


def idiomas() -> list:
    d = ler()
    return sorted({c.get("idioma") for c in d["canais"].values() if not c.get("excluido") and c.get("idioma")})
