"""Trilha sonora: biblioteca local por tema (músicas baixadas da Biblioteca de Áudio do YouTube)."""
import json
import random
import re
import shutil
from pathlib import Path

from .config import MUSIC_DIR
from .utils import duration

# tema → (pasta, ícone, filtro de "Humor" sugerido na Biblioteca de Áudio do YouTube)
TEMAS = {
    "Som ambiente": ("ambiente", "🌫️", "Calmo"),
    "Relaxante": ("relaxante", "🌿", "Calmo"),
    "Animado": ("animado", "⚡", "Alegre / Brilhante"),
    "Reflexivo": ("reflexivo", "💭", "Triste / Calmo"),
    "Dramático": ("dramatico", "🎭", "Dramático"),
    "Suspense / Dark": ("suspense", "🌑", "Sombrio"),
    "Épico": ("epico", "⚔️", "Dramático / Inspirador"),
    "Misterioso": ("misterioso", "🕵️", "Sombrio / Calmo"),
    "Inspirador": ("inspirador", "🌅", "Inspirador"),
    "Triste": ("triste", "🌧️", "Triste"),
    "Tensão / Ação": ("tensao", "🔥", "Irritado / Dramático"),
}
EXT = (".mp3", ".wav", ".m4a", ".ogg", ".flac")
LINK_BIBLIOTECA = "https://studio.youtube.com/channel/UC/music"


def pasta(tema: str) -> Path:
    p = MUSIC_DIR / TEMAS[tema][0]
    p.mkdir(parents=True, exist_ok=True)
    return p


def _meta_path(tema):
    return pasta(tema) / "_creditos.json"


def creditos(tema) -> dict:
    p = _meta_path(tema)
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        return {}


def listar(tema: str) -> list:
    return sorted(f for f in pasta(tema).iterdir() if f.suffix.lower() in EXT)


def contagem() -> dict:
    return {t: len(listar(t)) for t in TEMAS}


def importar(nome: str, dados: bytes, tema: str, atribuicao: str = "") -> Path:
    limpo = re.sub(r"[^\w\-. ()]", "_", nome).strip() or "musica.mp3"
    dest = pasta(tema) / limpo
    dest.write_bytes(dados)
    if atribuicao.strip():
        m = creditos(tema)
        m[dest.name] = atribuicao.strip()
        _meta_path(tema).write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")
    return dest


def importar_pasta(origem: str, tema: str) -> int:
    n = 0
    for f in Path(origem.strip().strip('"')).iterdir():
        if f.suffix.lower() in EXT:
            shutil.copy2(f, pasta(tema) / f.name)
            n += 1
    return n


def remover(tema: str, arquivo: str):
    (pasta(tema) / arquivo).unlink(missing_ok=True)
    m = creditos(tema)
    if m.pop(arquivo, None) is not None:
        _meta_path(tema).write_text(json.dumps(m, ensure_ascii=False, indent=1), encoding="utf-8")


PALAVRAS = {
    "Suspense / Dark": "morte assassin crime mistério sombra medo terror máfia sangue polícia desaparec murder dark",
    "Épico": "guerra batalha império rei deus deuses lenda herói conquista exército war empire god",
    "Dramático": "tragédia traição queda destino perdeu luta sobreviv trag",
    "Relaxante": "natureza calma paz relax dormir estudar",
    "Animado": "incrível curiosidade divertido rápido top fatos",
    "Inspirador": "sonho venceu superou sucesso conquistou esperança",
    "Triste": "luto perda saudade lágrimas morreu sozinho",
}


def tema_automatico(titulo: str, roteiro: str, log=print) -> str:
    """Escolhe o clima da trilha pelo roteiro (IA se houver; senão por palavras-chave)."""
    from .llm import chat, llm_available
    disponiveis = [t for t, n in contagem().items() if n > 0] or list(TEMAS)
    if llm_available():
        try:
            r = chat(f'Video title: "{titulo}"\nScript: "{roteiro[:2500]}"\n'
                     f"Choose the best background music mood for this video from EXACTLY one of: {disponiveis}. "
                     "Answer only with the option text.", max_tokens=30).strip().strip('"')
            for t in disponiveis:
                if t.lower() in r.lower():
                    return t
        except Exception as e:
            log(f"  IA não escolheu a trilha: {e}")
    txt = (titulo + " " + roteiro).lower()
    pont = {t: sum(txt.count(w) for w in ws.split()) for t, ws in PALAVRAS.items() if t in disponiveis}
    if pont and max(pont.values()) > 0:
        return max(pont, key=pont.get)
    return "Dramático" if "Dramático" in disponiveis else disponiveis[0]


def _cobrir(fs: list, total: float) -> list:
    """Repete a lista (em ordem) até cobrir a duração do vídeo."""
    ordem, acc, i = [], 0.0, 0
    while fs and acc < total and i < 200:
        f = fs[i % len(fs)]
        ordem.append(f)
        acc += max(5.0, duration(f) - 2.5)
        i += 1
    return ordem


def selecionar(job: dict, total: float, log=print):
    """Retorna (lista de arquivos na ordem de tocar, tema, créditos das faixas usadas)."""
    modo = job.get("trilha_modo", "Automático")
    if modo == "Sem música":
        return [], None, []
    if modo == "Arquivo ou pasta":
        p = Path((job.get("musica") or "").strip().strip('"'))
        fs = [p] if p.is_file() else sorted(f for f in p.iterdir() if f.suffix.lower() in EXT) if p.is_dir() else []
        random.shuffle(fs)
        return _cobrir(fs, total), None, []
    tema = tema_automatico(job["titulo"], job["roteiro"], log) if modo == "Automático" else job.get("trilha_tema", "Dramático")
    fs = listar(tema)
    if not fs:
        log(f"  nenhuma música no tema '{tema}' — adicione na Biblioteca de trilhas. Vídeo sai sem música.")
        return [], tema, []
    random.shuffle(fs)
    ordem = _cobrir(fs, total)
    cred = creditos(tema)
    usados = []
    for f in dict.fromkeys(ordem):
        c = cred.get(f.name)
        if c and c not in usados:
            usados.append(c)
    return ordem, tema, usados
