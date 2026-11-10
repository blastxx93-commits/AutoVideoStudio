"""Funções auxiliares: FFmpeg, downloads, log e progresso."""
import json
import re
import subprocess
import threading
import time
from pathlib import Path

import requests

from .config import ffmpeg_bin

CREATE_NO_WINDOW = 0x08000000 if __import__("os").name == "nt" else 0


class Cancelado(Exception):
    pass


class JobLogger:
    """Escreve o progresso num arquivo JSON que a interface lê."""

    def __init__(self, job_dir: Path):
        self.path = Path(job_dir) / "progresso.json"
        self._lock = threading.Lock()
        import os
        self.state = {"etapa": "Iniciando", "pct": 0, "log": [], "status": "rodando", "saida": None, "pid": os.getpid(),
                      "inicio": time.time(), "fim": None}
        self._flush()

    def _flush(self):
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.state, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    # ---------- pausar / retomar / cancelar ----------
    def _controle(self) -> dict:
        p = self.path.parent / "controle.json"
        try:
            return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
        except Exception:
            return {}

    def checkpoint(self):
        """Chamado entre etapas e entre cenas: espera enquanto estiver pausado; para se cancelado."""
        c = self._controle()
        if c.get("cancelar"):
            raise Cancelado("Cancelado por você")
        if c.get("pausado"):
            with self._lock:  # só uma thread anuncia a pausa; as outras esperam aqui
                self._esperar_pausa()

    def _esperar_pausa(self):
        c = self._controle()
        if c.get("pausado"):
            etapa = self.state["etapa"]
            self.state.update(status="pausado")
            self.info("⏸️ Pausado")
            while True:
                time.sleep(1)
                c = self._controle()
                if c.get("cancelar"):
                    raise Cancelado("Cancelado por você")
                if not c.get("pausado"):
                    break
            self.state.update(status="rodando", etapa=etapa)
            self.info("▶️ Retomado")

    def step(self, etapa: str, pct: float):
        self.checkpoint()
        self.state["etapa"] = etapa
        self.state["pct"] = round(pct, 1)
        self.info(f"▶ {etapa}")

    def info(self, msg: str):
        line = time.strftime("%H:%M:%S ") + msg
        try:
            print(line, flush=True)
        except Exception:  # janela/arquivo sem suporte a emoji no Windows: o log em JSON continua
            try:
                print(line.encode("ascii", "replace").decode(), flush=True)
            except Exception:
                pass
        self.state["log"].append(line)
        self.state["log"] = self.state["log"][-400:]
        self._flush()

    def done(self, saida: str):
        self.state.update(status="concluido", pct=100, etapa="Pronto!", saida=saida, fim=time.time())
        self._flush()

    def aguardando(self, video: str):
        self.state.update(status="aguardando", pct=100, etapa="Pronto! Assista e aprove para exportar", saida=video,
                          fim=time.time())
        self.info("Vídeo pronto — aguardando sua aprovação para exportar.")
        self._flush()

    def cancel(self):
        self.state.update(status="cancelado", etapa="Cancelado — dá para continuar de onde parou", fim=time.time())
        self.info("⏹️ Cancelado")
        self._flush()

    def fail(self, err: str):
        self.state.update(status="erro", etapa="Erro: " + err[:300], fim=time.time())
        self.info("ERRO: " + err)
        self._flush()


def processo_vivo(pid) -> bool:
    """Confere se o processo de geração ainda está rodando."""
    import os
    if not pid:
        return True
    try:
        if os.name == "nt":
            out = subprocess.run(["tasklist", "/FI", f"PID eq {int(pid)}", "/NH"], capture_output=True, text=True,
                                 creationflags=CREATE_NO_WINDOW).stdout
            return str(int(pid)) in out
        os.kill(int(pid), 0)
        return True
    except Exception:
        return False


def env_utf8():
    import os
    e = dict(os.environ)
    e["PYTHONIOENCODING"] = "utf-8"
    e["PYTHONUTF8"] = "1"
    return e


def run(cmd, cwd=None, timeout=None):
    """Roda um comando e levanta erro com a saída do FFmpeg se falhar."""
    cmd = [str(c) for c in cmd]
    if cmd[0] == "ffmpeg":
        cmd[0] = ffmpeg_bin("ffmpeg")
    elif cmd[0] == "ffprobe":
        cmd[0] = ffmpeg_bin("ffprobe")
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, creationflags=CREATE_NO_WINDOW)
    if p.returncode != 0:
        tail = (p.stderr or "")[-1500:]
        raise RuntimeError(f"Comando falhou: {' '.join(cmd[:6])}...\n{tail}")
    return p


def duration(path) -> float:
    p = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)])
    try:
        return float(p.stdout.strip())
    except ValueError:
        return 0.0


def has_video_stream(path) -> bool:
    try:
        p = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=codec_name",
                 "-of", "csv=p=0", str(path)])
        return bool(p.stdout.strip())
    except Exception:
        return False


def http(method, url, retries=3, timeout=120, **kw):
    last = None
    for i in range(retries):
        try:
            r = requests.request(method, url, timeout=timeout, **kw)
            if r.status_code == 429 or r.status_code >= 500:
                last = RuntimeError(f"HTTP {r.status_code}: {r.text[:300]}")
                time.sleep(3 * (i + 1))
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"HTTP {r.status_code} em {url.split('?')[0]}: {r.text[:400]}")
            return r
        except requests.RequestException as e:
            last = e
            time.sleep(2 * (i + 1))
    raise RuntimeError(f"Falha de conexão: {last}")


def download(url, dest: Path, headers=None) -> Path:
    r = http("GET", url, headers=headers or {"User-Agent": "AutoVideoStudio/1.0"}, stream=True, timeout=300)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as f:
        for chunk in r.iter_content(1 << 16):
            f.write(chunk)
    return dest


def safe_name(text: str, maxlen=60) -> str:
    t = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip()
    t = re.sub(r"\s+", "_", t)
    return (t[:maxlen] or "video").strip("_")


def extract_json(text: str):
    """Extrai o primeiro JSON (lista ou objeto) de uma resposta de IA."""
    text = text.strip()
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    for open_c, close_c in (("[", "]"), ("{", "}")):
        a, b = text.find(open_c), text.rfind(close_c)
        if a != -1 and b > a:
            try:
                return json.loads(text[a:b + 1])
            except Exception:
                continue
    raise ValueError("A IA não devolveu um JSON válido.")
