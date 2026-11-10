"""Publicar no YouTube: conectar contas (OAuth), enviar vídeo, thumbnail e legenda, e agendar publicação.
Usa a YouTube Data API v3 oficial.
Rodar um envio direto:  python -m core.youtube_upload dados/youtube/envios/<id>.json"""
import json
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

from .config import DATA_DIR

PASTA = DATA_DIR / "youtube"
CONTAS = PASTA / "contas"
ENVIOS = PASTA / "envios"
CLIENT_SECRET = PASTA / "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.force-ssl"]
for _p in (PASTA, CONTAS, ENVIOS):
    _p.mkdir(parents=True, exist_ok=True)

CATEGORIAS = {"Educação": "27", "Entretenimento": "24", "Pessoas e blogs": "22", "Ciência e tecnologia": "28",
              "Filmes e animação": "1", "Música": "10", "Notícias e política": "25", "Viagens e eventos": "19",
              "Jogos": "20", "Esportes": "17", "Automóveis": "2", "Guias e estilo": "26", "Comédia": "23",
              "Animais": "15", "Organizações sem fins lucrativos": "29"}
IDIOMAS_VIDEO = {"Português": "pt-BR", "Português (Portugal)": "pt-PT", "Inglês": "en", "Espanhol": "es",
                 "Alemão": "de", "Polonês": "pl", "Tcheco": "cs", "Dinamarquês": "da", "Norueguês": "no"}
LINK_STUDIO_UPLOAD = "https://studio.youtube.com/channel/UC/videos/upload?d=ud"


def bibliotecas_ok() -> bool:
    try:
        import googleapiclient  # noqa: F401
        import google_auth_oauthlib  # noqa: F401
        return True
    except ImportError:
        return False


def _creds(conta_id: str):
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    arq = CONTAS / f"{conta_id}.json"
    dados = json.loads(arq.read_text(encoding="utf-8"))
    c = Credentials.from_authorized_user_info(dados["token"], SCOPES)
    if not c.valid and c.refresh_token:
        try:
            c.refresh(Request())
        except Exception as e:
            raise RuntimeError("A autorização desta conta expirou. Reconecte a conta em Publicar no YouTube. "
                               "(Dica: deixe o app do Google Cloud como 'Em produção' para não expirar a cada 7 dias.) "
                               f"Detalhe: {e}")
        dados["token"] = json.loads(c.to_json())
        arq.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    return c


def _yt(conta_id: str):
    from googleapiclient.discovery import build
    return build("youtube", "v3", credentials=_creds(conta_id), cache_discovery=False)


def conectar_conta() -> dict:
    """Abre o navegador para você entrar na conta Google e escolher o canal."""
    if not CLIENT_SECRET.exists():
        raise RuntimeError("Primeiro envie o arquivo client_secret.json (veja o passo a passo).")
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent select_account", open_browser=True,
                                  authorization_prompt_message="Abrindo o navegador para você autorizar o canal...",
                                  success_message="Pronto! Canal conectado ao AutoVideo Studio. Pode fechar esta aba.",
                                  timeout_seconds=300)
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    r = yt.channels().list(part="snippet,statistics", mine=True).execute()
    if not r.get("items"):
        raise RuntimeError("Essa conta Google não tem canal do YouTube.")
    ch = r["items"][0]
    conta = {"id": ch["id"], "nome": ch["snippet"]["title"],
             "foto": ch["snippet"].get("thumbnails", {}).get("default", {}).get("url", ""),
             "inscritos": ch.get("statistics", {}).get("subscriberCount", ""),
             "conectado_em": datetime.now().strftime("%d/%m/%Y %H:%M"),
             "token": json.loads(creds.to_json())}
    (CONTAS / f"{ch['id']}.json").write_text(json.dumps(conta, ensure_ascii=False, indent=1), encoding="utf-8")
    return conta


def listar_contas() -> list:
    out = []
    for f in sorted(CONTAS.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            d.pop("token", None)
            out.append(d)
        except Exception:
            pass
    return out


def remover_conta(conta_id: str):
    (CONTAS / f"{conta_id}.json").unlink(missing_ok=True)


# ------------------------------------------------------------------ envios
def criar_envio(dados: dict) -> Path:
    """Registra um envio e devolve o arquivo de controle (o envio roda em segundo plano)."""
    eid = time.strftime("%Y%m%d_%H%M%S")
    dados.update(id=eid, status="na fila", pct=0, log=[], criado=datetime.now().strftime("%d/%m/%Y %H:%M"))
    arq = ENVIOS / f"{eid}.json"
    arq.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    return arq


def listar_envios() -> list:
    out = []
    for f in sorted(ENVIOS.glob("*.json"), reverse=True):
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return out


def _salvar(arq: Path, d: dict):
    tmp = arq.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(arq)


def executar_envio(arq: Path):
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload
    arq = Path(arq)
    d = json.loads(arq.read_text(encoding="utf-8"))

    def log(m, **kw):
        d["log"] = (d.get("log") or [])[-40:] + [time.strftime("%H:%M:%S ") + m]
        d.update(kw)
        _salvar(arq, d)

    try:
        log("Conectando ao YouTube...", status="enviando")
        yt = _yt(d["conta_id"])
        status = {"privacyStatus": d["privacidade"], "selfDeclaredMadeForKids": bool(d.get("para_criancas", False)),
                  "embeddable": True}
        if d.get("publicar_em"):
            status["privacyStatus"] = "private"
            status["publishAt"] = d["publicar_em"]  # ISO em UTC
        if d.get("conteudo_sintetico") is not None:
            status["containsSyntheticMedia"] = bool(d["conteudo_sintetico"])
        tags = [t for t in d.get("tags", []) if t.strip()]
        body = {"snippet": {"title": d["titulo"][:100], "description": d.get("descricao", "")[:5000],
                            "tags": tags or None, "categoryId": d.get("categoria", "27"),
                            "defaultLanguage": d.get("idioma"), "defaultAudioLanguage": d.get("idioma")},
                "status": status}
        body["snippet"] = {k: v for k, v in body["snippet"].items() if v}
        media = MediaFileUpload(d["video"], chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")

        def inserir(b):
            req = yt.videos().insert(part="snippet,status", body=b, media_body=media,
                                     notifySubscribers=bool(d.get("notificar", True)))
            resp, ultimo = None, -1
            while resp is None:
                st, resp = req.next_chunk(num_retries=5)
                if st:
                    p = int(st.progress() * 100)
                    if p != ultimo:
                        log(f"Enviando vídeo: {p}%", pct=p * 0.9)
                        ultimo = p
            return resp

        try:
            resp = inserir(body)
        except HttpError as e:
            if "containsSyntheticMedia" in str(e) and "containsSyntheticMedia" in body["status"]:
                body["status"].pop("containsSyntheticMedia")
                log("Campo de conteúdo sintético não aceito; enviando sem ele.")
                media = MediaFileUpload(d["video"], chunksize=8 * 1024 * 1024, resumable=True, mimetype="video/mp4")
                resp = inserir(body)
            else:
                raise
        vid = resp["id"]
        log(f"Vídeo enviado: https://youtu.be/{vid}", video_id=vid, link=f"https://youtu.be/{vid}", pct=92)

        if d.get("thumbnail") and Path(d["thumbnail"]).exists():
            try:
                yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(d["thumbnail"], mimetype="image/jpeg")).execute()
                log("Thumbnail aplicada ✔", pct=96)
            except HttpError as e:
                log("Thumbnail não aplicada: o canal precisa estar verificado por telefone para usar thumbnail "
                    f"personalizada (youtube.com/verify). Detalhe: {str(e)[:160]}")
        if d.get("legenda") and Path(d["legenda"]).exists():
            try:
                yt.captions().insert(part="snippet", body={"snippet": {"videoId": vid, "language": d.get("idioma") or "pt-BR",
                                                                          "name": "", "isDraft": False}},
                                     media_body=MediaFileUpload(d["legenda"], mimetype="application/octet-stream")).execute()
                log("Legenda .srt enviada ✔", pct=99)
            except HttpError as e:
                log(f"Legenda não enviada: {str(e)[:160]}")
        fim = "Agendado ✔" if d.get("publicar_em") else "Publicado ✔"
        log(fim, status="agendado" if d.get("publicar_em") else "enviado", pct=100)
    except Exception as e:
        msg = str(e)
        if "quotaExceeded" in msg or "uploadLimitExceeded" in msg:
            msg = "Limite diário de envios/cota da API atingido. Tente de novo amanhã. " + msg[:200]
        log("ERRO: " + msg[:600], status="erro")
        print(traceback.format_exc(), flush=True)


def iso_utc(data_local: datetime) -> str:
    """Converte a data/hora local escolhida para o formato que o YouTube exige (UTC)."""
    if data_local.tzinfo is None:
        data_local = data_local.astimezone()
    return data_local.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    executar_envio(Path(sys.argv[1]))
