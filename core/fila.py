"""Fila de vídeos: produz vários vídeos em sequência, sozinho (ex.: durante a madrugada).
Cada item pode ser: roteiro pronto, tema (a IA escreve o roteiro) ou link (adapta de outro idioma).
Rodar o trabalhador direto:  python -m core.fila"""
import json
import os
import sys
import time
import traceback
from pathlib import Path

from .config import DATA_DIR, JOBS_DIR
from .utils import safe_name, processo_vivo

ARQ = DATA_DIR / "fila.json"
LOCK = DATA_DIR / "fila.lock"
CTRL = DATA_DIR / "fila_controle.json"


def _ler() -> list:
    try:
        return json.loads(ARQ.read_text(encoding="utf-8")) if ARQ.exists() else []
    except Exception:
        return []


def _gravar(itens: list):
    tmp = ARQ.with_suffix(".tmp")
    tmp.write_text(json.dumps(itens, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(ARQ)


def listar() -> list:
    return _ler()


def adicionar(job: dict, tipo: str = "pronto", nome: str = "", tema: str = "", link: str = "",
              exportar_auto: bool = False) -> dict:
    itens = _ler()
    item = {"id": f"{time.strftime('%Y%m%d%H%M%S')}{len(itens):03d}", "tipo": tipo,
            "nome": nome or job.get("titulo") or tema or link, "tema": tema, "link": link, "job": dict(job),
            "exportar_auto": exportar_auto, "status": "na fila", "criado": time.strftime("%d/%m %H:%M"),
            "job_dir": None, "erro": None}
    itens.append(item)
    _gravar(itens)
    return item


def remover(iid: str):
    _gravar([i for i in _ler() if i["id"] != iid])


def mover(iid: str, delta: int):
    itens = _ler()
    idx = next((k for k, i in enumerate(itens) if i["id"] == iid), None)
    if idx is None:
        return
    novo = max(0, min(len(itens) - 1, idx + delta))
    itens.insert(novo, itens.pop(idx))
    _gravar(itens)


def repetir(iid: str):
    itens = _ler()
    for i in itens:
        if i["id"] == iid:
            i.update(status="na fila", erro=None)
    _gravar(itens)


def limpar_concluidos():
    _gravar([i for i in _ler() if i["status"] not in ("pronto", "exportado")])


def _atualizar(iid: str, **kw):
    itens = _ler()
    for i in itens:
        if i["id"] == iid:
            i.update(kw)
    _gravar(itens)


# ------------------------------------------------------------------ trabalhador
def trabalhador_ativo() -> bool:
    try:
        pid = int(LOCK.read_text())
        return processo_vivo(pid)
    except Exception:
        return False


def pedir_pausa(valor: bool = True):
    CTRL.write_text(json.dumps({"pausar": valor}), encoding="utf-8")


def pausa_pedida() -> bool:
    try:
        return json.loads(CTRL.read_text(encoding="utf-8")).get("pausar", False)
    except Exception:
        return False


def iniciar():
    """Liga o trabalhador em segundo plano (se ainda não estiver rodando)."""
    import subprocess
    from .config import APP_DIR
    from .utils import env_utf8
    pedir_pausa(False)
    if trabalhador_ativo():
        return False
    flags = 0x08000000 if os.name == "nt" else 0
    log = open(DATA_DIR / "fila_log.txt", "a", encoding="utf-8")
    subprocess.Popen([sys.executable, "-m", "core.fila"], cwd=str(APP_DIR), stdout=log, stderr=subprocess.STDOUT,
                     creationflags=flags, env=env_utf8())
    return True


def _preparar(item: dict, log) -> dict:
    """Completa o job do item: escreve o roteiro (tema) ou adapta (link)."""
    job = dict(item["job"])
    skills = job.get("skills_ativas", [])
    if item["tipo"] == "tema":
        from . import roteiro as RT
        r = RT.gerar({"tema": item["tema"], "titulo": "", "idioma": job.get("gr_idioma", "Português (Brasil)"),
                      "minutos": job.get("gr_minutos", 10), "tom": job.get("gr_tom", ""), "publico": job.get("gr_publico", ""),
                      "referencia": "", "extras": job.get("gr_extras", ""), "pesquisa": job.get("gr_pesquisa", False),
                      "skills": skills}, log=log)
        job["titulo"] = (r["titulos"] or [item["tema"]])[0].lstrip("⭐ ").strip()
        job["roteiro"] = r["roteiro"]
    elif item["tipo"] == "link":
        from . import adaptar as AD
        info = AD.info_video(item["link"])
        tr = AD.transcricao(item["link"])
        r = AD.adaptar(tr["texto"], job.get("ad_idioma", "English"), job.get("ad_angulo"),
                       job.get("ad_minutos") or None, info.get("titulo", ""), skills, job.get("ad_extras", ""),
                       job.get("gr_pesquisa", False), log=log)
        job["titulo"] = (r["titulos"] or [info.get("titulo", "Vídeo")])[0].lstrip("⭐ ").strip()
        job["roteiro"] = r["roteiro"]
    if not job.get("titulo") or len(job.get("roteiro", "").split()) < 5:
        raise RuntimeError("Item sem título ou roteiro.")
    return job


def rodar():
    from . import pipeline
    LOCK.write_text(str(os.getpid()))
    try:
        while True:
            if pausa_pedida():
                print("Fila pausada.", flush=True)
                break
            itens = _ler()
            item = next((i for i in itens if i["status"] == "na fila"), None)
            if not item:
                print("Fila vazia. Fim.", flush=True)
                break
            iid = item["id"]
            try:
                _atualizar(iid, status="preparando roteiro" if item["tipo"] != "pronto" else "gerando")
                job = _preparar(item, lambda m: print(m, flush=True))
                job_dir = JOBS_DIR / (time.strftime("%Y%m%d_%H%M%S_") + safe_name(job["titulo"], 40))
                job_dir.mkdir(parents=True, exist_ok=True)
                if item.get("exportar_auto"):
                    job["revisar_antes"] = False
                (job_dir / "trabalho.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
                _atualizar(iid, status="gerando", job_dir=str(job_dir), nome=job["titulo"])
                pipeline.run_job(job_dir)
                pr = json.loads((job_dir / "progresso.json").read_text(encoding="utf-8"))
                st = {"aguardando": "pronto", "concluido": "exportado", "cancelado": "cancelado"}.get(pr["status"], "erro")
                _atualizar(iid, status=st, erro=pr["etapa"] if st == "erro" else None)
            except Exception as e:
                print(traceback.format_exc(), flush=True)
                _atualizar(iid, status="erro", erro=str(e)[:400])
    finally:
        try:
            LOCK.unlink()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    rodar()
