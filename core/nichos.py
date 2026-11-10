"""BUSCADOR DE NICHOS: acha canais pequenos (poucos inscritos) com vídeos recentes explodindo em views.
Usa a YouTube Data API v3 (grátis; cota diária de 10.000 unidades).
Custo por busca: ~100 unidades por página de 50 vídeos + 2 unidades para estatísticas."""
import json
import math
import re
import statistics
import time
from datetime import datetime, timedelta, timezone

from .config import load_settings, DATA_DIR
from .utils import http

API = "https://www.googleapis.com/youtube/v3"

# Nichos prontos, traduzidos por idioma (pt, en, es, de, pl, cs, da, no)
NICHOS = {
    "Dark / Mistério": {
        "pt": ["mistérios não resolvidos", "casos misteriosos", "lugares assombrados"],
        "en": ["unsolved mysteries", "mysterious cases", "haunted places"],
        "es": ["misterios sin resolver", "casos misteriosos", "lugares embrujados"],
        "de": ["ungelöste Rätsel", "mysteriöse Fälle", "Lost Places"],
        "pl": ["niewyjaśnione zagadki", "tajemnicze sprawy", "nawiedzone miejsca"],
        "cs": ["nevyřešené záhady", "tajemné případy", "strašidelná místa"],
        "da": ["uløste mysterier", "mystiske sager", "hjemsøgte steder"],
        "no": ["uløste mysterier", "mystiske saker", "hjemsøkte steder"]},
    "True crime": {
        "pt": ["true crime caso real", "crimes que chocaram", "serial killer documentário"],
        "en": ["true crime case", "crimes that shocked the world", "serial killer documentary"],
        "es": ["true crime caso real", "crímenes que impactaron", "asesino en serie documental"],
        "de": ["True Crime Fall", "wahre Kriminalfälle", "Serienmörder Doku"],
        "pl": ["true crime po polsku", "zbrodnie które wstrząsnęły", "seryjny morderca dokument"],
        "cs": ["true crime česky", "kriminální případy", "sériový vrah dokument"],
        "da": ["true crime dansk", "kriminalsager", "seriemorder dokumentar"],
        "no": ["true crime norsk", "kriminalsaker", "seriemorder dokumentar"]},
    "Máfia / Crime organizado": {
        "pt": ["máfia italiana história", "cartel documentário", "gângsteres famosos"],
        "en": ["italian mafia history", "cartel documentary", "famous gangsters"],
        "es": ["historia de la mafia italiana", "cártel documental", "gánsteres famosos"],
        "de": ["Mafia Geschichte", "Kartell Doku", "berühmte Gangster"],
        "pl": ["historia mafii", "kartel dokument", "słynni gangsterzy"],
        "cs": ["historie mafie", "kartel dokument", "slavní gangsteři"],
        "da": ["mafiaens historie", "kartel dokumentar", "berømte gangstere"],
        "no": ["mafiaens historie", "kartell dokumentar", "kjente gangstere"]},
    "Mitologia": {
        "pt": ["mitologia grega", "mitologia nórdica", "deuses e lendas"],
        "en": ["greek mythology", "norse mythology", "myths and legends"],
        "es": ["mitología griega", "mitología nórdica", "mitos y leyendas"],
        "de": ["griechische Mythologie", "nordische Mythologie", "Mythen und Legenden"],
        "pl": ["mitologia grecka", "mitologia nordycka", "mity i legendy"],
        "cs": ["řecká mytologie", "severská mytologie", "mýty a legendy"],
        "da": ["græsk mytologi", "nordisk mytologi", "myter og sagn"],
        "no": ["gresk mytologi", "norrøn mytologi", "myter og sagn"]},
    "História": {
        "pt": ["história antiga documentário", "segunda guerra mundial histórias", "impérios que caíram"],
        "en": ["ancient history documentary", "world war 2 stories", "fall of empires"],
        "es": ["historia antigua documental", "historias segunda guerra mundial", "imperios que cayeron"],
        "de": ["Geschichte Doku", "Zweiter Weltkrieg Geschichten", "Untergang von Imperien"],
        "pl": ["historia starożytna dokument", "druga wojna światowa historie", "upadek imperiów"],
        "cs": ["historie dokument", "druhá světová válka příběhy", "pád říší"],
        "da": ["historie dokumentar", "anden verdenskrig historier", "imperiers fald"],
        "no": ["historie dokumentar", "andre verdenskrig historier", "imperiers fall"]},
    "Sobrevivência": {
        "pt": ["histórias reais de sobrevivência", "sobreviveu sozinho", "perdido na selva"],
        "en": ["true survival stories", "survived alone", "lost in the jungle"],
        "es": ["historias reales de supervivencia", "sobrevivió solo", "perdido en la selva"],
        "de": ["wahre Überlebensgeschichten", "allein überlebt", "im Dschungel verschollen"],
        "pl": ["prawdziwe historie przetrwania", "przeżył sam", "zaginiony w dżungli"],
        "cs": ["skutečné příběhy přežití", "přežil sám", "ztracen v džungli"],
        "da": ["sande overlevelseshistorier", "overlevede alene", "fortabt i junglen"],
        "no": ["sanne overlevelseshistorier", "overlevde alene", "savnet i jungelen"]},
    "Curiosidades": {
        "pt": ["curiosidades incríveis", "fatos que você não sabia", "como funciona"],
        "en": ["amazing facts", "things you didn't know", "how it works"],
        "es": ["curiosidades increíbles", "datos que no sabías", "cómo funciona"],
        "de": ["unglaubliche Fakten", "Dinge die du nicht wusstest", "wie funktioniert"],
        "pl": ["ciekawostki", "fakty których nie znałeś", "jak to działa"],
        "cs": ["zajímavosti", "věci které jste nevěděli", "jak to funguje"],
        "da": ["utrolige fakta", "ting du ikke vidste", "hvordan virker det"],
        "no": ["utrolige fakta", "ting du ikke visste", "hvordan fungerer det"]},
    "Carros": {
        "pt": ["carros raros", "história de carros", "carros abandonados"],
        "en": ["rare cars", "car history", "abandoned cars"],
        "es": ["autos raros", "historia de autos", "autos abandonados"],
        "de": ["seltene Autos", "Auto Geschichte", "verlassene Autos"],
        "pl": ["rzadkie samochody", "historia samochodów", "porzucone samochody"],
        "cs": ["vzácná auta", "historie aut", "opuštěná auta"],
        "da": ["sjældne biler", "bilhistorie", "forladte biler"],
        "no": ["sjeldne biler", "bilhistorie", "forlatte biler"]},
    "Finanças / Ricos": {
        "pt": ["como ficou rico", "bilionários história", "empresas que faliram"],
        "en": ["how he got rich", "billionaire stories", "companies that went bankrupt"],
        "es": ["cómo se hizo rico", "historias de multimillonarios", "empresas que quebraron"],
        "de": ["wie er reich wurde", "Milliardär Geschichte", "Firmen die pleite gingen"],
        "pl": ["jak został bogaty", "historie miliarderów", "firmy które zbankrutowały"],
        "cs": ["jak zbohatl", "příběhy miliardářů", "firmy které zkrachovaly"],
        "da": ["hvordan han blev rig", "milliardær historie", "virksomheder der gik konkurs"],
        "no": ["hvordan han ble rik", "milliardær historie", "selskaper som gikk konkurs"]},
    "Espaço / Ciência": {
        "pt": ["universo documentário", "mistérios do espaço", "ciência explicada"],
        "en": ["universe documentary", "space mysteries", "science explained"],
        "es": ["universo documental", "misterios del espacio", "ciencia explicada"],
        "de": ["Universum Doku", "Rätsel des Weltalls", "Wissenschaft erklärt"],
        "pl": ["wszechświat dokument", "tajemnice kosmosu", "nauka wyjaśniona"],
        "cs": ["vesmír dokument", "záhady vesmíru", "věda vysvětlená"],
        "da": ["universet dokumentar", "rummets mysterier", "videnskab forklaret"],
        "no": ["universet dokumentar", "verdensrommets mysterier", "vitenskap forklart"]},
    "Histórias / Relatos": {
        "pt": ["histórias reais emocionantes", "relatos de reddit", "histórias de vingança"],
        "en": ["true emotional stories", "reddit stories", "revenge stories"],
        "es": ["historias reales emotivas", "historias de reddit", "historias de venganza"],
        "de": ["wahre Geschichten", "Reddit Geschichten", "Rache Geschichten"],
        "pl": ["prawdziwe historie", "historie z reddita", "historie zemsty"],
        "cs": ["skutečné příběhy", "příběhy z redditu", "příběhy o pomstě"],
        "da": ["sande historier", "reddit historier", "hævnhistorier"],
        "no": ["sanne historier", "reddit historier", "hevnhistorier"]},
    "Bíblia / Religião": {
        "pt": ["histórias da bíblia", "personagens bíblicos", "profecias"],
        "en": ["bible stories", "biblical characters", "prophecies"],
        "es": ["historias de la biblia", "personajes bíblicos", "profecías"],
        "de": ["Geschichten aus der Bibel", "biblische Figuren", "Prophezeiungen"],
        "pl": ["historie biblijne", "postacie biblijne", "proroctwa"],
        "cs": ["biblické příběhy", "biblické postavy", "proroctví"],
        "da": ["bibelhistorier", "bibelske personer", "profetier"],
        "no": ["bibelhistorier", "bibelske personer", "profetier"]},
    "Música / Lofi": {
        "pt": ["lofi para estudar", "música relaxante", "playlist calma"],
        "en": ["lofi study music", "relaxing music", "calm playlist"],
        "es": ["lofi para estudiar", "música relajante", "playlist tranquila"],
        "de": ["Lofi zum Lernen", "entspannende Musik", "ruhige Playlist"],
        "pl": ["lofi do nauki", "muzyka relaksacyjna", "spokojna playlista"],
        "cs": ["lofi na učení", "relaxační hudba", "klidný playlist"],
        "da": ["lofi til at studere", "afslappende musik", "rolig playliste"],
        "no": ["lofi for å studere", "avslappende musikk", "rolig spilleliste"]},
    "Inteligência artificial": {
        "pt": ["inteligência artificial", "ferramentas de IA", "ganhar dinheiro com IA"],
        "en": ["artificial intelligence", "AI tools", "make money with AI"],
        "es": ["inteligencia artificial", "herramientas de IA", "ganar dinero con IA"],
        "de": ["künstliche Intelligenz", "KI Tools", "mit KI Geld verdienen"],
        "pl": ["sztuczna inteligencja", "narzędzia AI", "zarabianie z AI"],
        "cs": ["umělá inteligence", "AI nástroje", "vydělávání s AI"],
        "da": ["kunstig intelligens", "AI værktøjer", "tjen penge med AI"],
        "no": ["kunstig intelligens", "AI verktøy", "tjen penger med AI"]},
}
NICHOS_SUGERIDOS = {n: t["pt"] for n, t in NICHOS.items()}  # compatibilidade

REGIOES = {"Brasil": ("BR", "pt"), "Portugal": ("PT", "pt"), "Estados Unidos": ("US", "en"),
           "Reino Unido": ("GB", "en"), "Austrália": ("AU", "en"), "Espanha": ("ES", "es"), "México": ("MX", "es"),
           "Alemanha": ("DE", "de"), "Polônia": ("PL", "pl"), "República Tcheca": ("CZ", "cs"),
           "Dinamarca": ("DK", "da"), "Noruega": ("NO", "no"), "Mundo (sem região)": (None, None)}

IDIOMA_NOME = {"pt": "português", "en": "inglês", "es": "espanhol", "de": "alemão", "pl": "polonês",
               "cs": "tcheco", "da": "dinamarquês", "no": "norueguês"}


def idioma_da_regiao(regiao: str) -> str:
    return REGIOES.get(regiao, (None, None))[1] or "en"


def termos_nichos(escolhidos: list, regiao: str) -> dict:
    """Termos de busca dos nichos prontos no idioma da região."""
    lang = idioma_da_regiao(regiao)
    return {n: NICHOS[n].get(lang, NICHOS[n]["en"]) for n in escolhidos if n in NICHOS}

DURACOES = {"Qualquer": "any", "Shorts / curtos (< 4 min)": "short",
            "Médios (4–20 min)": "medium", "Longos (> 20 min)": "long"}


def _key():
    k = load_settings().get("youtube_key", "").strip()
    if not k:
        raise RuntimeError("Coloque a chave da YouTube Data API em APIs e configurações.")
    return k


def _iso_dur(s: str) -> int:
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", s or "")
    if not m:
        return 0
    d, h, mi, se = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + se


def erro_amigavel(e) -> str:
    t = str(e)
    if "quotaExceeded" in t or "quota" in t.lower():
        return ("A cota diária grátis da API do YouTube acabou. Ela renova à meia-noite do horário do Pacífico "
                "(por volta das 4h ou 5h da manhã no Brasil). Para gastar menos: menos nichos, 'Checar concorrência' "
                "em 3 ou desligado.")
    if "API key not valid" in t or "keyInvalid" in t or "API_KEY_INVALID" in t:
        return "A chave da YouTube Data API está errada. Copie de novo no Google Cloud e cole em APIs e configurações."
    if "accessNotConfigured" in t or "has not been used" in t or "SERVICE_DISABLED" in t or "is disabled" in t:
        return ("A YouTube Data API v3 não está ativada no projeto da sua chave. No Google Cloud, vá em "
                "APIs e serviços → Biblioteca → YouTube Data API v3 → Ativar. Espere 2 minutos e busque de novo.")
    if "referer" in t.lower() or "API_KEY_HTTP_REFERRER_BLOCKED" in t or "IP address" in t or "API_KEY_SERVICE_BLOCKED" in t:
        return ("A chave tem uma restrição que bloqueia o programa. No Google Cloud → Credenciais → sua chave: em "
                "'Restrições do aplicativo' marque Nenhuma, e em 'Restrições de API' deixe a YouTube Data API v3 liberada.")
    if "Falha de conexão" in t:
        return "Sem conexão com o YouTube. Confira a internet do PC e tente de novo."
    return t[:400]


def _chunks(lst, n=50):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def buscar(termo: str, dias: int, regiao: str, duracao: str, paginas: int = 1, quota=None) -> list:
    """Busca vídeos publicados nos últimos `dias`, ordenados por views."""
    key = _key()
    reg, lang = REGIOES.get(regiao, (None, None))
    after = (datetime.now(timezone.utc) - timedelta(days=dias)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {"part": "snippet", "type": "video", "order": "viewCount", "publishedAfter": after,
              "maxResults": 50, "videoDuration": DURACOES.get(duracao, "any"), "key": key}
    if termo.strip():
        params["q"] = termo.strip()
    if reg:
        params["regionCode"] = reg
    if lang:
        params["relevanceLanguage"] = lang
    ids, token = [], None
    for _ in range(paginas):
        if token:
            params["pageToken"] = token
        r = http("GET", f"{API}/search", params=params).json()
        if quota is not None:
            quota[0] += 100
        ids += [it["id"]["videoId"] for it in r.get("items", []) if it.get("id", {}).get("videoId")]
        token = r.get("nextPageToken")
        if not token:
            break
    return ids


def detalhes(video_ids: list, quota=None):
    key = _key()
    vids, chans = {}, {}
    for ch in _chunks(list(dict.fromkeys(video_ids))):
        r = http("GET", f"{API}/videos", params={"part": "snippet,statistics,contentDetails",
                                                  "id": ",".join(ch), "key": key}).json()
        if quota is not None:
            quota[0] += 1
        for v in r.get("items", []):
            vids[v["id"]] = v
    cids = list({v["snippet"]["channelId"] for v in vids.values()})
    for ch in _chunks(cids):
        r = http("GET", f"{API}/channels", params={"part": "snippet,statistics", "id": ",".join(ch),
                                                    "key": key}).json()
        if quota is not None:
            quota[0] += 1
        for c in r.get("items", []):
            chans[c["id"]] = c
    return vids, chans


def _dt(x: str) -> datetime:
    return datetime.fromisoformat(x.replace("Z", "+00:00"))


def momento_canais(chans: dict, quota=None, log=print) -> dict:
    """Lê os últimos 50 envios de cada canal para medir o 'momento':
    data do 1º vídeo (idade real), aceleração (vídeos novos rendendo mais que os antigos),
    mediana de views e frequência de postagem. Custa ~2 unidades por canal."""
    key = _key()
    agora = datetime.now(timezone.utc)
    envios = {}
    for cid in chans:
        try:
            r = http("GET", f"{API}/playlistItems", params={"part": "contentDetails", "maxResults": 50,
                                                           "playlistId": "UU" + cid[2:], "key": key}).json()
            if quota is not None:
                quota[0] += 1
            envios[cid] = [it["contentDetails"]["videoId"] for it in r.get("items", [])]
        except Exception as e:
            log(f"  não consegui ler os envios de um canal: {e}")
    todos = [v for l in envios.values() for v in l]
    stats = {}
    for ch in _chunks(list(dict.fromkeys(todos))):
        r = http("GET", f"{API}/videos", params={"part": "snippet,statistics", "id": ",".join(ch), "key": key}).json()
        if quota is not None:
            quota[0] += 1
        for v in r.get("items", []):
            th = v["snippet"].get("thumbnails", {})
            stats[v["id"]] = (_dt(v["snippet"]["publishedAt"]), int(v.get("statistics", {}).get("viewCount", 0)),
                              v["snippet"].get("title", ""),
                              (th.get("medium") or th.get("high") or th.get("default") or {}).get("url", ""), v["id"])
    out = {}
    for cid, ids in envios.items():
        vs = sorted((stats[i] for i in ids if i in stats), key=lambda x: x[0], reverse=True)
        if not vs:
            continue
        total = int(chans[cid].get("statistics", {}).get("videoCount", 0))
        completo = total <= len(vs)  # temos todos os vídeos do canal
        primeiro = vs[-1][0]
        views = [x[1] for x in vs]
        k = min(5, max(2, len(views) // 2))
        novos, antigos = views[:k], views[k:]
        acel = (statistics.median(novos) / max(statistics.median(antigos), 1)) if len(antigos) >= 2 else None
        semana = sum(x[1] for x in vs if (agora - x[0]).days < 7)
        mes = [x for x in vs if (agora - x[0]).days < 30]
        out[cid] = {
            "primeiro_video_dias": (agora - primeiro).days if completo else None,
            "mediana_views": int(statistics.median(views)),
            "aceleracao": round(acel, 1) if acel is not None else None,
            "pct_semana": round(100 * semana / max(sum(views), 1)),
            "videos_por_semana": round(len(mes) / 4.3, 1),
            "primeiro_dt": primeiro.isoformat(), "completo": completo,
            "top": [{"id": x[4], "titulo": x[2], "views": x[1], "thumb": x[3]}
                    for x in sorted(vs, key=lambda x: -x[1])[:3]],
            "vel_max": int(max([x[1] / max(1, (agora - x[0]).total_seconds() / 3600)
                                for x in vs if (agora - x[0]).days < 7] or [0])),
        }
    return out


# ------------------------------------------------------------------ radar (acompanhamento ao longo dos dias)
RADAR = DATA_DIR / "nichos" / "radar.json"


def _radar_ler() -> dict:
    try:
        return json.loads(RADAR.read_text(encoding="utf-8"))
    except Exception:
        return {"canais": {}}


def _radar_gravar(d: dict):
    RADAR.parent.mkdir(parents=True, exist_ok=True)
    RADAR.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def crescimento(snaps: list):
    """(Δ inscritos/dia, Δ views/dia, dias) entre a foto mais antiga útil e a mais nova."""
    if len(snaps) < 2:
        return None
    t1, s1, v1 = snaps[-1][:3]
    base = next((x for x in snaps[:-1] if t1 - x[0] >= 6 * 3600), None)
    if not base:
        return None
    dias = (t1 - base[0]) / 86400
    return round((s1 - base[1]) / dias), round((v1 - base[2]) / dias), round(dias, 1)


def radar_registrar(chans: dict, nicho_de: dict = None, seguir: list = ()):
    """Guarda uma 'foto' (inscritos, views, vídeos) de cada canal visto. Na próxima busca dá para medir o crescimento real."""
    d = _radar_ler()
    agora = time.time()
    for cid, c in chans.items():
        st_ = c.get("statistics", {})
        if st_.get("hiddenSubscriberCount"):
            continue
        it = d["canais"].setdefault(cid, {"nome": c["snippet"]["title"], "link": f"https://www.youtube.com/channel/{cid}",
                                          "nicho": (nicho_de or {}).get(cid, ""), "seguindo": False, "snaps": []})
        snap = [agora, int(st_.get("subscriberCount", 0)), int(st_.get("viewCount", 0)), int(st_.get("videoCount", 0))]
        if not it["snaps"] or agora - it["snaps"][-1][0] > 3600:
            it["snaps"].append(snap)
        else:
            it["snaps"][-1] = snap
        it["snaps"] = it["snaps"][-40:]
        if cid in seguir:
            it["seguindo"] = True
    # não deixa o arquivo crescer sem limite: mantém os seguidos + os 3000 vistos mais recentemente
    if len(d["canais"]) > 3000:
        ordem = sorted(d["canais"].items(), key=lambda kv: (kv[1]["seguindo"], kv[1]["snaps"][-1][0]), reverse=True)
        d["canais"] = dict(ordem[:3000])
    _radar_gravar(d)


def radar_seguir(cid: str, nome: str, link: str, nicho: str = "", seguir: bool = True):
    d = _radar_ler()
    it = d["canais"].setdefault(cid, {"nome": nome, "link": link, "nicho": nicho, "seguindo": False, "snaps": []})
    it["seguindo"] = seguir
    _radar_gravar(d)


def radar_lista() -> list:
    d = _radar_ler()
    out = []
    for cid, it in d["canais"].items():
        if not it.get("seguindo"):
            continue
        last = it["snaps"][-1] if it["snaps"] else [0, 0, 0, 0]
        cr = crescimento(it["snaps"])
        out.append({"id": cid, "Canal": it["nome"], "Nicho": it.get("nicho", ""), "Inscritos": last[1], "Views": last[2],
                    "Vídeos": last[3],
                    "Inscritos/dia": cr[0] if cr else None, "Views/dia": cr[1] if cr else None,
                    "Medido em (dias)": cr[2] if cr else None,
                    "Última leitura": datetime.fromtimestamp(last[0]).strftime("%d/%m %H:%M") if last[0] else "—",
                    "Link canal": it["link"]})
    return sorted(out, key=lambda x: -(x["Views/dia"] or 0))


def radar_atualizar(log=print) -> int:
    """Relê os números de todos os canais seguidos (1 unidade a cada 50 canais)."""
    d = _radar_ler()
    ids = [cid for cid, it in d["canais"].items() if it.get("seguindo")]
    key = _key()
    chans = {}
    for ch in _chunks(ids):
        r = http("GET", f"{API}/channels", params={"part": "snippet,statistics", "id": ",".join(ch), "key": key}).json()
        for c in r.get("items", []):
            chans[c["id"]] = c
    radar_registrar(chans)
    return len(chans)


# ------------------------------------------------------------------ concorrência no idioma de destino
REGIAO_DO_IDIOMA = {"pt": "BR", "en": "US", "es": "MX", "de": "DE", "pl": "PL", "cs": "CZ", "da": "DK", "no": "NO"}


def _termo_destino(titulo: str, nicho: str, lang: str) -> str:
    from .llm import chat, llm_available
    if llm_available():
        try:
            t = chat(f'YouTube video title: "{titulo}"\nWrite the 2 to 5 word YouTube search query someone would type in '
                     f'{IDIOMA_NOME.get(lang, lang)} to find videos about this exact topic. Reply with the query only.',
                     max_tokens=40).strip().strip('"').splitlines()[0]
            if t:
                return t
        except Exception:
            pass
    if nicho in NICHOS:
        return NICHOS[nicho].get(lang, NICHOS[nicho]["en"])[0]
    return titulo


def concorrencia(titulo: str, nicho: str, lang: str, quota=None) -> dict:
    """Quantos vídeos sobre o mesmo assunto já existem no idioma de destino (últimos 6 meses). ~101 unidades."""
    key = _key()
    termo = _termo_destino(titulo, nicho, lang)
    after = (datetime.now(timezone.utc) - timedelta(days=180)).strftime("%Y-%m-%dT%H:%M:%SZ")
    params = {"part": "snippet", "type": "video", "order": "viewCount", "publishedAfter": after, "maxResults": 25,
              "q": termo, "relevanceLanguage": lang, "key": key}
    if REGIAO_DO_IDIOMA.get(lang):
        params["regionCode"] = REGIAO_DO_IDIOMA[lang]
    r = http("GET", f"{API}/search", params=params).json()
    if quota is not None:
        quota[0] += 100
    ids = [it["id"]["videoId"] for it in r.get("items", []) if it.get("id", {}).get("videoId")]
    fortes, canais, exemplos = 0, set(), []
    if ids:
        v = http("GET", f"{API}/videos", params={"part": "snippet,statistics", "id": ",".join(ids), "key": key}).json()
        if quota is not None:
            quota[0] += 1
        for it in v.get("items", []):
            views = int(it.get("statistics", {}).get("viewCount", 0))
            if views >= 10_000:
                fortes += 1
                canais.add(it["snippet"]["channelId"])
                if len(exemplos) < 3:
                    exemplos.append(f'{it["snippet"]["title"]} ({views:,} views)'.replace(",", "."))
    nivel = "🟢 Livre" if len(canais) <= 1 else ("🟡 Pouca" if len(canais) <= 4 else "🔴 Já tem gente")
    return {"termo": termo, "videos_fortes": fortes, "canais": len(canais), "nivel": nivel, "exemplos": exemplos}


def _pontuacao_cedo(l: dict) -> float:
    """0–100: quanto o vídeo/canal parece um nicho NASCENDO agora."""
    p = min(32, math.log10(l["Views/hora"] + 1) * 9)                       # velocidade
    p += min(20, math.log10(l["Multiplicador (views ÷ inscritos)"] + 1) * 9)  # muito acima do tamanho do canal
    idade = l.get("1º vídeo há (dias)")
    if idade is None:
        idade = l["Idade do canal (dias)"]
    p += max(0, 1 - idade / 180) * 20                                        # canal jovem
    p += max(0, 1 - l["Vídeos no canal"] / 60) * 8                           # poucos vídeos = começo
    if l.get("Aceleração") is not None:
        p += max(0, min(3, math.log2(max(l["Aceleração"], 0.01)))) * 4       # vídeos novos rendendo mais
    p += min(8, (l.get("% views na última semana") or 0) / 10)               # explodiu agora
    return round(min(100, p), 1)


def _sinais(l: dict) -> str:
    s = []
    if l["Views/hora"] >= 500 or l["Multiplicador (views ÷ inscritos)"] >= 50:
        s.append("🔥 Explodindo")
    idade = l.get("1º vídeo há (dias)")
    if (idade is not None and idade <= 30) or l["Vídeos no canal"] <= 10:
        s.append("🌱 Bem no início")
    if (l.get("Aceleração") or 0) >= 2:
        s.append("🚀 Acelerando")
    if (l.get("Outlier (× mediana do canal)") or 0) >= 5:
        s.append("⭐ Fora da curva")
    if (l.get("Inscritos/dia (radar)") or 0) > 0:
        s.append("📡 Crescendo no radar")
    return " ".join(s)


FUNIL = {}


def analisar(vids: dict, chans: dict, nicho: str, max_inscritos: int, min_views: int,
             idade_canal_dias: int = 0, momento: dict = None, radar: dict = None) -> list:
    """Filtra e monta as linhas de resultado (um vídeo por linha)."""
    agora = datetime.now(timezone.utc)
    f = FUNIL
    momento = momento or {}
    linhas = []
    for v in vids.values():
        c = chans.get(v["snippet"]["channelId"])
        if not c:
            continue
        cs = c.get("statistics", {})
        if cs.get("hiddenSubscriberCount"):
            continue
        subs = int(cs.get("subscriberCount", 0))
        views = int(v.get("statistics", {}).get("viewCount", 0))
        f["videos"] = f.get("videos", 0) + 1
        if subs > max_inscritos:
            f["inscritos"] = f.get("inscritos", 0) + 1
            continue
        if views < min_views:
            f["views"] = f.get("views", 0) + 1
            continue
        idade_dias = (agora - _dt(c["snippet"]["publishedAt"])).days
        m = momento.get(c["id"], {})
        # idade "real": desde o 1º vídeo (muitos canais são antigos mas começaram a postar agora)
        idade_real = m.get("primeiro_video_dias")
        idade_filtro = idade_real if idade_real is not None else idade_dias
        if idade_canal_dias and idade_filtro > idade_canal_dias:
            f["idade"] = f.get("idade", 0) + 1
            continue
        horas = max(1.0, (agora - _dt(v["snippet"]["publishedAt"])).total_seconds() / 3600)
        mult = views / max(subs, 10)
        thumbs = v["snippet"].get("thumbnails", {})
        cr = crescimento((radar or {}).get(c["id"], {}).get("snaps", []))
        l = {
            "Sinais": "",
            "Chegou cedo": 0,
            "Nicho": nicho,
            "Thumb": (thumbs.get("medium") or thumbs.get("default") or {}).get("url", ""),
            "Vídeo": v["snippet"]["title"],
            "Canal": c["snippet"]["title"],
            "Inscritos": subs,
            "Views": views,
            "Views/hora": int(views / horas),
            "Views/dia": int(views / horas * 24),
            "Multiplicador (views ÷ inscritos)": round(mult, 1),
            "Postado há (horas)": int(horas),
            "Postado há (dias)": round(horas / 24, 1),
            "1º vídeo há (dias)": idade_real,
            "Idade do canal (dias)": idade_dias,
            "Vídeos no canal": int(cs.get("videoCount", 0)),
            "Vídeos por semana": m.get("videos_por_semana"),
            "Aceleração": m.get("aceleracao"),
            "Outlier (× mediana do canal)": round(views / max(m["mediana_views"], 1), 1) if m.get("mediana_views") else None,
            "% views na última semana": m.get("pct_semana"),
            "Inscritos/dia (radar)": cr[0] if cr else None,
            "Duração (min)": round(_iso_dur(v.get("contentDetails", {}).get("duration", "")) / 60, 1),
            "Concorrência no meu idioma": "",
            "Link vídeo": f"https://www.youtube.com/watch?v={v['id']}",
            "Link canal": f"https://www.youtube.com/channel/{c['id']}",
            "_cid": c["id"],
        }
        l["Chegou cedo"] = _pontuacao_cedo(l)
        l["Pontuação"] = l["Chegou cedo"]
        l["Sinais"] = _sinais(l)
        linhas.append(l)
    linhas.sort(key=lambda x: -x["Chegou cedo"])
    return linhas


def resumo_nichos(linhas: list) -> list:
    """Agrupa por nicho: quantos canais pequenos estão explodindo e quão forte."""
    g = {}
    for l in linhas:
        d = g.setdefault(l["Nicho"], {"canais": set(), "views": [], "mult": [], "cedo": [], "novos": set()})
        d["canais"].add(l["Canal"])
        d["views"].append(l["Views"])
        d["mult"].append(l["Multiplicador (views ÷ inscritos)"])
        d["cedo"].append(l.get("Chegou cedo", 0))
        if "🌱" in l.get("Sinais", ""):
            d["novos"].add(l["Canal"])
    out = []
    for n, d in g.items():
        vs = sorted(d["views"])
        top = sorted(d["cedo"], reverse=True)[:5]
        out.append({"Nicho": n, "Chegou cedo (média top 5)": round(sum(top) / len(top), 1),
                    "Canais bem no início": len(d["novos"]),
                    "Canais pequenos crescendo": len(d["canais"]), "Vídeos encontrados": len(vs),
                    "Mediana de views": vs[len(vs) // 2], "Maior views": vs[-1],
                    "Multiplicador médio": round(sum(d["mult"]) / len(d["mult"]), 1),
                    "Oportunidade": round(len(d["canais"]) * math.log10(vs[len(vs) // 2] + 1), 1)})
    return sorted(out, key=lambda x: -x["Chegou cedo (média top 5)"])


def rodar(nichos: dict, dias: int, regiao: str, duracao: str, max_inscritos: int, min_views: int,
          paginas: int = 1, idade_canal_dias: int = 0, log=print, momento: bool = True,
          idioma_destino: str = "", top_concorrencia: int = 0, classificar_ia: int = 40):
    """nichos = {nome_do_nicho: [termos de busca]}. Retorna (linhas, resumo, unidades_gastas)."""
    quota = [0]
    linhas = []
    FUNIL.clear()
    erros, buscas_ok = [], 0
    radar = _radar_ler()["canais"]
    vistos_canais, nicho_de = {}, {}
    for nome, termos in nichos.items():
        ids = []
        log(f"Buscando: {nome}...")
        for t in termos:
            try:
                ids += buscar(t, dias, regiao, duracao, paginas, quota)
                buscas_ok += 1
            except Exception as e:
                msg = erro_amigavel(e)
                log(f"Erro buscando '{t}': {msg}")
                erros.append(msg)
                if "cota" in msg or "chave" in msg.lower() or "ativada" in msg:
                    if linhas:
                        log("Parei a busca aqui e mostro o que já encontrei.")
                        break
                    raise RuntimeError(msg)
        if not ids:
            continue
        vids, chans = detalhes(ids, quota)
        # só lê o "momento" dos canais que passam nos filtros básicos (economiza cota)
        candidatos = {}
        for v in vids.values():
            c = chans.get(v["snippet"]["channelId"])
            if not c or c.get("statistics", {}).get("hiddenSubscriberCount"):
                continue
            if int(c["statistics"].get("subscriberCount", 0)) <= max_inscritos and \
                    int(v.get("statistics", {}).get("viewCount", 0)) >= min_views:
                candidatos[c["id"]] = c
        mom = {}
        if momento and candidatos:
            log(f"{nome}: lendo o momento de {len(candidatos)} canais (1º vídeo, aceleração)...")
            mom = momento_canais(candidatos, quota, log)
        novas = analisar(vids, chans, nome, max_inscritos, min_views, idade_canal_dias, mom, radar)
        log(f"{nome}: {len(novas)} vídeos de canais pequenos acima do filtro")
        try:
            from . import base_canais as BC
            ok = {l["_cid"] for l in novas}
            lang = idioma_da_regiao(regiao)
            BC.registrar({c: candidatos[c] for c in ok if c in candidatos}, mom,
                         {c: {"nicho": nome, "termo": ", ".join(termos[:2]), "lang": lang} for c in ok})
        except Exception as e:
            log(f"  não consegui guardar na base de canais: {e}")
        linhas += novas
        vistos_canais.update(candidatos)
        for cid in candidatos:
            nicho_de.setdefault(cid, nome)
    if not buscas_ok and erros:
        raise RuntimeError(erros[0])
    FUNIL["buscas"] = buscas_ok
    # remove vídeos repetidos entre nichos
    vistos, unicas = set(), []
    for l in sorted(linhas, key=lambda x: -x["Chegou cedo"]):
        if l["Link vídeo"] not in vistos:
            vistos.add(l["Link vídeo"])
            unicas.append(l)
    # concorrência no idioma de destino para os melhores (1 por canal)
    if idioma_destino and top_concorrencia:
        feitos = set()
        for l in unicas:
            if len(feitos) >= top_concorrencia:
                break
            if l["_cid"] in feitos:
                continue
            try:
                cc = concorrencia(l["Vídeo"], l["Nicho"], idioma_destino, quota)
                l["Concorrência no meu idioma"] = f'{cc["nivel"]} · {cc["canais"]} canais fortes · busca: "{cc["termo"]}"'
                if cc["nivel"].startswith("🟢"):
                    l["Chegou cedo"] = min(100, l["Chegou cedo"] + 10)
                elif cc["nivel"].startswith("🔴"):
                    l["Chegou cedo"] = max(0, l["Chegou cedo"] - 15)
                l["Pontuação"] = l["Chegou cedo"]
                log(f'Concorrência em {IDIOMA_NOME.get(idioma_destino, idioma_destino)}: "{l["Vídeo"][:50]}" → {cc["nivel"]}')
            except Exception as e:
                log(f"  não consegui checar a concorrência: {e}")
            feitos.add(l["_cid"])
        unicas.sort(key=lambda x: -x["Chegou cedo"])
    radar_registrar(vistos_canais, nicho_de)
    if classificar_ia:
        try:
            from . import base_canais as BC
            log("IA olhando as thumbs para estimar % faceless e nicho...")
            BC.classificar_ia(classificar_ia, log)
        except Exception as e:
            log(f"  classificação pela IA falhou: {e}")
    return unicas, resumo_nichos(unicas), quota[0]


def custo_estimado(n_termos: int, paginas: int, momento: bool = True, top_concorrencia: int = 0) -> int:
    base = n_termos * (paginas * 100 + 4)
    if momento:
        base += n_termos * 15 * 2      # ~15 canais candidatos por termo, ~2 unidades cada
    return base + top_concorrencia * 101


def analise_ia(linhas: list, resumo: list) -> str:
    from .llm import chat, llm_available
    if not llm_available():
        raise RuntimeError("Configure uma IA de texto em APIs e configurações.")
    top = "\n".join(f"- [{l['Nicho']}] \"{l['Vídeo']}\" | canal {l['Canal']} ({l['Inscritos']} inscritos, "
                    f"1º vídeo há {l.get('1º vídeo há (dias)', '?')} dias, {l['Vídeos no canal']} vídeos) | "
                    f"{l['Views']} views em {l['Postado há (dias)']} dias ({l.get('Views/hora', '?')}/hora) | "
                    f"{l['Duração (min)']} min | sinais: {l.get('Sinais', '')} | "
                    f"concorrência no idioma de destino: {l.get('Concorrência no meu idioma') or 'não checada'}"
                    for l in linhas[:40])
    res = "\n".join(f"- {r['Nicho']}: {r['Canais pequenos crescendo']} canais, mediana {r['Mediana de views']} views"
                    for r in resumo)
    p = ("Você é um estrategista de canais dark/faceless no YouTube. Abaixo estão vídeos recentes de canais com "
         f"poucos inscritos que estão performando muito acima do tamanho do canal.\n\nResumo por nicho:\n{res}\n\n"
         f"Vídeos:\n{top}\n\nEm português, responda de forma objetiva:\n"
         "O objetivo do usuário é CHEGAR CEDO: achar nichos que estão nascendo agora em um idioma para levar a "
         "outro idioma antes de todo mundo. Priorize canais com 1º vídeo recente, poucos vídeos, alta velocidade "
         "de views e pouca concorrência no idioma de destino.\n"
         "1. Os 3 nichos/subnichos que estão NASCENDO agora (ainda no início) e por quê; diga se a janela parece "
         "estar aberta ou já fechando.\n"
         "2. Padrões dos títulos que estão funcionando (estrutura, gatilhos, tamanho).\n"
         "3. Formato e duração que estão performando.\n"
         "4. 10 ideias de títulos de vídeos para entrar nesses nichos, escritas no MESMO idioma dos vídeos acima (com a tradução em português entre parênteses se não for português).\n"
         "Não invente números que não estão nos dados.")
    return chat(p, max_tokens=2500)
