"""Roteirista: gera roteiros narrados com o Claude (ou outra IA configurada) seguindo as suas skills."""
import io
import json
import re
import time
import zipfile
from pathlib import Path

from .config import SKILLS_DIR, DATA_DIR, load_settings
from .llm import chat, llm_available

HIST = DATA_DIR / "roteiros"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)

IDIOMAS = {"Português (Brasil)": 150, "Português (Portugal)": 145, "English": 150, "Español": 155,
           "Deutsch": 130, "Polski": 130, "Čeština": 130, "Dansk": 140, "Norsk": 140}  # palavras por minuto narrado
TONS = ["Documentário dark / mistério", "True crime", "Máfia / crime organizado", "Mitologia épica",
        "História", "Sobrevivência real", "Curiosidades", "Biografia", "Carros / máquinas", "Finanças / negócios",
        "Motivacional / reflexivo", "Infantil / leve"]


# ------------------------------------------------------------------ skills
def _sem_frontmatter(txt: str):
    meta = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", txt, re.S)
    if m:
        for linha in m.group(1).splitlines():
            if ":" in linha:
                k, v = linha.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
        txt = txt[m.end():]
    return meta, txt.strip()


def listar_skills() -> list:
    out = []
    for d in sorted(SKILLS_DIR.iterdir()):
        sk = d / "SKILL.md" if d.is_dir() else None
        if sk and sk.exists():
            meta, _ = _sem_frontmatter(sk.read_text(encoding="utf-8"))
            out.append({"id": d.name, "nome": meta.get("name", d.name), "descricao": meta.get("description", "")})
    return out


def conteudo_skill(sid: str) -> str:
    d = SKILLS_DIR / sid
    partes = []
    sk = d / "SKILL.md"
    if sk.exists():
        meta, corpo = _sem_frontmatter(sk.read_text(encoding="utf-8"))
        partes.append(f"## Skill: {meta.get('name', sid)}\n{corpo}")
    for extra in sorted(d.rglob("*.md")):  # arquivos de referência da skill
        if extra.name != "SKILL.md":
            partes.append(f"### Referência: {extra.name}\n{extra.read_text(encoding='utf-8')[:20000]}")
    return "\n\n".join(partes)


def importar_skill(nome_arquivo: str, dados: bytes) -> str:
    """Aceita um SKILL.md / .md solto ou um .zip de skill (como o exportado do Claude)."""
    base = re.sub(r"[^\w\-]", "-", Path(nome_arquivo).stem.lower()).strip("-") or f"skill-{int(time.time())}"
    if nome_arquivo.lower().endswith(".zip"):
        z = zipfile.ZipFile(io.BytesIO(dados))
        mds = [n for n in z.namelist() if n.lower().endswith(".md")]
        if not any(n.endswith("SKILL.md") for n in mds):
            raise ValueError("O .zip não tem um SKILL.md.")
        principal = next(n for n in mds if n.endswith("SKILL.md"))
        meta, _ = _sem_frontmatter(z.read(principal).decode("utf-8", errors="replace"))
        sid = re.sub(r"[^\w\-]", "-", meta.get("name", base).lower())
        destino = SKILLS_DIR / sid
        destino.mkdir(parents=True, exist_ok=True)
        raiz = principal.rsplit("SKILL.md", 1)[0]
        for n in mds:
            rel = n[len(raiz):] if n.startswith(raiz) else Path(n).name
            alvo = destino / rel
            alvo.parent.mkdir(parents=True, exist_ok=True)
            alvo.write_bytes(z.read(n))
        return sid
    txt = dados.decode("utf-8", errors="replace")
    meta, _ = _sem_frontmatter(txt)
    sid = re.sub(r"[^\w\-]", "-", meta.get("name", base).lower())
    destino = SKILLS_DIR / sid
    destino.mkdir(parents=True, exist_ok=True)
    if not txt.lstrip().startswith("---"):
        txt = f'---\nname: "{sid}"\ndescription: "Guia importado"\n---\n\n' + txt
    (destino / "SKILL.md").write_text(txt, encoding="utf-8")
    return sid


def remover_skill(sid: str):
    import shutil
    shutil.rmtree(SKILLS_DIR / sid, ignore_errors=True)


# ------------------------------------------------------------------ geração
BASE = """Você é o roteirista-chefe de canais faceless do YouTube. Escreve roteiros NARRADOS por voz de IA,
prontos para gravar, com foco total em retenção. Siga TODAS as skills/guias de estilo abaixo; quando falarem de
edição ou títulos, use isso para escolher cenas fáceis de ilustrar e para os títulos sugeridos.
Nunca copie frases de outros canais. Em histórias reais, não invente nomes, datas, números ou falas entre aspas."""

FORMATO = """Responda EXATAMENTE neste formato (as tags são obrigatórias):
<titulos>
8 a 12 títulos, um por linha, no idioma do roteiro, até 100 caracteres. Marque os 2 melhores com ⭐ no início.
</titulos>
<roteiro>
Só o texto que será narrado, em parágrafos separados por uma linha em branco. Sem títulos de seção, rubricas,
marcações de cena, emojis ou observações.
</roteiro>
<notas>
Em português: em 3 a 6 linhas, a estrutura usada (ganchos e viradas) e, se pesquisou, as fontes principais.
</notas>"""


def _modelo(s):
    if s.get("llm_provider") == "anthropic":
        return s.get("roteiro_model_anthropic") or s.get("anthropic_model")
    return s.get("roteiro_model_outro") or None


def _parse(txt: str) -> dict:
    def tag(t):
        m = re.search(rf"<{t}>\s*(.*?)\s*(?:</{t}>|$)", txt, re.S)
        return m.group(1).strip() if m else ""
    roteiro = tag("roteiro")
    if not roteiro:  # IA não respeitou as tags
        roteiro = re.sub(r"<[^>]+>", "", txt).strip()
    titulos = [re.sub(r"^\s*(?:\d+[.)-]\s*|[-•*]\s*)", "", l).strip() for l in tag("titulos").splitlines() if l.strip()]
    roteiro = re.sub(r"^\s*(#+ .*|\*\*.*\*\*|\[.*?\])\s*$", "", roteiro, flags=re.M)  # tira títulos/rubricas
    roteiro = re.sub(r"\n{3,}", "\n\n", roteiro).strip()
    return {"titulos": titulos, "roteiro": roteiro, "notas": tag("notas")}


def _sistema(skills: list) -> str:
    guias = "\n\n".join(conteudo_skill(sid) for sid in skills if (SKILLS_DIR / sid).exists())
    return BASE + ("\n\n# SKILLS / GUIAS DE ESTILO\n" + guias if guias else "")


def gerar(p: dict, log=print) -> dict:
    """p: tema, titulo, idioma, minutos, tom, publico, referencia, extras, pesquisa, skills"""
    s = load_settings()
    if not llm_available(s):
        raise RuntimeError("Configure a IA de texto (de preferência o Claude) em APIs e configurações.")
    ppm = IDIOMAS.get(p.get("idioma"), 150)
    palavras = int(float(p.get("minutos", 10)) * ppm)
    partes = [f"IDIOMA DO ROTEIRO E DOS TÍTULOS: {p.get('idioma')}",
              f"TEMA / IDEIA: {p.get('tema', '').strip()}"]
    if p.get("titulo", "").strip():
        partes.append(f"TÍTULO JÁ ESCOLHIDO (use como norte; ainda assim sugira variações): {p['titulo']}")
    partes.append(f"ESTILO / TOM: {p.get('tom')}")
    if p.get("publico", "").strip():
        partes.append(f"PÚBLICO: {p['publico']}")
    partes.append(f"TAMANHO: cerca de {palavras} palavras narradas (≈ {p.get('minutos')} minutos). "
                  "Não termine antes de chegar perto desse tamanho.")
    if p.get("referencia", "").strip():
        partes.append("REFERÊNCIA (transcrição de um vídeo que performou bem). Use só como inspiração de estrutura, "
                      "ritmo e ganchos; NÃO copie frases. Se estiver em outro idioma, adapte a história para o idioma "
                      "do roteiro com naturalidade:\n\"\"\"\n" + p["referencia"][:30000] + "\n\"\"\"")
    if p.get("extras", "").strip():
        partes.append(f"PEDIDOS EXTRAS: {p['extras']}")
    if p.get("pesquisa"):
        partes.append("Antes de escrever, pesquise na web os fatos principais (datas, nomes, lugares) para não errar.")
    partes.append(FORMATO)
    max_tok = min(32000, int(palavras * 2.2) + 2500)
    log(f"Escrevendo ~{palavras} palavras…")
    txt = chat("\n\n".join(partes), system=_sistema(p.get("skills", [])), max_tokens=max_tok, model=_modelo(s),
               web_search=5 if p.get("pesquisa") else 0, timeout=900)
    r = _parse(txt)
    r["params"] = {k: v for k, v in p.items() if k != "referencia"}
    r["palavras"] = len(r["roteiro"].split())
    r["minutos"] = round(r["palavras"] / ppm, 1)
    salvar_historico(r)
    return r


def ajustar(r: dict, pedido: str, skills: list, log=print) -> dict:
    """Reescreve o roteiro seguindo um pedido ("mais tenso", "encurte para 8 min", "troque o final"…)."""
    s = load_settings()
    prompt = (f"Aqui está um roteiro narrado e os títulos sugeridos. Reescreva seguindo este pedido: {pedido}\n"
              f"Mantenha o idioma original.\n\n<titulos>\n" + "\n".join(r.get("titulos", [])) +
              f"\n</titulos>\n<roteiro>\n{r['roteiro']}\n</roteiro>\n\n{FORMATO}")
    txt = chat(prompt, system=_sistema(skills), max_tokens=min(32000, int(len(r["roteiro"].split()) * 2.4) + 3000),
               model=_modelo(s), timeout=900)
    novo = _parse(txt)
    novo["params"] = r.get("params", {})
    ppm = IDIOMAS.get(novo["params"].get("idioma"), 150)
    novo["palavras"] = len(novo["roteiro"].split())
    novo["minutos"] = round(novo["palavras"] / ppm, 1)
    salvar_historico(novo)
    return novo


def salvar_historico(r: dict):
    HIST.mkdir(parents=True, exist_ok=True)
    r["quando"] = time.strftime("%d/%m/%Y %H:%M")
    nome = re.sub(r"\W+", "_", (r.get("titulos") or ["roteiro"])[0].lstrip("⭐ "))[:40]
    (HIST / f"{time.strftime('%Y%m%d_%H%M%S')}_{nome}.json").write_text(json.dumps(r, ensure_ascii=False, indent=1),
                                                                         encoding="utf-8")


def historico() -> list:
    if not HIST.exists():
        return []
    out = []
    for f in sorted(HIST.glob("*.json"), reverse=True)[:30]:
        try:
            out.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return out
