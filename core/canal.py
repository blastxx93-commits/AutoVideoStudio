"""Análise de canal do YouTube (YouTube Data API v3).
Custo: ~1 unidade por 50 vídeos analisados (+ 100 se precisar buscar o canal pelo nome)."""
import re
import statistics
from collections import Counter
from datetime import datetime, timezone, timedelta

from .nichos import API, _key, _iso_dur, _chunks
from .utils import http

DIAS = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"]
STOP = set("""a o e é de da do das dos em no na nos nas um uma uns umas que para por com sem como mais muito sua seu
suas seus se ao à às os as ele ela eles elas isso esse essa este esta foi ser são tem the of and to in is you
your for on with how why what this that from at by it an my me we el la los las y en del con por para un una
es que su se lo al""".split())


def resolver_canal(entrada: str, quota) -> str:
    """Aceita link, @handle, ID (UC...) ou nome. Retorna o ID do canal."""
    e = entrada.strip()
    key = _key()
    m = re.search(r"(UC[\w-]{22})", e)
    if m:
        return m.group(1)
    m = re.search(r"@([\w.\-]+)", e)
    if m:
        r = http("GET", f"{API}/channels", params={"part": "id", "forHandle": "@" + m.group(1), "key": key}).json()
        quota[0] += 1
        if r.get("items"):
            return r["items"][0]["id"]
    m = re.search(r"youtube\.com/(?:user|c)/([\w.\-]+)", e)
    if m:
        r = http("GET", f"{API}/channels", params={"part": "id", "forUsername": m.group(1), "key": key}).json()
        quota[0] += 1
        if r.get("items"):
            return r["items"][0]["id"]
        e = m.group(1)
    m = re.search(r"watch\?v=([\w-]{11})|youtu\.be/([\w-]{11})|shorts/([\w-]{11})", e)
    if m:
        vid = next(g for g in m.groups() if g)
        r = http("GET", f"{API}/videos", params={"part": "snippet", "id": vid, "key": key}).json()
        quota[0] += 1
        if r.get("items"):
            return r["items"][0]["snippet"]["channelId"]
    r = http("GET", f"{API}/search", params={"part": "snippet", "type": "channel", "q": e, "maxResults": 1,
                                              "key": key}).json()
    quota[0] += 100
    if r.get("items"):
        return r["items"][0]["snippet"]["channelId"]
    raise RuntimeError("Canal não encontrado. Cole o link do canal, o @ ou o link de um vídeo dele.")


def analisar_canal(entrada: str, max_videos: int = 200, rpm_min=0.5, rpm_max=4.0) -> dict:
    quota = [0]
    key = _key()
    cid = resolver_canal(entrada, quota)
    r = http("GET", f"{API}/channels", params={"part": "snippet,statistics,contentDetails,brandingSettings",
                                                "id": cid, "key": key}).json()
    quota[0] += 1
    if not r.get("items"):
        raise RuntimeError("Canal não encontrado.")
    c = r["items"][0]
    uploads = c["contentDetails"]["relatedPlaylists"]["uploads"]

    ids, token = [], None
    while len(ids) < max_videos:
        p = {"part": "contentDetails", "playlistId": uploads, "maxResults": 50, "key": key}
        if token:
            p["pageToken"] = token
        pr = http("GET", f"{API}/playlistItems", params=p).json()
        quota[0] += 1
        ids += [it["contentDetails"]["videoId"] for it in pr.get("items", [])]
        token = pr.get("nextPageToken")
        if not token:
            break
    ids = ids[:max_videos]

    vids = []
    agora = datetime.now(timezone.utc)
    for ch in _chunks(ids):
        vr = http("GET", f"{API}/videos", params={"part": "snippet,statistics,contentDetails", "id": ",".join(ch),
                                                   "key": key}).json()
        quota[0] += 1
        for v in vr.get("items", []):
            pub = datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00"))
            st = v.get("statistics", {})
            dur = _iso_dur(v.get("contentDetails", {}).get("duration", ""))
            views = int(st.get("viewCount", 0))
            dias = max(0.25, (agora - pub).total_seconds() / 86400)
            thumbs = v["snippet"].get("thumbnails", {})
            vids.append({
                "Thumb": (thumbs.get("medium") or thumbs.get("default") or {}).get("url", ""),
                "Título": v["snippet"]["title"], "Publicado": pub.strftime("%d/%m/%Y"), "_pub": pub,
                "Views": views, "Likes": int(st.get("likeCount", 0)), "Comentários": int(st.get("commentCount", 0)),
                "Duração (min)": round(dur / 60, 1), "_dur": dur, "Views/dia": int(views / dias),
                "Tipo": "Short" if dur <= 180 else "Longo",
                "Tags": v["snippet"].get("tags", []),
                "Link": f"https://www.youtube.com/watch?v={v['id']}",
            })
    if not vids:
        raise RuntimeError("O canal não tem vídeos públicos.")
    vids.sort(key=lambda x: x["_pub"], reverse=True)

    cs = c.get("statistics", {})
    subs = int(cs.get("subscriberCount", 0)) if not cs.get("hiddenSubscriberCount") else None
    criado = datetime.fromisoformat(c["snippet"]["publishedAt"].replace("Z", "+00:00"))
    views_l = [v["Views"] for v in vids]
    med = statistics.median(views_l)
    for v in vids:
        v["Desempenho"] = round(v["Views"] / med, 2) if med else 0  # 1.0 = mediana do canal
        v["Engajamento %"] = round((v["Likes"] + v["Comentários"]) / v["Views"] * 100, 2) if v["Views"] else 0

    # frequência
    def n_desde(d):
        return sum(1 for v in vids if v["_pub"] >= agora - timedelta(days=d))
    freq_30, freq_90 = n_desde(30), n_desde(90)
    intervalos = [(vids[i]["_pub"] - vids[i + 1]["_pub"]).days for i in range(min(len(vids) - 1, 20))]

    # tendência: últimos 10 vs 10 anteriores
    rec = [v["Views"] for v in vids[:10]]
    ant = [v["Views"] for v in vids[10:20]]
    tendencia = (statistics.median(rec) / statistics.median(ant) - 1) * 100 if ant and statistics.median(ant) else None

    # tipos
    por_tipo = {}
    for t in ("Longo", "Short"):
        vs = [v["Views"] for v in vids if v["Tipo"] == t]
        if vs:
            por_tipo[t] = {"Vídeos": len(vs), "Mediana de views": int(statistics.median(vs)), "Média": int(sum(vs) / len(vs))}

    # duração (faixas) x views
    faixas = [(0, 3, "até 3 min"), (3, 8, "3–8 min"), (8, 15, "8–15 min"), (15, 25, "15–25 min"),
              (25, 45, "25–45 min"), (45, 9999, "45+ min")]
    por_duracao = {}
    for a, b, nome in faixas:
        vs = [v["Views"] for v in vids if a * 60 < v["_dur"] <= b * 60]
        if vs:
            por_duracao[nome] = int(statistics.median(vs))

    # dia/hora de postagem (horário de Brasília)
    brt = timezone(timedelta(hours=-3))
    por_dia, por_hora = {}, {}
    for v in vids:
        lt = v["_pub"].astimezone(brt)
        por_dia.setdefault(DIAS[lt.weekday()], []).append(v["Views"])
        por_hora.setdefault(f"{lt.hour:02d}h", []).append(v["Views"])
    por_dia = {d: int(statistics.median(por_dia[d])) for d in DIAS if d in por_dia}
    por_hora = {h: int(statistics.median(vs)) for h, vs in sorted(por_hora.items())}
    contagem_dia = Counter(DIAS[v["_pub"].astimezone(brt).weekday()] for v in vids)

    # títulos
    titulos = [v["Título"] for v in vids]
    top_t = [v["Título"] for v in sorted(vids, key=lambda x: -x["Desempenho"])[:max(5, len(vids) // 5)]]

    def palavras(ts):
        return Counter(w for t in ts for w in re.findall(r"[\wÀ-ú]{3,}", t.lower()) if w not in STOP)
    def pct(pattern):
        return f"{sum(bool(re.search(pattern, t)) for t in titulos) * 100 // len(titulos)}%"
    padroes = {
        "Tamanho médio do título (letras)": int(sum(len(t) for t in titulos) / len(titulos)),
        "Títulos com número": pct(r"\d"),
        "Títulos com pergunta (?)": pct(r"\?"),
        "Títulos com PALAVRA EM CAIXA ALTA": pct(r"\b[A-ZÀ-Ú]{4,}\b"),
        "Títulos com emoji": pct("[\U0001F300-\U0001FAFF\u2600-\u27BF]"),
    }
    palavras_top = palavras(top_t).most_common(15)
    tags = Counter(t.lower() for v in vids for t in v["Tags"]).most_common(20)

    # receita estimada (views dos últimos 30 dias de vídeos postados no período é só aproximação)
    views_30 = sum(v["Views"] for v in vids if v["_pub"] >= agora - timedelta(days=30))
    receita = (views_30 / 1000 * rpm_min, views_30 / 1000 * rpm_max)

    idade_m = (agora - criado).days / 30.4
    resumo = {
        "Nome": c["snippet"]["title"], "ID": cid, "Link": f"https://www.youtube.com/channel/{cid}",
        "Foto": c["snippet"].get("thumbnails", {}).get("medium", {}).get("url", ""),
        "Descrição": c["snippet"].get("description", "")[:500],
        "País": c["snippet"].get("country", "—"),
        "Inscritos": subs, "Views totais": int(cs.get("viewCount", 0)), "Vídeos no canal": int(cs.get("videoCount", 0)),
        "Criado em": criado.strftime("%d/%m/%Y"), "Idade (meses)": round(idade_m, 1),
        "Vídeos analisados": len(vids), "Mediana de views": int(med), "Média de views": int(sum(views_l) / len(views_l)),
        "Vídeos últimos 30 dias": freq_30, "Vídeos últimos 90 dias": freq_90,
        "Posta a cada (dias, mediana)": statistics.median(intervalos) if intervalos else None,
        "Tendência (últimos 10 vs 10 anteriores)": None if tendencia is None else f"{tendencia:+.0f}%",
        "Views por inscrito": round(int(cs.get("viewCount", 0)) / subs, 1) if subs else None,
        "Inscritos por mês (média)": int(subs / max(idade_m, 1)) if subs else None,
        "Receita estimada 30 dias (US$)": f"{receita[0]:,.0f} – {receita[1]:,.0f}".replace(",", "."),
    }
    for v in vids:
        v.pop("_pub", None)
        v.pop("_dur", None)
        v.pop("Tags", None)
    return {"resumo": resumo, "videos": vids, "por_tipo": por_tipo, "por_duracao": por_duracao, "por_dia": por_dia,
            "contagem_dia": dict(contagem_dia), "por_hora": por_hora, "padroes": padroes,
            "palavras_top": palavras_top, "tags": tags, "quota": quota[0]}


def analise_ia_canal(a: dict) -> str:
    from .llm import chat, llm_available
    if not llm_available():
        raise RuntimeError("Configure uma IA de texto em APIs e configurações.")
    r = a["resumo"]
    top = sorted(a["videos"], key=lambda v: -v["Desempenho"])[:15]
    pior = sorted(a["videos"], key=lambda v: v["Desempenho"])[:8]
    fmt = lambda vs: "\n".join(f'- "{v["Título"]}" | {v["Views"]} views | {v["Duração (min)"]} min | {v["Publicado"]} | '
                               f'{v["Desempenho"]}x a mediana' for vs_ in [vs] for v in vs_)
    p = (f"Analise este canal do YouTube como um estrategista de canais dark/faceless.\n\nDados:\n"
         + "\n".join(f"- {k}: {v}" for k, v in r.items() if k not in ("Foto", "Link", "ID"))
         + f"\n- Views por tipo: {a['por_tipo']}\n- Mediana de views por duração: {a['por_duracao']}"
         + f"\n- Mediana de views por dia da semana (horário de Brasília): {a['por_dia']}"
         + f"\n- Padrões de título: {a['padroes']}\n- Palavras mais usadas nos melhores títulos: {a['palavras_top']}"
         + f"\n\nMelhores vídeos:\n{fmt(top)}\n\nPiores vídeos:\n{fmt(pior)}\n\n"
         "Responda em português, direto ao ponto, com estes tópicos:\n"
         "1. **Nicho e público**: qual é exatamente o nicho/subnicho e para quem.\n"
         "2. **Por que está crescendo** (ou não): o que os melhores vídeos têm em comum e os piores não.\n"
         "3. **Fórmula de título e thumbnail** que funciona aqui (com 3 modelos de título preenchíveis).\n"
         "4. **Formato**: duração ideal, frequência e melhor dia para postar, com base nos dados.\n"
         "5. **Lacunas**: temas que o canal ainda não explorou e que o público deve querer.\n"
         "6. **Como competir/replicar**: plano prático para um canal novo entrar nesse nicho.\n"
         "7. **10 ideias de títulos** prontos.\n"
         "Não invente números que não estão nos dados.")
    return chat(p, max_tokens=3000)
