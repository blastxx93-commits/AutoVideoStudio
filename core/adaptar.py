"""Dobra para outro idioma: pega a transcrição de um vídeo de referência, extrai só a ESTRUTURA do canal e
escreve um roteiro novo, com outro ângulo e perspectiva, no idioma escolhido (nunca uma tradução)."""
import json
import re

import requests

from .config import load_settings
from .llm import chat, llm_available
from . import roteiro as RT


def extrair_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|shorts/|embed/|live/)([\w-]{11})", url or "")
    if m:
        return m.group(1)
    if re.fullmatch(r"[\w-]{11}", (url or "").strip()):
        return url.strip()
    raise ValueError("Não reconheci o link. Cole o link completo do vídeo do YouTube.")


def info_video(url: str) -> dict:
    """Título e canal (oEmbed, sem chave)."""
    vid = extrair_id(url)
    try:
        r = requests.get("https://www.youtube.com/oembed", params={"url": f"https://www.youtube.com/watch?v={vid}",
                                                                   "format": "json"}, timeout=15)
        d = r.json()
        return {"id": vid, "titulo": d.get("title", ""), "canal": d.get("author_name", ""),
                "thumb": d.get("thumbnail_url", "")}
    except Exception:
        return {"id": vid, "titulo": "", "canal": "", "thumb": ""}


def transcricao(url: str) -> dict:
    """Baixa a legenda/transcrição pública do vídeo (manual ou automática), em qualquer idioma disponível."""
    vid = extrair_id(url)
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError:
        raise RuntimeError("Falta a biblioteca youtube-transcript-api. Rode o INSTALAR.bat de novo.")
    pref = ["pt", "pt-BR", "en", "es", "de", "it", "fr", "pl", "cs", "da", "no", "nb"]
    try:  # versão nova (1.x)
        api = YouTubeTranscriptApi()
        lista = api.list(vid)
        escolhida = None
        try:
            escolhida = lista.find_manually_created_transcript(pref)
        except Exception:
            try:
                escolhida = lista.find_generated_transcript(pref)
            except Exception:
                escolhida = next(iter(lista))
        dados = escolhida.fetch()
        partes = [s.text for s in dados] if hasattr(dados, "__iter__") else []
        idioma = escolhida.language_code
    except AttributeError:  # versão antiga (0.x)
        lista = YouTubeTranscriptApi.list_transcripts(vid)
        escolhida = next(iter(lista))
        partes = [x["text"] for x in escolhida.fetch()]
        idioma = escolhida.language_code
    except Exception as e:
        raise RuntimeError("Não consegui baixar a transcrição deste vídeo (ele pode não ter legendas, ou o YouTube "
                           f"bloqueou o acesso). Cole a transcrição manualmente. Detalhe: {str(e)[:200]}")
    texto = " ".join(p.replace("\n", " ").strip() for p in partes if p.strip())
    texto = re.sub(r"\[(música|music|aplausos|applause)\]", "", texto, flags=re.I)
    texto = re.sub(r"\s+", " ", texto).strip()
    return {"texto": texto, "idioma": idioma, "palavras": len(texto.split())}


# ------------------------------------------------------------------ dobra para outro idioma
# A dobra NÃO traduz o vídeo de referência: aproveita só a ESTRUTURA do canal e escreve uma versão nova,
# com outro ângulo/perspectiva, no idioma escolhido. Depois confere a originalidade e reescreve se precisar.
ANGULOS = {
    "Automático (a IA escolhe o ângulo mais forte e diferente)": "Escolha você o ângulo mais forte que seja claramente DIFERENTE do usado na referência.",
    "Outro protagonista / ponto de vista": "Conte a história pelos olhos de outra pessoa envolvida (investigador, vítima, testemunha, rival, familiar, cidade), não pelo do protagonista da referência.",
    "Bastidores e investigação": "Foque em como os fatos foram descobertos, investigados ou escondidos: pistas, erros, decisões e reviravoltas por trás da história.",
    "Mistérios e perguntas sem resposta": "Estruture em torno das dúvidas, contradições e teorias que até hoje cercam o tema.",
    "Consequências e legado": "Comece pelo impacto e pelas consequências (o que mudou depois) e volte no tempo para explicar como se chegou lá.",
    "Contexto histórico e comparação": "Coloque o tema dentro da época, compare com casos/figuras parecidas e mostre o que o torna único.",
    "Lado humano e psicológico": "Explore motivações, medos, dilemas e a psicologia das pessoas envolvidas.",
    "Linha do tempo invertida": "Comece pelo final/clímax e reconstrua os acontecimentos de trás para frente.",
}

SIS_ESTRUTURA = """Você é um analista de retenção de vídeos do YouTube. Extraia SOMENTE a ESTRUTURA/FÓRMULA do roteiro,
sem conteúdo: NÃO cite nomes, lugares, datas, frases, exemplos, metáforas ou fatos da história. Descreva de forma
genérica e reaproveitável, em português:
1. Tipo de gancho de abertura (ex.: cena de crise, pergunta, contraste) e quanto tempo dura.
2. Divisão em blocos/atos com a % aproximada do vídeo e a FUNÇÃO de cada bloco.
3. Onde e como aparecem os laços abertos / viradas / mini-cliffhangers (frequência).
4. Ritmo: tamanho médio das frases, alternância tensão x contexto, uso de perguntas retóricas.
5. Tom e narrador (1ª/3ª pessoa, distância, emoção) e como termina (fecho, CTA, gancho para o próximo).
Responda em tópicos curtos."""


def estrutura(texto: str) -> str:
    """Mapa da estrutura do canal (sem conteúdo)."""
    s = load_settings()
    return chat(f'ROTEIRO DE REFERÊNCIA:\n"""\n{texto[:60000]}\n"""', system=SIS_ESTRUTURA, max_tokens=1800,
                model=RT._modelo(s), timeout=300).strip()


def checar_originalidade(referencia: str, novo: str) -> dict:
    """Pede para a IA comparar e dar uma nota de semelhança (0 = nada parecido, 100 = tradução)."""
    s = load_settings()
    p = (f'TEXTO A (referência, pode estar em outro idioma):\n"""\n{referencia[:25000]}\n"""\n\n'
         f'TEXTO B (novo roteiro):\n"""\n{novo[:25000]}\n"""\n\n'
         "Compare B com A considerando que podem estar em idiomas diferentes. Avalie se B é tradução, paráfrase "
         "próxima ou reaproveitamento da sequência de frases/ideias/exemplos/metáforas/gancho de A. Fatos históricos "
         "em comum são permitidos e NÃO contam como cópia; o que conta é a EXPRESSÃO e a ordem das ideias.\n"
         'Responda SÓ JSON: {"semelhanca": <0-100>, "trechos": ["até 5 trechos de B parecidos demais com A"], '
         '"veredito": "<uma frase em português>"}')
    try:
        from .utils import extract_json
        d = extract_json(chat(p, max_tokens=900, model=RT._modelo(s), timeout=300))
        return {"semelhanca": int(d.get("semelhanca", 0)), "trechos": d.get("trechos", [])[:5],
                "veredito": d.get("veredito", "")}
    except Exception as e:
        return {"semelhanca": -1, "trechos": [], "veredito": f"Não consegui checar ({str(e)[:80]})."}


def adaptar(texto: str, idioma: str, angulo: str = None, minutos=None, titulo_original: str = "",
            skills: list = None, extras: str = "", pesquisa: bool = False, log=print, limite_semelhanca: int = 30) -> dict:
    """Dobra: mesma ESTRUTURA do canal de referência, roteiro novo com outro ângulo, no idioma escolhido."""
    s = load_settings()
    if not llm_available(s):
        raise RuntimeError("Configure a IA de texto (de preferência o Claude) em APIs e configurações.")
    if angulo not in ANGULOS:  # compatibilidade com itens antigos da fila ("adaptacao"/"traducao")
        angulo = list(ANGULOS)[0]
    ppm = RT.IDIOMAS.get(idioma, 150)
    alvo = int(float(minutos) * ppm) if minutos else len(texto.split())

    log("Lendo a estrutura do canal de referência…")
    mapa = estrutura(texto)

    def escrever(reforco=""):
        prompt = (
            f"Escreva em {idioma} um roteiro NOVO e ORIGINAL — uma 'dobra' para outro público, NÃO uma tradução.\n\n"
            f"TEMA GERAL (o mesmo assunto do vídeo de referência): {titulo_original or 'veja a referência'}\n"
            f"ÂNGULO DA NOVA VERSÃO: {angulo} — {ANGULOS[angulo]}\n\n"
            "ESTRUTURA DO CANAL A SEGUIR (use só a fórmula: tipo de gancho, blocos e % de tempo, frequência de viradas, "
            f"ritmo e tipo de final):\n{mapa}\n\n"
            "REGRAS DA DOBRA:\n"
            "- NÃO traduza nem parafraseie frases da referência; NÃO reaproveite o gancho, as metáforas, os exemplos, as "
            "frases de efeito nem a ordem em que as ideias aparecem.\n"
            "- Mude a perspectiva conforme o ângulo; a abertura precisa ser uma cena/ideia diferente da referência.\n"
            "- Traga pelo menos 4 detalhes, fatos ou explicações que NÃO aparecem na referência"
            + (" (pesquise na web para encontrar)" if pesquisa else " (só use fatos de que tenha certeza)") + ".\n"
            "- Fatos históricos podem coincidir, mas contados com outras palavras, outra ordem e outro foco.\n"
            "- Escreva para a cultura e o jeito de falar de quem fala esse idioma.\n"
            f"- Tamanho: cerca de {alvo} palavras narradas.\n"
            + (f"- Pedidos extras: {extras}\n" if extras.strip() else "")
            + reforco
            + f'\nREFERÊNCIA (só para você saber o tema e o que EVITAR repetir):\n"""\n{texto[:40000]}\n"""\n\n'
            + RT.FORMATO.replace("no idioma do roteiro", f"em {idioma}"))
        txt = chat(prompt, system=RT._sistema(skills or []), max_tokens=min(32000, int(alvo * 2.4) + 3000),
                   model=RT._modelo(s), web_search=5 if pesquisa else 0, timeout=900)
        return RT._parse(txt)

    log(f"Escrevendo a nova versão em {idioma} ({angulo.split(' (')[0]})…")
    r = escrever()
    log("Conferindo a originalidade…")
    chk = checar_originalidade(texto, r["roteiro"])
    tentativas = 1
    while chk["semelhanca"] > limite_semelhanca and tentativas < 3:
        log(f"Ficou parecido demais ({chk['semelhanca']}%). Reescrevendo com outro ângulo…")
        trechos = "\n".join(f"- {t}" for t in chk["trechos"])
        r = escrever(f"- ATENÇÃO: a versão anterior ficou parecida demais com a referência ({chk['semelhanca']}%). "
                     f"Mude mais a abordagem, a ordem e as palavras. Evite especialmente algo como:\n{trechos}\n")
        chk = checar_originalidade(texto, r["roteiro"])
        tentativas += 1
    nota_orig = (f"**Originalidade:** semelhança com a referência de {chk['semelhanca']}% "
                 f"(quanto menor, mais original; o limite é {limite_semelhanca}%). {chk['veredito']}"
                 if chk["semelhanca"] >= 0 else f"**Originalidade:** {chk['veredito']}")
    r["notas"] = (f"**Ângulo:** {angulo.split(' (')[0]}\n\n{nota_orig}\n\n**Estrutura do canal usada:**\n{mapa}\n\n"
                  + (r.get("notas") or ""))
    r["originalidade"] = chk
    r["params"] = {"tema": titulo_original or "dobra", "idioma": idioma, "angulo": angulo, "origem": "dobra"}
    r["palavras"] = len(r["roteiro"].split())
    r["minutos"] = round(r["palavras"] / ppm, 1)
    RT.salvar_historico(r)
    return r


IDIOMA_SEO = {"Português (Brasil)": "Português", "Português (Portugal)": "Português", "English": "English",
              "Español": "Español", "Deutsch": "Deutsch", "Polski": "Polski", "Čeština": "Čeština",
              "Dansk": "Dansk", "Norsk": "Norsk"}
