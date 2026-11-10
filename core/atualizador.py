"""Atualização do programa por dentro da própria ferramenta.

Duas fontes:
1. Online (GitHub): o programa confere se há versão nova e instala com um clique.
2. Arquivo .zip: você escolhe o zip da nova versão e ele instala sozinho (sem extrair nada à mão).

Sempre: faz backup da versão atual, nunca mexe em dados/ (chaves, projetos) nem em .venv/,
instala bibliotecas novas se o requirements.txt mudar e reinicia o programa.
"""
import io
import json
import os
import re
import subprocess
import sys
import threading
import time
import zipfile
from pathlib import Path

import requests

from .config import DATA_DIR, load_settings
from .versao import VERSAO

RAIZ = Path(__file__).resolve().parent.parent
BACKUPS = DATA_DIR / "backups"
FLAG_REINICIAR = DATA_DIR / "reiniciar.flag"
IGNORAR = ("dados/", ".venv/", "venv/", ".git/", "__pycache__")
NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def _v(t: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", t or "0")[:3]) or (0,)


def mais_nova(a: str, b: str) -> bool:
    """True se a versão a é mais nova que b."""
    return _v(a) > _v(b)


def _ignorar(rel: str) -> bool:
    rel = rel.replace("\\", "/")
    return (not rel or rel.endswith("/") or any(rel.startswith(p) or f"/{p}" in f"/{rel}" for p in IGNORAR)
            or rel.endswith(".pyc"))


# ------------------------------------------------------------------ fonte online (GitHub)
def _gh(cfg=None):
    s = cfg or load_settings()
    repo = (s.get("atualizacao_repo") or "").strip().strip("/")
    repo = re.sub(r"^https?://github\.com/", "", repo).removesuffix(".git")
    h = {"Accept": "application/vnd.github.raw", "User-Agent": "AutoVideoStudio-updater"}
    if (s.get("atualizacao_token") or "").strip():
        h["Authorization"] = f"Bearer {s['atualizacao_token'].strip()}"
    return repo, (s.get("atualizacao_ramo") or "main").strip(), h


def verificar_online(timeout: float = 6) -> dict:
    """Retorna {"versao", "novidades", "nova": bool} ou {"erro"}."""
    repo, ramo, h = _gh()
    if not repo:
        return {"erro": "sem_repo"}
    try:
        r = requests.get(f"https://api.github.com/repos/{repo}/contents/core/versao.py", params={"ref": ramo},
                         headers=h, timeout=timeout)
        if r.status_code == 404:
            return {"erro": "Não achei o repositório (ou ele é privado e falta o token de acesso)."}
        if r.status_code in (401, 403):
            return {"erro": "O GitHub recusou o acesso. Confira o token de atualização."}
        r.raise_for_status()
        txt = r.text
        m = re.search(r'VERSAO\s*=\s*["\']([^"\']+)', txt)
        ver = m.group(1) if m else "0"
        ns = {}
        try:
            exec(compile(txt, "versao_remota", "exec"), {}, ns)  # arquivo só com constantes
        except Exception:
            pass
        nov = (ns.get("NOVIDADES") or {}).get(ver, [])
        return {"versao": ver, "novidades": nov, "nova": mais_nova(ver, VERSAO)}
    except requests.RequestException as e:
        return {"erro": f"Sem conexão com o GitHub ({str(e)[:80]})."}


def baixar_online(log=print) -> bytes:
    repo, ramo, h = _gh()
    h = dict(h, Accept="application/vnd.github+json")
    log("Baixando a nova versão...")
    r = requests.get(f"https://api.github.com/repos/{repo}/zipball/{ramo}", headers=h, timeout=180)
    r.raise_for_status()
    return r.content


# ------------------------------------------------------------------ instalação a partir de um zip
def _prefixo(z: zipfile.ZipFile) -> str:
    """Pasta dentro do zip onde está o app.py (o zip pode ter uma pasta por cima)."""
    cands = [n for n in z.namelist() if n.replace("\\", "/").endswith("app.py")
             and "/dados/" not in "/" + n and "__MACOSX" not in n]
    if not cands:
        raise RuntimeError("Esse arquivo não parece ser o AutoVideo Studio (não achei o app.py dentro dele).")
    p = min(cands, key=len).replace("\\", "/")[:-len("app.py")]
    if f"{p}core/pipeline.py" not in {n.replace("\\", "/") for n in z.namelist()}:
        raise RuntimeError("Esse zip está incompleto (falta a pasta core).")
    return p


def versao_do_zip(dados: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        p = _prefixo(z)
        try:
            txt = z.read(f"{p}core/versao.py").decode("utf-8", "ignore")
            m = re.search(r'VERSAO\s*=\s*["\']([^"\']+)', txt)
            return m.group(1) if m else "?"
        except KeyError:
            return "?"


def backup(log=print) -> Path:
    BACKUPS.mkdir(parents=True, exist_ok=True)
    alvo = BACKUPS / f"versao_{VERSAO}_{time.strftime('%Y%m%d_%H%M%S')}.zip"
    log(f"Guardando cópia da versão atual ({VERSAO})...")
    with zipfile.ZipFile(alvo, "w", zipfile.ZIP_DEFLATED) as z:
        for f in RAIZ.rglob("*"):
            rel = f.relative_to(RAIZ).as_posix()
            if f.is_file() and not _ignorar(rel):
                z.write(f, f"AutoVideoStudio/{rel}")
    antigos = sorted(BACKUPS.glob("versao_*.zip"), key=lambda p: p.stat().st_mtime)
    for velho in antigos[:-3]:          # guarda só os 3 últimos
        velho.unlink(missing_ok=True)
    return alvo


def instalar_zip(dados: bytes, log=print, fazer_backup: bool = True) -> dict:
    """Instala a versão contida no zip por cima da atual. Retorna {"de", "para", "bibliotecas"}."""
    with zipfile.ZipFile(io.BytesIO(dados)) as z:
        p = _prefixo(z)
        nova = versao_do_zip(dados)
        req_antes = (RAIZ / "requirements.txt").read_text(encoding="utf-8") if (RAIZ / "requirements.txt").exists() else ""
        if fazer_backup:
            backup(log)
        log(f"Instalando a versão {nova}...")
        n = 0
        for info in z.infolist():
            nome = info.filename.replace("\\", "/")
            if not nome.startswith(p) or info.is_dir():
                continue
            rel = nome[len(p):]
            if _ignorar(rel) or ".." in rel.split("/"):
                continue
            destino = RAIZ / rel
            destino.parent.mkdir(parents=True, exist_ok=True)
            tmp = destino.with_name(destino.name + ".novo")
            tmp.write_bytes(z.read(info))
            os.replace(tmp, destino)
            n += 1
        log(f"{n} arquivos atualizados.")
    req_depois = (RAIZ / "requirements.txt").read_text(encoding="utf-8") if (RAIZ / "requirements.txt").exists() else ""
    bibliotecas = False
    if req_depois.strip() != req_antes.strip():
        log("Instalando bibliotecas novas (pode levar 1 ou 2 minutos)...")
        py = Path(sys.executable)
        if py.name.lower() == "pythonw.exe" and (py.parent / "python.exe").exists():
            py = py.parent / "python.exe"
        r = subprocess.run([str(py), "-m", "pip", "install", "-q", "-r", str(RAIZ / "requirements.txt")],
                           capture_output=True, text=True, creationflags=NO_WINDOW)
        bibliotecas = r.returncode == 0
        if r.returncode != 0:
            log("Aviso: algumas bibliotecas não instalaram. Se algo não abrir, rode o INSTALAR.bat de novo.")
    hist = DATA_DIR / "atualizacoes.json"
    try:
        h = json.loads(hist.read_text(encoding="utf-8"))
    except Exception:
        h = []
    h.append({"de": VERSAO, "para": nova, "quando": time.strftime("%d/%m/%Y %H:%M")})
    hist.write_text(json.dumps(h[-30:], ensure_ascii=False, indent=1), encoding="utf-8")
    return {"de": VERSAO, "para": nova, "bibliotecas": bibliotecas}


def ultimo_backup():
    b = sorted(BACKUPS.glob("versao_*.zip"), key=lambda p: p.stat().st_mtime) if BACKUPS.exists() else []
    return b[-1] if b else None


def voltar_versao(log=print) -> dict:
    b = ultimo_backup()
    if not b:
        raise RuntimeError("Não há versão anterior guardada.")
    r = instalar_zip(b.read_bytes(), log, fazer_backup=False)
    b.unlink(missing_ok=True)
    return r


# ------------------------------------------------------------------ reinício
def pode_reiniciar_sozinho() -> bool:
    """O lançador da janela (AutoVideoStudio.pyw) sabe reabrir o programa depois de atualizar."""
    return os.environ.get("AVS_LAUNCHER") == "1"


def reiniciar(atraso: float = 1.5):
    FLAG_REINICIAR.parent.mkdir(parents=True, exist_ok=True)
    FLAG_REINICIAR.write_text(str(time.time()), encoding="utf-8")
    threading.Timer(atraso, lambda: os._exit(0)).start()
