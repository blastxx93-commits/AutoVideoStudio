"""AutoVideo Studio — interface. Abra com ABRIR.bat (ou: streamlit run app.py)."""
import json
import math
import re
from datetime import datetime
import os
import subprocess
import sys
import time
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent))
from core import config as C  # noqa: E402
from core.config import (load_settings, save_settings, default_job, VISUAL_STYLES, MOTIONS, TRANSITIONS,  # noqa: E402
                         SUBTITLE_STYLES, IMAGE_PROVIDERS, STOCK_SOURCES, ELEVEN_MODELS, FISH_MODELS)

from core.tema import aplicar_tema, logo_sidebar, hero, cartoes  # noqa: E402

st.set_page_config(page_title="AutoVideo Studio", page_icon=str(C.ASSETS_DIR / "icone.png"), layout="wide")

from core.versao import VERSAO  # noqa: E402
PROFILE_SKIP = {"titulo", "roteiro"}


# ------------------------------------------------------------------ helpers
def J(key):
    return st.session_state["job"][key]


def bind(key, widget, label, **kw):
    """Cria um widget ligado ao dicionário do trabalho."""
    wkey = f"w_{key}"
    if wkey not in st.session_state:
        st.session_state[wkey] = st.session_state["job"].get(key)
    val = widget(label, key=wkey, **kw)
    st.session_state["job"][key] = val
    return val


def campo(key, label, area=False, onde=None, botao="✓ Confirmar", **kw):
    """Campo de texto com botão Confirmar ao lado (Enter também confirma)."""
    wkey = f"w_{key}"
    if wkey not in st.session_state:
        st.session_state[wkey] = st.session_state["job"].get(key) or ""
    alvo = onde or st
    with alvo.form(f"form_{key}", border=False):
        if area:
            val = st.text_area(label, key=wkey, **kw)
            ok = st.form_submit_button(botao)
        else:
            c1, c2 = st.columns([5, 1], vertical_alignment="bottom")
            val = c1.text_input(label, key=wkey, **kw)
            ok = c2.form_submit_button(botao, use_container_width=True)
    st.session_state["job"][key] = val
    if ok:
        st.toast(f"✓ {label.split('(')[0].strip()[:40]} confirmado")
    return val


def _tem(valor, aviso: str) -> bool:
    """Valida um campo na hora do clique (em vez de deixar o botão desativado até apertar Enter)."""
    if str(valor or "").strip():
        return True
    st.warning(aviso)
    return False


def set_job(d: dict):
    d = dict(d)
    for _k in ("img_provider", "img_provider_thumb"):  # nome antigo do gerador da OpenAI
        if d.get(_k) == "OpenAI (gpt-image)":
            d[_k] = "ChatGPT / OpenAI (gpt-image)"
    if "pct_banco" not in d:
        d["pct_banco"] = C.pct_banco(d)
    job = default_job()
    job.update(d)
    st.session_state["job"] = job
    for k in list(st.session_state.keys()):
        if k.startswith("w_"):
            del st.session_state[k]


def pick_folder(initial=""):
    code = ("import tkinter as tk;from tkinter import filedialog;r=tk.Tk();r.withdraw();r.attributes('-topmost',True);"
            f"print(filedialog.askdirectory(initialdir=r'''{initial}'''))")
    try:
        out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=600)
        return out.stdout.strip()
    except Exception:
        return ""


def open_folder(path):
    try:
        if os.name == "nt":
            os.startfile(path)  # type: ignore
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        st.warning(f"Não consegui abrir a pasta: {e}")


def ir_adaptar(link: str):
    """Leva um vídeo do Buscador direto para a etapa Roteiro → Adaptar."""
    st.session_state["_pending"] = {"ad_link": link}
    for k in ("ad_info", "ad_texto_area", "roteiro_gerado"):
        st.session_state.pop(k, None)
    st.session_state["pagina"] = "Dobra de canais"
    st.rerun()


def abrir_projeto(job_dir: Path):
    st.session_state["projeto_aberto"] = str(job_dir)
    st.session_state["pagina"] = "Fila de vídeos"
    st.rerun()


def controle(job_dir: Path, **kw):
    p = Path(job_dir) / "controle.json"
    try:
        d = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:
        d = {}
    d.update(kw)
    p.write_text(json.dumps(d), encoding="utf-8")


def start_job(job_dir: Path):
    (Path(job_dir) / "controle.json").unlink(missing_ok=True)
    from core.utils import env_utf8
    log = open(job_dir / "saida_terminal.txt", "a", encoding="utf-8")
    flags = 0x08000000 if os.name == "nt" else 0
    subprocess.Popen([sys.executable, "-m", "core.pipeline", str(job_dir)], cwd=str(C.APP_DIR),
                     stdout=log, stderr=subprocess.STDOUT, creationflags=flags, env=env_utf8())
    st.session_state["job_ativo"] = str(job_dir)


def read_progress(job_dir: Path):
    p = Path(job_dir) / "progresso.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


if "job" not in st.session_state:
    set_job({})

# ------------------------------------------------------------------ menu
if "tema" not in st.session_state:
    st.session_state["tema"] = load_settings().get("tema", "escuro")
TEMA = aplicar_tema(st.session_state["tema"])
logo_sidebar(st.session_state["tema"])

PAGINAS = [("🎬", "Novo vídeo"), ("🌍", "Dobra de canais"), ("📋", "Fila de vídeos"), ("🔎", "BUSCADOR DE NICHOS"), ("📂", "Trabalhos"),
           ("📤", "Publicar no YouTube"), ("⚙️", "APIs e configurações")]
if "pagina" not in st.session_state:
    st.session_state["pagina"] = "Novo vídeo"
for _ic, _nome in PAGINAS:
    if st.sidebar.button(f"{_ic}   {_nome}", key=f"nav_{_nome}", use_container_width=True,
                         type="primary" if st.session_state["pagina"] == _nome else "secondary"):
        st.session_state["pagina"] = _nome
        st.rerun()
page = st.session_state["pagina"]

st.sidebar.divider()
_escuro = st.sidebar.toggle("🌙  Tema escuro", value=st.session_state["tema"] == "escuro")
_novo = "escuro" if _escuro else "claro"
if _novo != st.session_state["tema"]:
    st.session_state["tema"] = _novo
    _s = load_settings()
    _s["tema"] = _novo
    save_settings(_s)
    st.rerun()
st.sidebar.markdown('<div class="av-side-foot">Roteiro + título → vídeo pronto.<br>'
                    'Tudo roda no seu PC; só as APIs que você escolher são pagas.<br><br>'
                    f'<b>AutoVideo Studio</b> · versão {VERSAO}</div>', unsafe_allow_html=True)
def _consertar_atalhos():
    """Uma vez por versão: recria o atalho com o logo e coloca o logo nos atalhos antigos da Área de Trabalho."""
    marca = C.DATA_DIR / "atalhos_v2.ok"
    if os.name != "nt" or marca.exists() or st.session_state.get("_atalhos_tentado"):
        return
    st.session_state["_atalhos_tentado"] = True
    import subprocess
    import sys as _sys
    raiz = Path(__file__).resolve().parent
    py = Path(_sys.executable)
    if py.name.lower() == "pythonw.exe" and (py.parent / "python.exe").exists():
        py = py.parent / "python.exe"
    try:
        subprocess.Popen([str(py), str(raiz / "criar_atalhos.py")], cwd=str(raiz), creationflags=0x08000000)
    except Exception:
        pass


_consertar_atalhos()


@st.cache_data(ttl=1800, show_spinner=False)
def _checar_atualizacao(repo: str) -> dict:
    """Procura versão nova no máximo a cada 30 minutos (resposta rápida, até 4 s)."""
    from core import atualizador as AT
    try:
        return AT.verificar_online(timeout=4)
    except Exception:
        return {}


_cfg_upd = load_settings()
if "upd_info" not in st.session_state and _cfg_upd.get("atualizacao_auto", True) and _cfg_upd.get("atualizacao_repo"):
    st.session_state["upd_info"] = _checar_atualizacao(_cfg_upd["atualizacao_repo"])
_upd = st.session_state.get("upd_info") or {}
if _upd.get("nova"):
    if st.sidebar.button(f"⬆️ Atualizar para a versão {_upd['versao']}", key="upd_side", type="primary",
                         use_container_width=True):
        st.session_state["pagina"] = "APIs e configurações"
        st.session_state["upd_auto_abrir"] = True
        st.rerun()
if st.sidebar.button("⏻  Sair do programa", key="sair", use_container_width=True,
                     help="Fecha o programa. Vídeos que já estão sendo gerados continuam até terminar."):
    import threading
    st.sidebar.success("Programa encerrado. Pode fechar a janela.")
    threading.Timer(1.0, lambda: os._exit(0)).start()


# ================================================================== NOVO VÍDEO
def aplicar_pendentes():
    for k, v in st.session_state.pop("_pending", {}).items():
        st.session_state["job"][k] = v
        st.session_state[f"w_{k}"] = v


def page_new():
    s = load_settings()
    aplicar_pendentes()
    hero("🎬", "Novo vídeo", "Do título ao vídeo pronto, em etapas. Confirme cada uma e siga para a próxima.")

    # ---- título + perfil (topo, igual a um formulário de projeto)
    with st.container(key="titulo_card"):
        c1, c2 = st.columns([3, 1.25], vertical_alignment="bottom")
        with c1:
            campo("titulo", label="Título do vídeo", placeholder="Ex.: O dia em que Roma queimou")
        with c2:
            profiles = sorted(p.stem for p in C.PROFILES_DIR.glob("*.json"))
            sel = st.selectbox("Perfil do canal", ["—"] + profiles, key="perfil_sel",
                               help="Carrega todas as opções salvas para esse canal (voz, estilo, template, trilha…).")
            if sel != "—" and st.session_state.get("_perfil_carregado") != sel:
                d = json.loads((C.PROFILES_DIR / f"{sel}.json").read_text(encoding="utf-8"))
                d.update({k: st.session_state["job"][k] for k in PROFILE_SKIP})
                set_job(d)
                st.session_state["_perfil_carregado"] = sel
                st.toast(f"Perfil {sel} carregado")
                st.rerun()

    referencia_edicao()

    tabs = etapas_novo_video()

    with tabs[0]:
        if J("modo_roteiro") not in ("Já tenho", "Gerar com IA"):
            st.session_state["job"]["modo_roteiro"] = "Já tenho"
            st.session_state.pop("w_modo_roteiro", None)
        bind("modo_roteiro", st.radio, "Como você quer o roteiro?", options=["Já tenho", "Gerar com IA"], horizontal=True,
             format_func={"Já tenho": "📝 Já tenho o roteiro", "Gerar com IA": "✨ Gerar com IA (Claude + skills)"}.get)
        st.caption("🌍 Quer levar um vídeo de outro canal para outro idioma? Use **Dobra de canais** no menu à esquerda.")
        if J("modo_roteiro") == "Gerar com IA":
            gerador_roteiro()
            st.markdown("#### 📝 Roteiro que será usado no vídeo")
        campo("roteiro", area=True, label="Roteiro (só o texto que será narrado)", height=360,
             help="Deixe uma linha em branco entre parágrafos. O texto é narrado exatamente como está.")
        txt = J("roteiro") or ""
        words = len(txt.split())
        st.caption(f"{words} palavras · ≈ {words / 150:.1f} min de vídeo")
        bind("segundos_por_cena", st.slider, "Duração média de cada cena (segundos)", min_value=3, max_value=15,
             help="Menos segundos = mais imagens e vídeo mais dinâmico (e mais imagens geradas).")
        if words:
            n = max(1, int(words / 2.6 / J("segundos_por_cena")))
            st.caption(f"≈ {n} cenas/imagens")

    with tabs[1]:
        if "pct_banco" not in st.session_state["job"] or st.session_state["job"].get("pct_banco") is None:
            st.session_state["job"]["pct_banco"] = C.pct_banco(st.session_state["job"])
        st.markdown("**Conteúdo do vídeo: arraste para escolher a mistura**")
        bind("pct_banco", st.slider, "🗂️ Banco de imagens/clipes  ←→  🤖 Imagens de IA", min_value=0, max_value=100, step=5,
             format="%d%% banco",
             help="0% = só IA · 100% = só banco · 70% = 7 de cada 10 cenas vêm do banco e 3 da IA.")
        pb = int(J("pct_banco"))
        pi = 100 - pb
        n_cenas = max(1, int(len((J("roteiro") or "").split()) / 2.6 / J("segundos_por_cena"))) if J("roteiro") else 0
        nb = round(n_cenas * pb / 100)
        st.markdown(
            f'''<div style="display:flex;height:34px;border-radius:12px;overflow:hidden;margin:4px 0 6px 0;
            box-shadow:0 6px 18px {TEMA["glow"]};font-weight:700;font-size:.92rem;color:#fff">
            <div style="width:{pb}%;background:linear-gradient(135deg,#0EA5E9,#2563EB);display:flex;align-items:center;
            justify-content:center;white-space:nowrap;overflow:hidden">{"🗂️ Banco " + str(pb) + "%" if pb >= 12 else ""}</div>
            <div style="width:{pi}%;background:linear-gradient(135deg,#F42B03,#FF6A3D);display:flex;align-items:center;
            justify-content:center;white-space:nowrap;overflow:hidden">{"🤖 IA " + str(pi) + "%" if pi >= 12 else ""}</div></div>''',
            unsafe_allow_html=True)
        if n_cenas:
            st.caption(f"≈ {nb} cenas do banco + {n_cenas - nb} cenas geradas por IA (de ≈ {n_cenas} cenas)")
        if 0 < pb < 100:
            bind("distribuicao_mix", st.radio, "Como misturar", options=["Intercalado", "Blocos", "Aleatório"], horizontal=True,
                 help="Intercalado: espalha por igual (B I B B I…). Blocos: grupos de ~3 cenas seguidas da mesma fonte. "
                      "Aleatório: sorteia a ordem. Se o banco não achar nada para uma cena, ela vira IA automaticamente.")
        st.session_state["job"]["modo_visual"] = "Banco" if pb == 100 else "IA"
        if pb < 100:
            galeria_estilos(pb)
        _ca, _cb = st.columns(2) if 0 < pb < 100 else (st.container(), st.container())
        if pb < 100:
            with _ca.container(border=True):
                st.markdown(f"#### 🤖 Imagens de IA — {pi}%")
                bind("img_provider", st.selectbox, "Gerador de imagens", options=IMAGE_PROVIDERS)
                st.caption(f"Estilo: **{J('estilo_visual')}** (escolha na galeria acima)")
                st.info("Meta AI e Google Flow não têm API pública de imagens. Do Google, use **Google Imagen** "
                        "(mesmo modelo de imagem do Flow, via chave do Gemini). Flux está no Pollinations (grátis), "
                        "Replicate, fal.ai, Together e BFL.")
                with st.expander("Testar gerador"):
                    tp = st.text_input("Prompt de teste", "an old sicilian village at dusk")
                    if st.button("Gerar imagem de teste"):
                        from core import images
                        try:
                            with st.spinner("Gerando..."):
                                out = images.generate_ai(J("img_provider"), images.full_prompt(tp, st.session_state["job"]),
                                                         C.DATA_DIR / "teste_imagem")
                            st.image(str(out))
                        except Exception as e:
                            st.error(str(e))
        if pb > 0:
            with _cb.container(border=True):
                st.markdown(f"#### 🗂️ Banco de imagens/clipes — {pb}%")
                bind("banco_fontes", st.multiselect, "Fontes", options=STOCK_SOURCES)
                bind("banco_tipo", st.radio, "Tipo de mídia", options=["Misto (clipes + fotos)", "Clipes", "Fotos"], horizontal=True)
                if "Pasta do meu PC" in J("banco_fontes"):
                    campo("pasta_midia_local", label="Pasta com suas imagens/clipes",
                          help="Nomeie os arquivos com palavras-chave (ex: mafia_tribunal.mp4) para o programa achar o melhor para cada cena.")
                    if True:
                        if st.button("📂 Escolher pasta…", key="pick_local"):
                            p = pick_folder()
                            if p:
                                st.session_state["_pending"] = {"pasta_midia_local": p}
                                st.rerun()
                if ("Pexels" in J("banco_fontes") and not s["pexels_key"]) or ("Pixabay" in J("banco_fontes") and not s["pixabay_key"]):
                    st.warning("Falta a chave do Pexels/Pixabay em **APIs e configurações** (as duas são grátis).")

    with tabs[2]:
        bind("tts_provider", st.radio, "Serviço de voz", options=["ElevenLabs", "Fish Audio"], horizontal=True)
        prov = J("tts_provider")
        if prov == "ElevenLabs":
            bind("eleven_model", st.selectbox, "Modelo", options=ELEVEN_MODELS)
        else:
            bind("fish_model", st.selectbox, "Modelo", options=FISH_MODELS)
        c1, c2 = st.columns([3, 1])
        with c2:
            busca = st.text_input("Buscar voz pública (Fish)", "") if prov == "Fish Audio" else ""
            if st.button("Carregar vozes"):
                from core import tts
                try:
                    st.session_state["vozes"] = tts.list_voices(prov, busca)
                except Exception as e:
                    st.error(str(e))
        with c1:
            vozes = st.session_state.get("vozes", [])
            if vozes:
                names = [n for n, _ in vozes]
                cur = next((i for i, (_, v) in enumerate(vozes) if v == J("voz_id")), 0)
                escolha = st.selectbox("Voz", names, index=cur)
                vid = dict(vozes)[escolha]
                if vid != J("voz_id"):
                    st.session_state["job"]["voz_id"] = vid
                    st.session_state["job"]["voz_nome"] = escolha
                    st.session_state["w_voz_id"] = vid
            campo("voz_id", label="ID da voz", help="Pode colar o ID direto do site da ElevenLabs/Fish Audio.")
        bind("velocidade_voz", st.slider, "Velocidade da narração", min_value=0.8, max_value=1.3, step=0.05)
        if st.button("▶ Ouvir amostra"):
            from core import tts
            try:
                mp3 = C.DATA_DIR / "amostra_voz.mp3"
                with st.spinner("Gerando amostra..."):
                    tts.synth(prov, "Esta é uma amostra da narração do seu próximo vídeo.", J("voz_id"), mp3,
                              st.session_state["job"])
                st.audio(str(mp3))
            except Exception as e:
                st.error(str(e))

    with tabs[3]:
        bind("legendas", st.toggle, "Colocar legendas no vídeo")
        if J("legendas"):
            bind("estilo_legenda", st.selectbox, "Estilo da legenda", options=list(SUBTITLE_STYLES))
            from core import previas as PV, templates as TP
            _ov = TP.legenda_override(J("template")) if J("template") not in (None, "Nenhum") and J("template_legenda") else None
            try:
                with st.spinner("Preparando exemplo…"):
                    st.image(str(PV.legenda(J("estilo_legenda"), _ov)), use_container_width=True)
                st.caption("👁️ Exemplo da legenda" + (f" (com as cores do template {J('template')})" if _ov else ""))
            except Exception as e:
                st.caption(f"(exemplo indisponível: {str(e)[:120]})")
            bind("exportar_srt", st.checkbox, "Exportar também arquivo .srt (para subir no YouTube)")
            st.caption("Dica: instale o pacote opcional faster-whisper para legendas sincronizadas palavra por palavra.")

    with tabs[4]:
        secao_templates()
        st.markdown("#### 🎞️ Movimento, transições e efeitos")
        c1, c2 = st.columns(2)
        with c1:
            from core import previas as PV
            bind("movimento", st.selectbox, "Movimento nas imagens", options=MOTIONS)
            bind("intensidade_movimento", st.select_slider, "Intensidade do movimento", options=["Suave", "Média", "Forte"])
            if J("movimento") == "Aleatório":
                st.caption("Aleatório sorteia um destes por cena: zoom in, zoom out e pans. Exemplo de um deles:")
            previa_video(PV.movimento, "Zoom in" if J("movimento") == "Aleatório" else J("movimento"),
                         J("intensidade_movimento"), legenda=f"Exemplo: {J('movimento')} · {J('intensidade_movimento')}")
            bind("transicao", st.selectbox, "Transição entre cenas", options=list(TRANSITIONS))
            if TRANSITIONS.get(J("transicao")):
                bind("duracao_transicao", st.slider, "Duração da transição (s)", min_value=0.2, max_value=1.5, step=0.1)
            previa_video(PV.transicao, J("transicao"), float(J("duracao_transicao")),
                         legenda=f"Exemplo: {J('transicao')}")
        with c2:
            bind("efeitos_sonoros", st.toggle, "Efeitos sonoros nas transições (whoosh)")
            if J("efeitos_sonoros"):
                bind("volume_sfx", st.slider, "Volume dos efeitos", min_value=0.05, max_value=1.0, step=0.05)
                st.caption(f"Coloque seus próprios efeitos (.wav/.mp3) em: {C.SFX_DIR}")
            st.caption("🎵 A trilha sonora agora fica na aba **Trilha sonora**.")

    with tabs[5]:
        aba_trilha()

    with tabs[6]:
        bind("revisao", st.toggle, "Ativar agente de revisão")
        if J("revisao"):
            st.markdown("Confere: **imagens repetidas**, **arquivos corrompidos**, **tela preta/branca**, "
                        "**imagens sem detalhe**, **narração cortada ou com silêncio**, **áudio estourado/baixo**, "
                        "**legendas sobrepostas/vazias**, **duração do vídeo x narração**.")
            bind("revisao_auto_corrigir", st.checkbox, "Corrigir automaticamente (troca imagens e regera áudios com problema)")
            bind("revisao_ia_visao", st.checkbox, "Revisão extra com IA de visão (confere se a imagem combina com a narração e tem defeitos — gasta créditos da IA de texto)")

    with tabs[7]:
        bind("thumbnail", st.toggle, "Gerar thumbnail")
        if J("thumbnail"):
            bind("img_provider_thumb", st.selectbox, "Gerador para a thumbnail", options=IMAGE_PROVIDERS)
            campo("thumb_texto", label="Texto da thumbnail (vazio = a IA sugere; escreva 'sem texto' para não ter)")
            campo("thumb_prompt", area=True, label="Descrição da imagem (vazio = a IA cria a partir do título)", height=80)

    with tabs[8]:
        from core import seo as SEO
        bind("seo", st.toggle, "Gerar descrição, hashtags e palavras-chave")
        if J("seo"):
            c1, c2 = st.columns(2)
            with c1:
                bind("seo_idioma", st.selectbox, "Idioma", options=list(SEO.IDIOMAS))
                bind("seo_qtd_hashtags", st.slider, "Quantidade de hashtags", min_value=3, max_value=15,
                     help="As 3 primeiras aparecem acima do título. Com mais de 15 o YouTube ignora todas.")
                bind("seo_capitulos", st.checkbox, "Incluir capítulos com minutagem (0:00 Introdução…)")
                bind("seo_checar_api", st.checkbox, "Medir a demanda das hashtags na API do YouTube (~100 unidades de cota por hashtag)")
            with c2:
                campo("seo_texto_fixo", area=True, label="Texto fixo no fim da descrição (redes sociais, inscreva-se, créditos…)", height=150,
                     placeholder="🔔 Inscreva-se e ative o sininho!\nInstagram: @seucanal")
            st.caption("As palavras-chave e hashtags priorizam o que as pessoas **realmente digitam** na busca do YouTube "
                       "(sugestões de busca da plataforma), e não só o que a IA imagina.")
            if st.button("⚡ Gerar só a descrição agora (sem fazer o vídeo)"):
                if not J("titulo").strip() or len(J("roteiro").split()) < 5:
                    st.error("Preencha título e roteiro primeiro.")
                else:
                    with st.spinner("Pesquisando buscas e escrevendo..."):
                        st.session_state["seo_rapido"] = SEO.gerar(st.session_state["job"])
            if st.session_state.get("seo_rapido"):
                painel_seo(st.session_state["seo_rapido"], "rapido")

    with tabs[9]:
        campo("pasta_saida", label="Pasta onde o vídeo será salvo")
        if True:
            if st.button("📂 Escolher pasta…", key="pick_out"):
                p = pick_folder(J("pasta_saida"))
                if p:
                    st.session_state["_pending"] = {"pasta_saida": p}
                    st.rerun()
        st.caption("Será criada uma subpasta com o nome do vídeo contendo: vídeo .mp4, thumbnail, legenda .srt e relatório de revisão.")
        bind("resolucao", st.radio, "Resolução do vídeo", options=list(C.RESOLUCOES), horizontal=True,
             help="2K (2560×1440) fica mais nítido e o YouTube usa um codec melhor (VP9) até para quem assiste em 1080p. "
                  "Demora ~1,8x mais para renderizar e o arquivo fica maior.")
        bind("revisar_antes", st.toggle, "👀 Assistir e aprovar antes de exportar",
             help="Ligado: quando o vídeo fica pronto, ele aparece aqui para você assistir; só vai para a pasta quando você aprovar. "
                  "Desligado: exporta direto.")

    rodapes_etapas(tabs)

    st.write("")
    problems = []
    job = st.session_state["job"]
    if not job["titulo"].strip():
        problems.append("falta o título")
    if len(job["roteiro"].split()) < 5:
        problems.append("falta o roteiro")
    if not job["voz_id"].strip():
        problems.append("escolha uma voz")
    if job["tts_provider"] == "ElevenLabs" and not s["elevenlabs_key"]:
        problems.append("falta a chave da ElevenLabs")
    if job["tts_provider"] == "Fish Audio" and not s["fishaudio_key"]:
        problems.append("falta a chave da Fish Audio")
    if s["llm_provider"] == "nenhum":
        st.warning("Nenhuma IA de texto configurada: os prompts das imagens ficarão mais fracos. Configure em **APIs e configurações**.")
    if problems:
        st.error("Antes de gerar: " + ", ".join(problems) + ".")
    g1, g2 = st.columns([3, 1.3])
    if g2.button("➕ Adicionar à fila", use_container_width=True, disabled=bool(problems),
                 help="Guarda este vídeo na Fila para gerar depois, junto com outros, sem você precisar ficar olhando."):
        from core import fila as FL
        FL.adicionar(dict(job))
        st.toast("✓ Adicionado à Fila de vídeos")
        st.success("Adicionado à **Fila de vídeos**. Monte o próximo e adicione também, ou vá na Fila e clique em Iniciar.")
    if g1.button("🚀 GERAR VÍDEO", type="primary", use_container_width=True, disabled=bool(problems)):
        from core.utils import safe_name
        jd = C.JOBS_DIR / (time.strftime("%Y%m%d_%H%M%S_") + safe_name(job["titulo"], 40))
        jd.mkdir(parents=True, exist_ok=True)
        (jd / "trabalho.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        start_job(jd)
        st.success("Começou! Acompanhe abaixo ou em **Trabalhos**. Você pode montar o próximo vídeo enquanto isso.")

    with st.expander("💾 Salvar as opções atuais como perfil de canal"):
        c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
        nome = c1.text_input("Nome do perfil", placeholder="ex: Canal Máfia", key="nome_perfil_novo")
        if c2.button("Salvar perfil", use_container_width=True) and _tem(nome, "Escreva o nome do perfil."):
            d = {k: v for k, v in st.session_state["job"].items() if k not in PROFILE_SKIP}
            (C.PROFILES_DIR / f"{nome.strip()}.json").write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            st.toast(f"✓ Perfil {nome.strip()} salvo")

    if st.session_state.get("job_ativo"):
        progress_panel(Path(st.session_state["job_ativo"]))


ETAPAS = [  # (índice usado no código, slug, ícone, nome)
    (0, "roteiro", "📄", "Roteiro"), (2, "narracao", "🎙️", "Narração"), (1, "cenas", "🎬", "Cenas"),
    (4, "edicao", "✨", "Edição e animação"), (3, "legenda", "💬", "Legenda"), (5, "trilha", "🎵", "Trilha"),
    (6, "revisao", "🔍", "Revisão"), (7, "thumb", "🖼️", "Thumb"), (8, "seo", "📣", "Descrição e SEO"),
    (9, "exportar", "📂", "Exportar"),
]


def resumo_etapa(slug: str) -> str:
    j = st.session_state["job"]
    try:
        if slug == "roteiro":
            w = len((j.get("roteiro") or "").split())
            modo = {"Já tenho": "roteiro seu", "Gerar com IA": "gerado com IA", "Adaptar": "dobra de outro vídeo"}.get(j.get("modo_roteiro", "Já tenho"), "roteiro seu")
            return f"{modo} · {w} palavras · ≈ {w / 150:.1f} min" if w else f"{modo} · ainda vazio"
        if slug == "narracao":
            return f"{j['tts_provider']} · " + (j.get("voz_nome") or (j["voz_id"][:22] if j["voz_id"] else "escolha uma voz")) + f" · velocidade {j['velocidade_voz']:.2f}"
        if slug == "cenas":
            pb = C.pct_banco(j)
            mix = "só IA" if pb == 0 else "só banco" if pb == 100 else f"{pb}% banco · {100 - pb}% IA"
            return f"{mix} · {j['estilo_visual'] if pb < 100 else ', '.join(j['banco_fontes'])} · ~{j['segundos_por_cena']}s por cena"
        if slug == "edicao":
            return f"template {j.get('template', 'Nenhum')} · {j['movimento'].lower()} · {j['transicao'].split(' (')[0].lower()}"
        if slug == "legenda":
            return j["estilo_legenda"].split(" (")[0] if j["legendas"] else "sem legenda"
        if slug == "trilha":
            m = j.get("trilha_modo", "Automático")
            return "sem música" if m == "Sem música" else (f"tema {j.get('trilha_tema')}" if m == "Tema" else m.lower())
        if slug == "revisao":
            return ("agente ativo · " + ("corrige sozinho" if j["revisao_auto_corrigir"] else "só relatório")) if j["revisao"] else "desligada"
        if slug == "thumb":
            return ("gerar thumb · " + j.get("img_provider_thumb", "").split(" (")[0]) if j["thumbnail"] else "sem thumb"
        if slug == "seo":
            return f"descrição + {j.get('seo_qtd_hashtags', 5)} hashtags + palavras-chave" if j.get("seo", True) else "desligado"
        if slug == "exportar":
            return f"{j.get('resolucao', '1080p').split(' (')[0]} · " + ("assistir antes de exportar" if j.get("revisar_antes", True) else "exporta direto")
    except Exception:
        return ""
    return ""


def etapas_novo_video() -> dict:
    """Desenha a lista de etapas (estilo pipeline). Todas as etapas são montadas; só a aberta aparece."""
    aberta = st.session_state.setdefault("etapa_aberta", "roteiro")
    feitas = st.session_state.setdefault("etapas_ok", set())
    corpos = {}
    for n, (idx, slug, ico, nome) in enumerate(ETAPAS, 1):
        with st.container(key=f"etapa_{n}"):
            c1, c2 = st.columns([8, 1.35], vertical_alignment="center")
            dot = "aberta" if slug == aberta else ("ok" if slug in feitas else "")
            c1.markdown(f'<div class="av-row"><div class="ico">{ico}<span class="dot {dot}"></span></div>'
                        f'<div class="tx"><span class="n">{n}</span><b>{nome}</b>'
                        f'{"<span class=av-badge>CONFIRMADO</span>" if slug in feitas and slug != aberta else ""}'
                        f'<span class="res">{resumo_etapa(slug)}</span></div></div>', unsafe_allow_html=True)
            if c2.button("Fechar ▲" if slug == aberta else "Editar ▼", key=f"tg_{slug}", use_container_width=True,
                         type="primary" if slug == aberta else "secondary"):
                st.session_state["etapa_aberta"] = None if slug == aberta else slug
                st.rerun()
            corpos[idx] = st.container(key=f"corpo_{slug}_{'on' if slug == aberta else 'off'}")
    return corpos


def rodapes_etapas(corpos: dict):
    """Botão 'Confirmar e continuar' no fim de cada etapa: marca como feita e abre a próxima."""
    for k, (idx, slug, ico, nome) in enumerate(ETAPAS):
        prox = ETAPAS[k + 1] if k + 1 < len(ETAPAS) else None
        with corpos[idx]:
            rot = f"✓ Confirmar e ir para {prox[3]} →" if prox else "✓ Confirmar — tudo pronto para gerar"
            if st.button(rot, key=f"ok_{slug}", type="primary"):
                st.session_state["etapas_ok"].add(slug)
                st.session_state["etapa_aberta"] = prox[1] if prox else None
                st.rerun()


def progress_panel(job_dir: Path, key=""):
    """Mostra o estado do trabalho: progresso ao vivo, revisão do vídeo pronto, exportado ou erro."""
    if not Path(job_dir).exists():
        st.session_state.pop("job_ativo", None)
        return
    pr = read_progress(job_dir)
    if pr and pr["status"] == "aguardando":
        painel_revisao(job_dir, pr, key)
    elif pr and pr["status"] in ("concluido", "erro", "cancelado"):
        painel_final(job_dir, pr, key)
    else:
        painel_ao_vivo(job_dir)


def previa_video(gerar, *args, legenda="Exemplo"):
    """Mostra um mini-vídeo de exemplo (gerado na hora na 1ª vez, depois vem do cache)."""
    try:
        with st.spinner("Preparando exemplo…"):
            caminho = gerar(*args)
        try:
            st.video(str(caminho), autoplay=True, loop=True, muted=True)
        except TypeError:
            st.video(str(caminho))
        st.caption(f"👁️ {legenda}")
    except Exception as e:
        st.caption(f"(exemplo indisponível: {str(e)[:120]})")


def gerador_roteiro():
    from core import roteiro as RT
    s = load_settings()
    if s.get("llm_provider") == "nenhum":
        st.warning("Configure a IA de texto em **APIs e configurações** (recomendado: Claude/Anthropic).")
    elif s.get("llm_provider") != "anthropic":
        st.info("Funciona com a IA configurada, mas as skills foram pensadas para o **Claude** — ele segue melhor os guias.")
    with st.container(border=True):
        st.markdown("#### ✨ Gerar roteiro")
        campo("gr_tema", area=True, label="Sobre o que é o vídeo?", height=90,
             placeholder="Ex: a queda de Bernardo Provenzano, o chefão que comandou a máfia escondido por 43 anos")
        c1, c2, c3 = st.columns(3)
        bind("gr_idioma", c1.selectbox, "Idioma", options=list(RT.IDIOMAS))
        bind("gr_minutos", c2.slider, "Duração (minutos)", min_value=2, max_value=60)
        bind("gr_tom", c3.selectbox, "Estilo", options=RT.TONS)
        palavras = int(J("gr_minutos") * RT.IDIOMAS.get(J("gr_idioma"), 150))
        st.caption(f"≈ {palavras:,} palavras narradas".replace(",", "."))
        c1, c2 = st.columns(2)
        campo("gr_publico", onde=c1, label="Público (opcional)", placeholder="Ex: adultos que curtem história e true crime")
        bind("gr_pesquisa", c2.toggle, "🔎 Pesquisar fatos na web antes de escrever",
             help="O Claude pesquisa datas, nomes e lugares para não errar (custa um pouco a mais por pesquisa).")
        with st.expander("📎 Adaptar de um vídeo de referência (transcrição)"):
            campo("gr_referencia", area=True, label="Cole a transcrição do vídeo que viralizou (pode ser em outro idioma)",
                 height=150, help="Serve de inspiração para estrutura, ritmo e ganchos. O roteiro sai original e no idioma escolhido.")
        campo("gr_extras", label="Pedidos extras (opcional)",
             placeholder="Ex: começar no julgamento de 1986, terminar com gancho para a parte 2")
        skills = RT.listar_skills()
        ids = [k["id"] for k in skills]
        atuais = [x for x in (J("skills_ativas") or []) if x in ids]
        st.session_state["job"]["skills_ativas"] = atuais
        if "w_skills_ativas" in st.session_state:
            st.session_state["w_skills_ativas"] = [x for x in st.session_state["w_skills_ativas"] if x in ids]
        bind("skills_ativas", st.multiselect, "🧠 Skills que o roteirista deve seguir", options=ids,
             format_func=lambda i: next((k["nome"] for k in skills if k["id"] == i), i))
        b1, b2 = st.columns([2, 1])
        gerar = b1.button("✨ GERAR ROTEIRO", type="primary", use_container_width=True) and _tem(J("gr_tema"), "Escreva o tema e clique em ✓ Confirmar.")
        if gerar:
            params = {"tema": J("gr_tema"), "titulo": J("titulo"), "idioma": J("gr_idioma"), "minutos": J("gr_minutos"),
                      "tom": J("gr_tom"), "publico": J("gr_publico"), "referencia": J("gr_referencia"),
                      "extras": J("gr_extras"), "pesquisa": J("gr_pesquisa"), "skills": J("skills_ativas")}
            try:
                with st.spinner(f"O roteirista está escrevendo ~{palavras} palavras… (pode levar de 1 a 4 minutos)"):
                    st.session_state["roteiro_gerado"] = RT.gerar(params)
            except Exception as e:
                st.error(f"Não consegui gerar: {e}")
        hist = RT.historico()
        if hist and b2.button("🕘 Último gerado", use_container_width=True):
            st.session_state["roteiro_gerado"] = hist[0]

    mostrar_resultado_roteiro()

    with st.expander("🧠 Gerenciar skills do roteirista"):
        st.caption("Skills são guias em Markdown (SKILL.md) que o roteirista sempre segue. Dá para importar as que você "
                   "criou no Claude: no claude.ai, abra a skill e baixe o .zip, ou copie o texto para um arquivo .md.")
        for k in RT.listar_skills():
            c1, c2 = st.columns([5, 1])
            c1.markdown(f"**{k['nome']}**  \n<small>{k['descricao']}</small>", unsafe_allow_html=True)
            if c2.button("🗑️", key=f"rmsk_{k['id']}"):
                RT.remover_skill(k["id"])
                st.rerun()
        up = st.file_uploader("Importar skill (.md ou .zip)", type=["md", "zip"], key="up_skill")
        if up is not None and st.button("📥 Importar skill"):
            try:
                sid = RT.importar_skill(up.name, up.getvalue())
                st.success(f"Skill **{sid}** importada!")
                st.rerun()
            except Exception as e:
                st.error(str(e))


def mostrar_resultado_roteiro():
    from core import roteiro as RT
    r = st.session_state.get("roteiro_gerado")
    if r:
        with st.container(border=True):
            st.markdown(f"#### 📜 Roteiro gerado — {r.get('palavras', 0)} palavras · ≈ {r.get('minutos', 0)} min")
            o = r.get("originalidade")
            if o and o.get("semelhanca", -1) >= 0:
                sem = o["semelhanca"]
                (st.success if sem <= 30 else st.warning)(
                    f"{'✅' if sem <= 30 else '⚠️'} Semelhança com o vídeo de referência: **{sem}%** — {o.get('veredito', '')}")
                st.progress(min(1.0, sem / 100), text="0% = totalmente original · 100% = tradução")
            titulos = r.get("titulos") or ["(sem título sugerido)"]
            esc = st.radio("Escolha o título", titulos, key="gr_titulo_escolhido")
            texto = st.text_area("Roteiro (pode editar antes de usar)", r["roteiro"], height=320, key="gr_texto_" + r.get("quando", ""))
            if r.get("notas"):
                with st.expander("🗒️ Estrutura e fontes"):
                    st.markdown(r["notas"])
            c1, c2 = st.columns([1, 1])
            if c1.button("✅ Usar este roteiro e título", type="primary", use_container_width=True):
                pend = {"titulo": esc.lstrip("⭐ ").strip(), "roteiro": texto}
                idi = (r.get("params") or {}).get("idioma")
                if idi:
                    from core.adaptar import IDIOMA_SEO
                    pend["seo_idioma"] = IDIOMA_SEO.get(idi, "Automático (mesmo do roteiro)")
                if st.session_state.get("pagina") != "Novo vídeo":
                    pend["modo_roteiro"] = "Já tenho"
                    st.session_state["pagina"] = "Novo vídeo"
                    st.session_state["etapa_aberta"] = "narracao"
                    st.session_state.setdefault("etapas_ok", set()).add("roteiro")
                st.session_state["_pending"] = pend
                st.toast("✓ Roteiro e título aplicados")
                st.rerun()
            with c2:
                pedido = st.text_input("Ajustar (ex: mais tenso, encurte para 8 min, final mais forte)", key="gr_pedido")
                if st.button("🔄 Reescrever com esse ajuste", use_container_width=True) and _tem(pedido, "Escreva o ajuste que você quer."):
                    try:
                        with st.spinner("Reescrevendo…"):
                            st.session_state["roteiro_gerado"] = RT.ajustar({**r, "roteiro": texto}, pedido, J("skills_ativas"))
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))



def adaptador_roteiro():
    from core import adaptar as AD, roteiro as RT
    with st.container(border=True):
        st.markdown("#### 🌍 Dobra para outro idioma")
        st.caption("Cole o link de um vídeo de referência (ex.: de um canal novo em alta). O programa aproveita só a "
                   "estrutura do canal e o Claude escreve uma versão nova, com outro ângulo, no idioma escolhido.")
        campo("ad_link", label="Link do vídeo", placeholder="https://www.youtube.com/watch?v=…")
        if st.button("🔎 Buscar vídeo e transcrição") and _tem(J("ad_link"), "Cole o link e clique em ✓ Confirmar."):
            try:
                with st.spinner("Buscando…"):
                    info = AD.info_video(J("ad_link"))
                    st.session_state["ad_info"] = info
                    tr = AD.transcricao(J("ad_link"))
                    st.session_state["ad_texto"] = tr["texto"]
                    st.session_state["ad_texto_area"] = tr["texto"]
                    st.toast(f"✓ Transcrição baixada ({tr['palavras']} palavras, idioma {tr['idioma']})")
            except Exception as e:
                st.error(str(e))
        info = st.session_state.get("ad_info")
        if info and info.get("titulo"):
            c1, c2 = st.columns([1, 4], vertical_alignment="center")
            if info.get("thumb"):
                c1.image(info["thumb"], use_container_width=True)
            c2.markdown(f"**{info['titulo']}**  \n{info.get('canal', '')}")
        st.text_area("Transcrição (pode colar manualmente se o vídeo não tiver legenda)", height=150, key="ad_texto_area")
        texto = st.session_state.get("ad_texto_area", "")
        if texto:
            st.caption(f"{len(texto.split())} palavras na transcrição")
        c1, c2 = st.columns([1, 1])
        bind("ad_idioma", c1.selectbox, "Fazer a dobra para", options=list(RT.IDIOMAS))
        bind("ad_minutos", c2.number_input, "Duração (min) · 0 = igual ao original", min_value=0, max_value=90, step=1)
        angs = list(AD.ANGULOS)
        if J("ad_angulo") not in angs:
            st.session_state["job"]["ad_angulo"] = angs[0]
            st.session_state.pop("w_ad_angulo", None)
        bind("ad_angulo", st.selectbox, "Ângulo da nova versão", options=angs,
             help="A dobra mantém só a ESTRUTURA do canal (gancho, blocos, ritmo, viradas). A história é contada por outro ângulo.")
        st.caption("🎯 " + AD.ANGULOS[J("ad_angulo")])
        campo("ad_extras", label="Pedidos extras (opcional)", placeholder="Ex: público alemão, tom mais sombrio, foco na investigação")
        st.info("**Como funciona a dobra:** 1) o Claude lê o vídeo e extrai só a **estrutura** do canal (sem o conteúdo); "
                "2) escreve um roteiro **novo**, com outro ângulo e detalhes que não estão no original; 3) confere a "
                "**originalidade** e, se ficar parecido demais (acima de 30%), reescreve sozinho. Nada é traduzido.")
        b1, b2 = st.columns([2, 1])
        if b1.button("🌍 FAZER A DOBRA", type="primary", use_container_width=True, disabled=len(texto.split()) < 30):
            try:
                with st.status(f"Fazendo a dobra para {J('ad_idioma')}… (2 a 6 minutos)", expanded=True) as stt:
                    st.session_state["roteiro_gerado"] = AD.adaptar(
                        texto, J("ad_idioma"), J("ad_angulo"), J("ad_minutos") or None, (info or {}).get("titulo", ""),
                        J("skills_ativas"), J("ad_extras"), J("gr_pesquisa"), log=st.write)
                    o = st.session_state["roteiro_gerado"].get("originalidade", {})
                    stt.update(label=f"Dobra pronta · semelhança com o original: {o.get('semelhanca', '?')}%", state="complete")
            except Exception as e:
                st.error(f"Não consegui adaptar: {e}")
        if b2.button("➕ Mandar link para a fila", use_container_width=True,
                     help="A fila baixa a transcrição, adapta e gera o vídeo sozinha, usando as opções atuais.") and \
                _tem(J("ad_link"), "Cole o link e clique em ✓ Confirmar."):
            from core import fila as FL
            FL.adicionar(dict(st.session_state["job"]), tipo="link", link=J("ad_link"), nome=(info or {}).get("titulo", ""))
            st.toast("✓ Link adicionado à fila")
    mostrar_resultado_roteiro()


NOMES_CAMPOS = {"segundos_por_cena": "Segundos por cena", "transicao": "Transição", "duracao_transicao": "Duração da transição (s)",
                "movimento": "Movimento", "intensidade_movimento": "Intensidade do movimento", "estilo_visual": "Estilo do vídeo",
                "estilo_personalizado": "Receita do estilo", "pct_banco": "% de cenas do banco", "legendas": "Legendas",
                "estilo_legenda": "Estilo da legenda", "template": "Template", "trilha_modo": "Trilha",
                "trilha_tema": "Clima da trilha", "personagem_fixo": "Personagem fixo", "ref_direcao": "Enquadramento das cenas",
                "velocidade_voz": "Velocidade da narração"}


def referencia_edicao():
    """Cole um vídeo de exemplo: o programa mede a edição e configura o vídeo igual."""
    from core import referencia as R
    res = st.session_state.get("ref_res")
    with st.expander("🎞️ Referência de edição: cole um vídeo e o programa copia o jeito de editar", expanded=bool(res)):
        st.caption("Copia só a **edição** (ritmo dos cortes, transições, movimento, legendas, estilo das imagens, clima "
                   "da trilha), nunca o conteúdo. Vídeos do YouTube são baixados em baixa qualidade só para a análise "
                   "e apagados logo depois. Analisa até os 10 primeiros minutos.")
        st.session_state.setdefault("ref_entrada", J("ref_link"))
        c1, c2 = st.columns([4, 1.3], vertical_alignment="bottom")
        entrada = c1.text_input("Link do vídeo de referência ou caminho do arquivo no PC", key="ref_entrada",
                                placeholder="https://www.youtube.com/watch?v=...  ou  C:\\Users\\voce\\Videos\\exemplo.mp4")
        if c2.button("🔍 Analisar edição", type="primary", use_container_width=True) and _tem(entrada, "Cole o link ou o caminho do vídeo."):
            try:
                with st.status("Analisando a edição...", expanded=True) as stt:
                    res = R.analisar(entrada, log=stt.write)
                    stt.update(label="Análise pronta", state="complete", expanded=False)
                st.session_state["ref_res"] = res
                st.session_state["ref_res_link"] = entrada.strip()
            except Exception as e:
                st.error(str(e))
                return
        if not res:
            return
        m, ia = res["medidas"], res.get("ia") or {}
        if res["info"].get("titulo"):
            st.markdown(f"**{res['info']['titulo']}**" + (f" · {res['info']['canal']}" if res["info"].get("canal") else ""))
        k = st.columns(4)
        k[0].metric("Duração média do plano", f"{m['plano_medio']} s",
                    help=f"No 1º minuto: {m.get('plano_medio_1min')} s" if m.get("plano_medio_1min") else None)
        k[1].metric("Trocas de imagem", f"{m['cortes_por_minuto']}/min")
        k[2].metric("Cortes secos · dissolves", f"{m['cortes_secos']} · {m['dissolves']}",
                    f"{m['fades_preto']} pelo preto" if m["fades_preto"] else None, delta_color="off")
        k[3].metric("Movimento", "parado" if m["movimento"] < 0.15 else
                    ("suave" if m["movimento"] < R.LIM_SUAVE else ("médio" if m["movimento"] < R.LIM_MEDIA else "forte")))
        if res.get("quadros"):
            cols = st.columns(min(8, len(res["quadros"])))
            for c, q in zip(cols, res["quadros"]):
                if Path(q).exists():
                    c.image(q, use_container_width=True)
        if ia.get("observacoes"):
            st.markdown("**O que a IA notou na edição:**\n" + "\n".join(f"- {o}" for o in ia["observacoes"]))
        elif not ia:
            st.caption("Sem IA de texto configurada (ou ela não aceita imagens): usei só as medições. Com o Claude, "
                       "o programa também reconhece o estilo das imagens, as legendas e o clima da trilha.")
        st.markdown("**Vai ser aplicado no seu vídeo** (desmarque o que não quiser):")
        escolhas = {}
        for i, (campo_, valor, motivo) in enumerate(res["sugestoes"]):
            v = ("sim" if valor else "não") if isinstance(valor, bool) else valor
            if st.checkbox(f"**{NOMES_CAMPOS.get(campo_, campo_)}** → {v}  ·  _{motivo}_", True, key=f"refsug_{i}"):
                escolhas[campo_] = valor
        if st.button("✓ Aplicar no vídeo", type="primary"):
            escolhas["ref_link"] = st.session_state.get("ref_res_link", "")
            st.session_state["_pending"] = escolhas
            st.toast(f"{len(escolhas) - 1} configurações aplicadas a partir da referência")
            st.rerun()


def galeria_estilos(pb: int):
    """Galeria dos estilos de vídeo com miniatura. O estilo escolhido vai em todas as imagens geradas."""
    from core import estilos as ES
    atual = J("estilo_visual")
    with st.container(border=True, key="galeria_estilos"):
        st.markdown("#### 🎨 Estilo do vídeo")
        st.caption("Todas as imagens geradas por IA (cenas e thumbnail) saem neste estilo.")
        nomes = list(ES.ESTILOS)
        for linha in range(0, len(nomes), 4):
            cols = st.columns(4)
            for col, nome in zip(cols, nomes[linha:linha + 4]):
                with col.container(border=True):
                    mini = ES.miniatura(nome)
                    if mini:
                        st.image(str(mini), use_container_width=True)
                    st.markdown(f"**{'✅ ' if nome == atual else ''}{nome}**")
                    st.caption(ES.ESTILOS[nome]["desc"])
                    if st.button("✓ Selecionado" if nome == atual else "Usar este", key=f"est_{ES.ESTILOS[nome]['slug']}",
                                 type="primary" if nome == atual else "secondary", use_container_width=True,
                                 disabled=nome == atual):
                        pend = {"estilo_visual": nome}
                        if ES.ESTILOS[nome].get("personagem") and not (J("personagem_fixo") or "").strip():
                            pend["personagem_fixo"] = ES.ESTILOS[nome]["personagem"]
                        st.session_state["_pending"] = pend
                        st.rerun()

        classicos = [n for n in VISUAL_STYLES if n not in ES.ESTILOS]
        c1, c2 = st.columns(2)
        with c1:
            opcoes = ["— usar a galeria acima —"] + classicos
            idx = opcoes.index(atual) if atual in classicos else 0
            esc = st.selectbox("Outros estilos (sem miniatura)", opcoes, index=idx, key=f"est_classico_{atual}")
            if esc != opcoes[0] and esc != atual:
                st.session_state["_pending"] = {"estilo_visual": esc}
                st.rerun()
        with c2:
            if atual == "Personalizado":
                campo("estilo_personalizado", label="Descreva o estilo (em inglês funciona melhor)")
        campo("personagem_fixo", label="Personagem principal fixo (opcional)",
              help="Descreva o personagem que deve aparecer igual em todas as cenas (roupa, cabelo, idade). "
                   "Ex.: an old fisherman with a grey beard, yellow raincoat and wool cap")
        with st.expander("Ver a receita do estilo (o que vai junto de cada prompt)"):
            st.code(J("estilo_personalizado") if atual == "Personalizado" else VISUAL_STYLES.get(atual, ""), language=None)
            if ES.info(atual).get("direcao"):
                st.caption("Direção para as cenas: " + ES.info(atual)["direcao"])
        if pb > 0 and ES.eh_desenhado(atual):
            st.warning(f"**{atual}** é um estilo desenhado, e as imagens do banco são fotos e vídeos reais. "
                       f"As {pb}% de cenas do banco vão destoar do estilo.")
            if st.button("🤖 Usar 100% IA para manter o estilo em todas as cenas", key="est_100ia"):
                st.session_state["_pending"] = {"pct_banco": 0}
                st.rerun()


def secao_templates():
    from core import templates as TP
    st.markdown("#### 🎨 Template do vídeo")
    st.caption("Muda a abertura com o título, o encerramento, a moldura, as cores do vídeo e o estilo da legenda.")
    atual = J("template") if J("template") in TP.TEMPLATES else "Nenhum"
    pasta_prev = C.DATA_DIR / "previas_templates"
    nomes = list(TP.TEMPLATES)
    for linha in range(0, len(nomes), 4):
        cols = st.columns(4)
        for col, nome in zip(cols, nomes[linha:linha + 4]):
            with col.container(border=True):
                try:
                    st.image(str(TP.previa(nome, pasta_prev)), use_container_width=True)
                except Exception as e:
                    st.caption(f"(prévia indisponível: {e})")
                st.markdown(f"**{'✅ ' if nome == atual else ''}{nome}**")
                st.caption(TP.TEMPLATES[nome]["desc"])
                if st.button("✓ Selecionado" if nome == atual else "Usar este", key=f"tpl_{nome}",
                             type="primary" if nome == atual else "secondary", use_container_width=True,
                             disabled=nome == atual):
                    st.session_state["_pending"] = {"template": nome}
                    st.rerun()
    if atual != "Nenhum":
        from core import previas as PV
        with st.container(border=True):
            st.markdown(f"**▶ {atual} em movimento** — abertura, cenas, legenda e encerramento")
            if st.session_state.get("tpl_video_de") == atual:
                previa_video(PV.template, atual, J("titulo").strip() or "O Último Chefão de Palermo",
                             J("template_rotulo") or "DOCUMENTÁRIO", J("estilo_legenda"),
                             legenda=f"Exemplo do template {atual} (vídeo de 7 segundos)")
            elif st.button("▶ Ver exemplo em vídeo", type="primary", key=f"tplv_{atual}"):
                st.session_state["tpl_video_de"] = atual
                st.rerun()
        with st.container(border=True):
            st.markdown(f"**Ajustes do template {atual}**")
            c1, c2 = st.columns(2)
            with c1:
                bind("template_abertura", st.toggle, "Abertura com o título")
                if J("template_abertura"):
                    campo("template_rotulo", label="Rótulo pequeno acima do título", help="Ex: DOCUMENTÁRIO · EP. 01, CASO REAL, PARTE 2")
                    bind("template_dur_abertura", st.slider, "Duração da abertura (s)", min_value=2.0, max_value=8.0, step=0.5)
                bind("template_encerramento", st.toggle, "Encerramento no fim do vídeo")
                if J("template_encerramento"):
                    campo("template_fim", label="Texto do encerramento")
                    campo("template_fim_sub", label="Linha de baixo do encerramento")
            with c2:
                bind("template_moldura", st.toggle, "Moldura / efeito de borda")
                bind("template_cor", st.toggle, "Tratamento de cor do template")
                bind("template_legenda", st.toggle, "Legenda com fonte e cores do template")
                if st.button("👁️ Ver a abertura com o meu título"):
                    if J("titulo").strip():
                        st.image(str(TP.previa(atual, pasta_prev, J("titulo"), J("template_rotulo"))), use_container_width=True)
                    else:
                        st.warning("Escreva o título na aba Roteiro primeiro.")


def aba_trilha():
    from core import trilha as TR
    modos = ["Automático", "Tema", "Arquivo ou pasta", "Sem música"]
    rot = {"Automático": "🤖 Automático (a IA escolhe o clima pelo roteiro)", "Tema": "🎚️ Escolher o tema",
           "Arquivo ou pasta": "📁 Arquivo ou pasta específica", "Sem música": "🔇 Sem música"}
    bind("trilha_modo", st.radio, "Trilha sonora", options=modos, format_func=rot.get, horizontal=True)
    cont = TR.contagem()
    if J("trilha_modo") == "Tema":
        bind("trilha_tema", st.selectbox, "Tema da trilha", options=list(TR.TEMAS),
             format_func=lambda t: f"{TR.TEMAS[t][1]} {t} ({cont[t]} músicas)")
        if cont[J("trilha_tema")] == 0:
            st.warning("Esse tema ainda não tem músicas. Adicione na Biblioteca de trilhas aqui embaixo.")
    elif J("trilha_modo") == "Automático":
        st.caption("A IA lê o roteiro e escolhe entre os temas que têm músicas na sua biblioteca.")
    elif J("trilha_modo") == "Arquivo ou pasta":
        campo("musica", label="Arquivo ou pasta de músicas", placeholder=r"C:\Músicas\minha_trilha.mp3")
    if J("trilha_modo") != "Sem música":
        bind("volume_musica", st.slider, "Volume da música", min_value=0.02, max_value=0.5, step=0.01)
        st.caption("A música abaixa sozinha quando a narração fala (ducking), tem fade entre faixas e no fim do vídeo. "
                   "Os créditos das faixas que pedem atribuição entram sozinhos na descrição.")

    st.markdown("#### 📚 Biblioteca de trilhas")
    cols = st.columns(4)
    for i, (t, (_, ic, _h)) in enumerate(TR.TEMAS.items()):
        cols[i % 4].markdown(f'<div class="av-card" style="min-height:0;padding:.7rem .9rem;margin-bottom:.6rem">'
                             f'<span style="font-size:1.4rem">{ic}</span> <b style="display:inline">{t}</b><br>'
                             f'<span>{cont[t]} música(s)</span></div>', unsafe_allow_html=True)
    with st.expander("➕ Adicionar músicas da Biblioteca de Áudio do YouTube", expanded=sum(cont.values()) == 0):
        st.markdown("1. Abra a **Biblioteca de áudio** no YouTube Studio (menu lateral → *Biblioteca de áudio*).\n"
                    "2. Filtre por **Humor** (sugestão abaixo), ouça e baixe as faixas.\n"
                    "3. Arraste os arquivos aqui, escolha o tema e clique em importar. Faz isso uma vez só — depois o programa usa sozinho.")
        st.link_button("🎵 Abrir Biblioteca de Áudio do YouTube", TR.LINK_BIBLIOTECA)
        tema_imp = st.selectbox("Tema dessas músicas", list(TR.TEMAS),
                                format_func=lambda t: f"{TR.TEMAS[t][1]} {t} — no YouTube filtre por Humor: {TR.TEMAS[t][2]}")
        arqs = st.file_uploader("Arquivos de música", type=["mp3", "wav", "m4a", "ogg", "flac"], accept_multiple_files=True)
        atrib = st.text_area("Atribuição (se a faixa pedir — aparece com o ícone de Creative Commons no YouTube)",
                             placeholder='Ex: "Nome da faixa" por Artista — Licença CC BY 4.0', height=70)
        if st.button("📥 Importar para a biblioteca", disabled=not arqs):
            for a in arqs:
                TR.importar(a.name, a.getvalue(), tema_imp, atrib)
            st.success(f"{len(arqs)} música(s) importadas em {tema_imp}!")
            st.rerun()
        pasta_imp = st.text_input("…ou importar uma pasta inteira do PC para esse tema", placeholder=r"C:\Users\Voce\Downloads\musicas_dark")
        if st.button("📂 Importar pasta") and _tem(pasta_imp, "Cole o caminho da pasta."):
            try:
                n = TR.importar_pasta(pasta_imp, tema_imp)
                st.success(f"{n} música(s) importadas em {tema_imp}!")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    with st.expander("🎧 Ouvir e gerenciar músicas"):
        tv = st.selectbox("Tema", list(TR.TEMAS), key="tema_ver", format_func=lambda t: f"{TR.TEMAS[t][1]} {t} ({cont[t]})")
        cred = TR.creditos(tv)
        for f in TR.listar(tv):
            c1, c2, c3 = st.columns([3, 4, 1])
            c1.markdown(f"**{f.stem}**" + (f"<br><small>{cred[f.name]}</small>" if f.name in cred else ""), unsafe_allow_html=True)
            c2.audio(str(f))
            if c3.button("🗑️", key=f"rm_{tv}_{f.name}"):
                TR.remover(tv, f.name)
                st.rerun()


@st.fragment(run_every=2)
def painel_ao_vivo(job_dir: Path):
    pr = read_progress(job_dir)
    st.subheader(f"Progresso — {job_dir.name}")
    if not pr:
        st.info("Iniciando...")
        return
    if pr["status"] not in ("rodando", "pausado"):
        st.rerun()  # terminou: recarrega a página para mostrar o vídeo
    from core.utils import processo_vivo
    if not processo_vivo(pr.get("pid")):
        st.error("⚠️ O processo de geração parou sem terminar (o PC pode ter suspendido ou houve um erro). "
                 "Nada do que já ficou pronto foi perdido.")
        txt = job_dir / "saida_terminal.txt"
        if txt.exists():
            with st.expander("Ver detalhes do erro"):
                st.code(txt.read_text(encoding="utf-8", errors="replace")[-3000:], language=None)
        if st.button("🔁 Continuar de onde parou", type="primary", key=f"morto{job_dir.name}"):
            start_job(job_dir)
            st.rerun()
        return
    ctrl = {}
    try:
        cp = job_dir / "controle.json"
        ctrl = json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else {}
    except Exception:
        pass
    pausado = pr["status"] == "pausado"
    pedindo_pausa = ctrl.get("pausado") and not pausado
    if pausado:
        st.warning(f"⏸️ Pausado em: {pr['etapa']} ({pr['pct']:.0f}%)")
    elif pedindo_pausa:
        st.info("⏳ Pausando… termina a cena atual e para (alguns segundos).")
    st.progress(min(1.0, pr["pct"] / 100), text=f"{pr['etapa']} ({pr['pct']:.0f}%)")
    b1, b2, b3, _ = st.columns([1, 1, 1.2, 0.8])
    if b3.button("🗂️ Abrir projeto", use_container_width=True, key=f"proj{job_dir.name}"):
        abrir_projeto(job_dir)
    if pausado or pedindo_pausa:
        if b1.button("▶️ Retomar", type="primary", use_container_width=True, key=f"res{job_dir.name}"):
            controle(job_dir, pausado=False)
            st.rerun(scope="fragment")
    else:
        if b1.button("⏸️ Pausar", use_container_width=True, key=f"pau{job_dir.name}"):
            controle(job_dir, pausado=True)
            st.rerun(scope="fragment")
    if b2.button("⏹️ Cancelar", use_container_width=True, key=f"can{job_dir.name}"):
        controle(job_dir, cancelar=True)
        st.rerun(scope="fragment")
    st.caption("Pausar/cancelar vale a partir do fim da cena ou etapa atual. "
               "Na junção final do vídeo pode levar alguns minutos para responder.")
    with st.expander("Log detalhado"):
        st.code("\n".join(pr["log"][-60:]), language=None)


def painel_revisao(job_dir: Path, pr: dict, key=""):
    job = json.loads((job_dir / "trabalho.json").read_text(encoding="utf-8"))
    st.subheader(f"👀 Revise o vídeo — {job['titulo']}")
    st.caption("O vídeo ainda NÃO foi exportado. Assista, confira a thumbnail e o relatório, e só depois exporte.")
    previa = job_dir / "previa.mp4"
    final = job_dir / "video_final.mp4"
    c1, c2 = st.columns([2.2, 1])
    with c1:
        st.video(str(previa if previa.exists() else final))
        if previa.exists():
            st.caption("Prévia em 720p para carregar rápido. O arquivo exportado sai em 1080p.")
        q1, q2 = st.columns(2)
        if q1.button("▶ Abrir em tela cheia no player do PC (1080p)", key=f"play{key}{job_dir.name}", use_container_width=True):
            open_folder(str(final))
        if q2.button("🗂️ Abrir projeto (ver e trocar cenas)", key=f"proj{key}{job_dir.name}", use_container_width=True):
            abrir_projeto(job_dir)
    with c2:
        thumb = job_dir / "thumbnail.jpg"
        if thumb.exists():
            st.markdown("**Thumbnail**")
            st.image(str(thumb), use_container_width=True)
        rel = job_dir / "relatorio.json"
        items = json.loads(rel.read_text(encoding="utf-8")) if rel.exists() else []
        st.markdown("**Relatório do agente de revisão**")
        if items:
            st.warning("\n".join(f"- {x}" for x in items))
        else:
            st.success("Nenhum problema encontrado ✔")
        try:
            from core.utils import duration
            st.metric("Duração", f"{duration(final) / 60:.1f} min")
        except Exception:
            pass
    seo_f = job_dir / "seo.json"
    if seo_f.exists():
        st.divider()
        r = json.loads(seo_f.read_text(encoding="utf-8"))
        d_txt = job_dir / "descricao.txt"
        if d_txt.exists():  # mostra a versão editada, se houver
            r = dict(r)
            r["_editada"] = d_txt.read_text(encoding="utf-8")
        painel_seo(r, f"{key}{job_dir.name}", job_dir)
    st.divider()
    pasta = st.text_input("Exportar para a pasta", job["pasta_saida"], key=f"dest{key}{job_dir.name}")
    gerado = job.get("resolucao", "1080p (Full HD)")
    opcoes_res = list(C.RESOLUCOES)
    res_exp = st.radio("Exportar em", opcoes_res, index=opcoes_res.index(gerado) if gerado in opcoes_res else 0,
                       horizontal=True, key=f"res{key}{job_dir.name}",
                       format_func=lambda r: r + (" — como foi gerado" if r == gerado else
                                                  (" — ampliado do 1080p" if r.startswith("2K") else " — reduzido do 2K")))
    if res_exp != gerado:
        st.caption("A conversão leva alguns minutos. Para 2K com o máximo de nitidez, gere o vídeo já em 2K (aba Exportar).")
    if st.button("📤 Publicar / agendar no YouTube", key=f"pub{key}{job_dir.name}"):
        st.session_state["publicar_job"] = str(job_dir)
        st.session_state["pagina"] = "Publicar no YouTube"
        st.rerun()
    b1, b2, b3 = st.columns([2, 1, 1])
    if b1.button("✅ APROVAR E EXPORTAR", type="primary", use_container_width=True, key=f"exp{key}{job_dir.name}"):
        from core.pipeline import exportar
        try:
            editada = st.session_state.get(f"desc_{key}{job_dir.name}")
            if editada and (job_dir / "seo.json").exists():
                (job_dir / "descricao.txt").write_text(editada, encoding="utf-8")
            with st.spinner("Exportando..." if res_exp == gerado else f"Convertendo para {res_exp} e exportando..."):
                out = exportar(job_dir, pasta, resolucao=res_exp)
            p = job_dir / "progresso.json"
            d = json.loads(p.read_text(encoding="utf-8"))
            d.update(status="concluido", etapa="Exportado ✔", saida=str(out))
            p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
            st.rerun()
        except Exception as e:
            st.error(f"Não consegui exportar: {e}")
    if b2.button("✏️ Ajustar e gerar de novo", use_container_width=True, key=f"adj{key}{job_dir.name}"):
        set_job(job)
        st.session_state["pagina"] = "Novo vídeo"
        st.rerun()
    confirma = b3.checkbox("Confirmo descartar", key=f"cdel{key}{job_dir.name}")
    if b3.button("🗑️ Descartar", use_container_width=True, disabled=not confirma, key=f"del{key}{job_dir.name}"):
        import shutil
        shutil.rmtree(job_dir, ignore_errors=True)
        if st.session_state.get("job_ativo") == str(job_dir):
            st.session_state.pop("job_ativo")
        st.rerun()


def painel_seo(r: dict, key: str, job_dir: Path = None):
    """Mostra/edita descrição, hashtags e palavras-chave."""
    from core import seo as SEO
    st.markdown("#### 📣 Descrição, hashtags e palavras-chave")
    txt = st.text_area("Descrição pronta para colar no YouTube (pode editar)", r.get("_editada") or SEO.montar_descricao(r),
                       height=300, key=f"desc_{key}")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Hashtags**")
        dem = r.get("demanda_hashtags", {})
        for h in r.get("hashtags", []):
            d = dem.get(h)
            extra = f" — {d['videos_30d']:,} vídeos/30 dias · top views ~{d['mediana_views_top']:,}".replace(",", ".") if d else ""
            st.markdown(f"`#{h}`{extra}")
        st.code(" ".join("#" + h for h in r.get("hashtags", [])), language=None)
    with c2:
        buscadas = {b.lower() for b in r.get("buscadas", [])}
        st.markdown(f"**Palavras-chave** ({len(r.get('palavras_chave', []))}) — 🔥 = busca real no YouTube")
        st.markdown(" ".join(f"`{'🔥 ' if k.lower() in buscadas else ''}{k}`" for k in r.get("palavras_chave", [])))
        st.code(", ".join(r.get("palavras_chave", [])), language=None)
    st.caption("Use o ícone de copiar no canto das caixas cinzas para copiar hashtags e palavras-chave.")
    if job_dir is not None:
        b1, b2 = st.columns(2)
        if b1.button("💾 Salvar edição da descrição", key=f"sv_{key}"):
            (Path(job_dir) / "descricao.txt").write_text(txt, encoding="utf-8")
            st.success("Descrição salva — vai junto na exportação.")
        if b2.button("🔄 Gerar outra versão", key=f"rg_{key}"):
            job = json.loads((Path(job_dir) / "trabalho.json").read_text(encoding="utf-8"))
            sc = json.loads((Path(job_dir) / "cenas.json").read_text(encoding="utf-8")) if (Path(job_dir) / "cenas.json").exists() else []
            t = 0.0
            for x in sc:
                x["inicio"] = t
                t += x.get("dur_audio", 0)
            with st.spinner("Gerando..."):
                SEO.salvar(SEO.gerar(job, sc, t), job_dir)
            st.rerun()
    return txt


def painel_final(job_dir: Path, pr: dict, key=""):
    if pr["status"] == "concluido":
        st.success(f"✅ Exportado: {pr['saida']}")
        f1, f2, _ = st.columns([1, 1, 2])
        if f1.button("📂 Abrir pasta", key=f"open{key}{job_dir.name}", use_container_width=True):
            open_folder(str(Path(pr["saida"]).parent))
        if f2.button("🗂️ Abrir projeto", key=f"projf{key}{job_dir.name}", use_container_width=True):
            abrir_projeto(job_dir)
        if st.button("📤 Publicar / agendar no YouTube", key=f"pubf{key}{job_dir.name}"):
            st.session_state["publicar_job"] = str(job_dir)
            st.session_state["pagina"] = "Publicar no YouTube"
            st.rerun()
    else:
        (st.warning if pr["status"] == "cancelado" else st.error)(pr["etapa"])
        if st.button("🗂️ Abrir projeto", key=f"proje{key}{job_dir.name}"):
            abrir_projeto(job_dir)
        if st.button("🔁 Continuar de onde parou", key=f"retry{key}{job_dir.name}"):
            start_job(job_dir)
            st.rerun()
    with st.expander("Log detalhado"):
        st.code("\n".join(pr["log"][-60:]), language=None)


# ================================================================== DOBRA DE CANAIS
def page_dobra():
    aplicar_pendentes()
    hero("🌍", "Dobra de canais", "Leve um canal em alta para outro idioma: mesma estrutura, roteiro novo com outro ângulo.")
    cartoes([("🧭", "1. Estrutura", "Lê o vídeo de referência e extrai só a fórmula do canal"),
              ("✍️", "2. Versão nova", "Outro ângulo, detalhes novos, no idioma escolhido"),
              ("🛡️", "3. Originalidade", "Confere a semelhança e reescreve se passar de 30%"),
              ("🎬", "4. Vídeo", "Use no Novo vídeo ou mande para a Fila")])
    st.write("")
    adaptador_roteiro()
    if st.session_state.get("roteiro_gerado"):
        st.caption("Clique em **✅ Usar este roteiro e título** para continuar no Novo vídeo (a narração já abre em seguida).")
    with st.expander("📋 Tem vários vídeos para dobrar?"):
        st.markdown("Na **Fila de vídeos**, aba **Links para dobra**, cole vários links (um por linha). O programa faz a "
                    "dobra de cada um e gera os vídeos em sequência, sozinho.")
        if st.button("Ir para a Fila de vídeos →"):
            st.session_state["pagina"] = "Fila de vídeos"
            st.rerun()


# ================================================================== FILA DE VÍDEOS
FILA_ST = {"na fila": ("⏳", "Na fila"), "preparando roteiro": ("✍️", "Escrevendo roteiro"), "gerando": ("🎬", "Gerando"),
           "pronto": ("👀", "Pronto — revisar"), "exportado": ("✅", "Exportado"), "erro": ("❌", "Erro"),
           "cancelado": ("⏹️", "Cancelado")}
FILA_TIPO = {"pronto": "📝 Roteiro pronto", "tema": "✨ Tema (IA escreve)", "link": "🌍 Dobra de link"}


def page_fila():
    from core import fila as FL
    hero("📋", "Fila de vídeos", "Todos os seus vídeos num lugar só: acompanhe, abra o projeto e produza vários em sequência.")
    aberto = st.session_state.get("projeto_aberto")
    if aberto and Path(aberto).exists():
        with st.container(key="projeto_aberto_box", border=True):
            c1, c2 = st.columns([5, 1], vertical_alignment="center")
            c1.markdown(f"### 🗂️ Projeto aberto · {Path(aberto).name.split('_', 2)[-1].replace('_', ' ')}")
            if c2.button("✕ Fechar projeto", use_container_width=True):
                st.session_state.pop("projeto_aberto", None)
                st.rerun()
            pr = read_progress(Path(aberto)) or {}
            if pr.get("status") in ("rodando", "pausado"):
                grade_ao_vivo(Path(aberto))
            else:
                grade_projeto(Path(aberto), editavel=True)
    lista_fila()
    st.markdown("### ➕ Adicionar vários de uma vez")
    base_ops = ["Opções atuais do Novo vídeo"] + sorted(p.stem for p in C.PROFILES_DIR.glob("*.json"))
    c1, c2 = st.columns([2, 1], vertical_alignment="bottom")
    base = c1.selectbox("Usar as opções de", base_ops, help="Voz, visual, template, trilha… de onde vêm as configurações dos vídeos.")
    auto = c2.toggle("Exportar sem revisar", help="Ligado: cada vídeo vai direto para a pasta. Desligado: fica esperando você assistir e aprovar.")

    def job_base():
        if base == base_ops[0]:
            return dict(st.session_state["job"])
        d = default_job()
        d.update(json.loads((C.PROFILES_DIR / f"{base}.json").read_text(encoding="utf-8")))
        return d

    t1, t2, t3 = st.tabs(["📝 Roteiros prontos", "✨ Temas (a IA escreve)", "🌍 Links para dobra"])
    with t1:
        st.caption("Um vídeo por bloco: **primeira linha = título**, depois o roteiro. Separe os vídeos com uma linha só com `---`.")
        with st.form("fila_prontos", border=False):
            txt = st.text_area("Roteiros", height=220, placeholder="Título do vídeo 1\nTexto do roteiro…\n---\nTítulo do vídeo 2\nTexto…")
            ok = st.form_submit_button("✓ Adicionar à fila")
        if ok:
            n = 0
            for bloco in re.split(r"^\s*---\s*$", txt, flags=re.M):
                linhas = bloco.strip().splitlines()
                if len(linhas) >= 2:
                    j = job_base()
                    j["titulo"], j["roteiro"] = linhas[0].strip(), "\n".join(linhas[1:]).strip()
                    FL.adicionar(j, "pronto", exportar_auto=auto)
                    n += 1
            st.toast(f"✓ {n} vídeo(s) adicionados") if n else st.warning("Não encontrei nenhum bloco com título + roteiro.")
    with t2:
        st.caption("Um tema por linha. O Claude escreve o roteiro (com as suas skills, idioma, duração e estilo da etapa Roteiro → Gerar com IA) e o vídeo é gerado em seguida.")
        with st.form("fila_temas", border=False):
            txt = st.text_area("Temas", height=160, placeholder="A queda de Bernardo Provenzano\nO julgamento de Al Capone\nO mito de Prometeu")
            ok = st.form_submit_button("✓ Adicionar à fila")
        if ok:
            temas = [t.strip() for t in txt.splitlines() if t.strip()]
            for t in temas:
                FL.adicionar(job_base(), "tema", tema=t, exportar_auto=auto)
            st.toast(f"✓ {len(temas)} tema(s) adicionados")
    with t3:
        st.caption("Um link do YouTube por linha. Para cada um: lê a estrutura do canal, escreve uma versão nova com outro ângulo no idioma escolhido (com checagem de originalidade) e gera o vídeo.")
        from core import roteiro as RT, adaptar as AD
        with st.form("fila_links", border=False):
            txt = st.text_area("Links", height=140, placeholder="https://www.youtube.com/watch?v=…\nhttps://youtu.be/…")
            c1, c2 = st.columns(2)
            idi = c1.selectbox("Fazer a dobra para", list(RT.IDIOMAS), index=list(RT.IDIOMAS).index("English"))
            modo = c2.selectbox("Ângulo da nova versão", list(AD.ANGULOS))
            ok = st.form_submit_button("✓ Adicionar à fila")
        if ok:
            links = [l.strip() for l in txt.splitlines() if l.strip()]
            for l in links:
                j = job_base()
                j.update(ad_idioma=idi, ad_angulo=modo, seo_idioma=AD.IDIOMA_SEO.get(idi, j.get("seo_idioma")))
                FL.adicionar(j, "link", link=l, exportar_auto=auto)
            st.toast(f"✓ {len(links)} link(s) adicionados")
            if links:
                st.caption("Lembre de escolher uma voz que fale o idioma de destino (ex.: ElevenLabs multilingual).")


ESTAGIOS = [("Roteiro", 0), ("Narração", 12), ("Imagens", 30), ("Montagem", 55), ("Finalização", 94)]


def _tempo(seg):
    seg = int(seg or 0)
    return f"{seg // 3600}h {seg % 3600 // 60:02d} min" if seg >= 3600 else f"{seg // 60} min {seg % 60:02d} s"


def _info_projeto(jd: Path) -> dict:
    """Números do cartão: duração, cenas, mistura IA/banco."""
    out = {"dur": None, "cenas": None, "prontas": 0, "ia": 0, "banco": 0}
    try:
        sc = json.loads((jd / "cenas.json").read_text(encoding="utf-8"))
        out["cenas"] = len(sc)
        out["dur"] = sum(x.get("dur_audio", 0) for x in sc) or None
        midia = jd / "midia"
        for x in sc:
            tem = (x.get("midia") and Path(x["midia"]).exists()) or (midia.exists() and any(midia.glob(f"c{x['id']:04d}*")))
            out["prontas"] += 1 if tem else 0
            if x.get("fonte") == "banco":
                out["banco"] += 1
            elif tem:
                out["ia"] += 1
    except Exception:
        pass
    return out


def cartao_projeto(n, it, jd, pr):
    """Cartão no estilo 'painel de produção' para um vídeo da fila (ou gerado avulso)."""
    status_fila = it["status"] if it else None
    pst = (pr or {}).get("status")
    if pst == "rodando" or status_fila in ("gerando", "preparando roteiro"):
        badge, cor = ("✍️ ESCREVENDO ROTEIRO", "#F5A524") if status_fila == "preparando roteiro" else ("⟳ EM ANDAMENTO", "#2F7BFF")
    elif pst == "pausado":
        badge, cor = "⏸ PAUSADO", "#F5A524"
    elif pst == "aguardando" or status_fila == "pronto":
        badge, cor = "👀 PRONTO · REVISAR", "#21C354"
    elif pst == "concluido" or status_fila == "exportado":
        badge, cor = "✅ EXPORTADO", "#21C354"
    elif pst == "erro" or status_fila == "erro":
        badge, cor = "❌ ERRO", "#FF4B4B"
    elif pst == "cancelado" or status_fila == "cancelado":
        badge, cor = "⏹ CANCELADO", "#8FA3D1"
    else:
        badge, cor = "⏳ NA FILA", "#8FA3D1"
    pct = (pr or {}).get("pct", 0) if pr else 0
    titulo = (it or {}).get("nome") or (jd.name.split("_", 2)[-1].replace("_", " ") if jd else "Vídeo")
    etapa = (pr or {}).get("etapa", "") if pr else ("aguardando a vez na fila" if status_fila == "na fila" else "")
    tempo = ""
    if pr and pr.get("inicio"):
        fim = pr.get("fim") or time.time()
        tempo = ("feito em " if pr.get("fim") else "") + _tempo(fim - pr["inicio"])
        if not pr.get("fim") and pct > 8:
            resta = (fim - pr["inicio"]) * (100 - pct) / pct
            tempo += f" · faltam cerca de {_tempo(resta)}"
    tipo = FILA_TIPO.get((it or {}).get("tipo"), "🎬 Gerado direto") if it else "🎬 Gerado direto"
    # etapas (pílulas)
    pills = ""
    for i, (nome, ini) in enumerate(ESTAGIOS):
        fim_e = ESTAGIOS[i + 1][1] if i + 1 < len(ESTAGIOS) else 100
        if pct >= fim_e or pst in ("aguardando", "concluido"):
            est, ic = "ok", "✓"
        elif pct >= ini and pst in ("rodando", "pausado"):
            est, ic = "agora", "⟳"
        else:
            est, ic = "", str(i + 1)
        pills += f'<div class="pill {est}">{ic} {nome}</div>'
    info = _info_projeto(jd) if jd and jd.exists() else {}
    dur = f"{int(info['dur'] // 60)}:{int(info['dur'] % 60):02d}" if info.get("dur") else "—"
    cen = f"{info['prontas']} de {info['cenas']}" if info.get("cenas") else "—"
    mix = f"{info['ia']} IA · {info['banco']} banco" if info.get("cenas") else "—"
    html = f"""<div class="pj-top"><div><span class="pj-badge" style="color:{cor};border-color:{cor}55;background:{cor}18">{badge}</span>
<span class="pj-tempo">{tempo}</span><div class="pj-tit">{n}. {titulo[:90]}</div><div class="pj-sub">{tipo} · {etapa[:120]}</div></div>
<div class="pj-pct">{pct:.0f}<small>%</small><span>ETAPA {min(len(ESTAGIOS), sum(1 for _, ini in ESTAGIOS if pct >= ini))} DE {len(ESTAGIOS)}</span></div></div>
<div class="pj-bar"><div style="width:{pct:.0f}%"></div></div><div class="pj-pills">{pills}</div>
<div class="pj-mets"><div><small>⏱ DURAÇÃO</small><b>{dur}</b><span>de narração</span></div><div><small>🎞 CENAS</small><b>{cen}</b><span>prontas</span></div>
<div><small>🖼 IMAGENS</small><b>{mix}</b><span>mistura do vídeo</span></div><div><small>🗓 ADICIONADO</small><b>{(it or {}).get('criado', '—')}</b><span>{'na fila' if it else 'gerado direto'}</span></div></div>"""
    return html


@st.fragment(run_every=3)
def lista_fila():
    from core import fila as FL
    itens = FL.listar()
    ativo = FL.trabalhador_ativo()
    cont = {k: sum(1 for i in itens if i["status"] == k) for k in FILA_ST}
    dirs_fila = {i.get("job_dir") for i in itens if i.get("job_dir")}
    avulsos = [d for d in sorted(C.JOBS_DIR.iterdir(), reverse=True)
               if d.is_dir() and (d / "trabalho.json").exists() and str(d) not in dirs_fila][:12]
    em_andamento = sum(1 for d in avulsos if (read_progress(d) or {}).get("status") in ("rodando", "pausado"))
    c1, c2 = st.columns([3, 2], vertical_alignment="center")
    c1.markdown(f"**FILA** · {cont['gerando'] + cont['preparando roteiro'] + em_andamento} em andamento · "
                f"{cont['na fila']} esperando · {cont['pronto'] + cont['exportado']} pronto(s)")
    b1, b2, b3 = c2.columns(3)
    if ativo:
        if b1.button("⏸ Pausar fila", use_container_width=True, help="Para depois do vídeo atual"):
            FL.pedir_pausa(True)
            st.rerun(scope="fragment")
    elif b1.button("▶ Iniciar fila", type="primary", use_container_width=True, disabled=cont["na fila"] == 0):
        FL.iniciar()
        st.toast("Fila iniciada")
        time.sleep(1)
        st.rerun(scope="fragment")
    if b2.button("🧹 Limpar prontos", use_container_width=True):
        FL.limpar_concluidos()
        st.rerun(scope="fragment")
    if ativo:
        st.caption("▶️ A fila está rodando sozinha" + (" — vai pausar depois do vídeo atual." if FL.pausa_pedida() else
                                                      ". Pode fechar a janela; deixe o PC ligado."))
    linhas = [(it, Path(it["job_dir"]) if it.get("job_dir") else None) for it in itens] + [(None, d) for d in avulsos]
    if not linhas:
        st.info("Nenhum vídeo ainda. Adicione aqui embaixo ou use **➕ Adicionar à fila** / **🚀 GERAR VÍDEO** no Novo vídeo.")
        return
    for n, (it, jd) in enumerate(linhas, 1):
        pr = read_progress(jd) if jd and jd.exists() else None
        k = it["id"] if it else jd.name
        with st.container(key=f"fila_item_{k}"):
            st.markdown(cartao_projeto(n, it, jd, pr), unsafe_allow_html=True)
            bts = st.columns([1.35, 1.1, 1.05, 1.1, 0.55, 0.55, 0.55])
            if jd and jd.exists() and bts[0].button("🗂️ Abrir o projeto", key=f"op_{k}", type="primary", use_container_width=True):
                abrir_projeto(jd)
            if pr and pr.get("status") in ("rodando", "pausado") and jd:
                if pr["status"] == "pausado":
                    if bts[1].button("▶ Retomar", key=f"rt_{k}", use_container_width=True):
                        controle(jd, pausado=False)
                        st.rerun(scope="fragment")
                elif bts[1].button("⏸ Pausar", key=f"pa_{k}", use_container_width=True):
                    controle(jd, pausado=True)
                    st.rerun(scope="fragment")
            elif pr and pr.get("status") in ("erro", "cancelado") and jd and not it:
                if bts[1].button("🔁 Continuar", key=f"ct_{k}", use_container_width=True):
                    start_job(jd)
                    st.rerun(scope="fragment")
            if it and it["status"] in ("erro", "cancelado") and bts[1].button("🔁 Repetir", key=f"rp_{k}", use_container_width=True):
                FL.repetir(it["id"])
                st.rerun(scope="fragment")
            if pr and bts[2].button("📋 Ver log", key=f"lg_{k}", use_container_width=True):
                st.session_state["log_aberto"] = None if st.session_state.get("log_aberto") == k else k
                st.rerun(scope="fragment")
            if jd and jd.exists():
                pasta = Path(pr["saida"]).parent if pr and pr.get("status") == "concluido" and pr.get("saida") else jd
                if bts[3].button("📂 Abrir a pasta", key=f"fd_{k}", use_container_width=True):
                    open_folder(str(pasta))
            if it and it["status"] == "na fila":
                if bts[4].button("▲", key=f"up_{k}", help="Subir na fila"):
                    FL.mover(it["id"], -1)
                    st.rerun(scope="fragment")
                if bts[5].button("▼", key=f"dn_{k}", help="Descer na fila"):
                    FL.mover(it["id"], 1)
                    st.rerun(scope="fragment")
            if it and it["status"] not in ("gerando", "preparando roteiro") and bts[6].button("🗑️", key=f"rm_{k}", help="Tirar da fila"):
                FL.remover(it["id"])
                st.rerun(scope="fragment")
            if it and it.get("erro"):
                st.caption(f"⚠️ {it['erro'][:240]}")
            if st.session_state.get("log_aberto") == k and pr:
                st.code("\n".join(pr.get("log", [])[-40:]), language=None)

# ================================================================== ABRIR PROJETO
STATUS_TXT = {"rodando": "⏳ Gerando", "pausado": "⏸️ Pausado", "aguardando": "👀 Esperando sua aprovação",
              "concluido": "✅ Exportado", "erro": "❌ Parou com erro", "cancelado": "⏹️ Cancelado"}


def page_project():
    hero("🗂️", "Abrir projeto", "Veja, cena por cena, as imagens e clipes do vídeo — e troque o que não gostar.")
    jobs = sorted([d for d in C.JOBS_DIR.iterdir() if d.is_dir() and (d / "trabalho.json").exists()], reverse=True)
    if not jobs:
        st.info("Nenhum projeto ainda. Gere um vídeo em **Novo vídeo**.")
        return
    nomes = [str(d) for d in jobs]
    atual = st.session_state.get("projeto_aberto")
    idx = nomes.index(atual) if atual in nomes else 0

    def rotulo(p):
        pr = read_progress(Path(p)) or {"status": "?"}
        return f"{STATUS_TXT.get(pr['status'], '•')} — {Path(p).name}"
    escolhido = st.selectbox("Projeto", nomes, index=idx, format_func=rotulo)
    st.session_state["projeto_aberto"] = escolhido
    jd = Path(escolhido)
    pr = read_progress(jd) or {"status": "?", "pct": 0, "etapa": ""}
    if pr["status"] in ("rodando", "pausado"):
        grade_ao_vivo(jd)
    else:
        grade_projeto(jd, editavel=True)


@st.fragment(run_every=3)
def grade_ao_vivo(jd: Path):
    pr = read_progress(jd) or {}
    if pr.get("status") not in ("rodando", "pausado"):
        st.rerun()
    st.info(f"{STATUS_TXT.get(pr.get('status'), '')}: {pr.get('etapa', '')} ({pr.get('pct', 0):.0f}%). "
            "As cenas aparecem aqui conforme ficam prontas. Para trocar cenas, espere terminar ou cancele.")
    grade_projeto(jd, editavel=False)


def grade_projeto(jd: Path, editavel: bool):
    from core import projeto as P
    try:
        dados = P.carregar(jd)
    except Exception as e:
        st.warning(f"Projeto ainda sem cenas ({e}).")
        return
    cenas = dados["cenas"]
    if not cenas:
        st.info("Dividindo o roteiro em cenas…")
        return
    job = dados["job"]
    n_ia = sum(1 for c in cenas if c.get("fonte", "ia") == "ia" and c["midia"])
    n_bk = sum(1 for c in cenas if c.get("fonte") == "banco" and c["midia"])
    n_pb = sum(1 for c in cenas if c["problemas"])
    m = st.columns(5)
    m[0].metric("Cenas prontas", f"{dados['prontas']}/{dados['total']}")
    m[1].metric("🤖 IA", n_ia)
    m[2].metric("🗂️ Banco", n_bk)
    m[3].metric("✋ Trocadas por você", sum(1 for c in cenas if c.get("manual")))
    m[4].metric("⚠️ Com aviso", n_pb)
    st.progress(dados["prontas"] / max(1, dados["total"]))

    if editavel and P.editado_depois_do_video(jd):
        cc1, cc2 = st.columns([3, 1])
        cc1.warning("Você trocou cenas depois que o vídeo foi montado. Remonte para o vídeo usar as novas imagens "
                    "(só as cenas trocadas são refeitas; narração, thumbnail e descrição são reaproveitadas).")
        if cc2.button("🎬 Remontar vídeo", type="primary", use_container_width=True):
            start_job(jd)
            st.session_state["job_ativo"] = str(jd)
            st.rerun()

    f1, f2 = st.columns([3, 1])
    filtro = f1.radio("Mostrar", ["Todas", "🤖 IA", "🗂️ Banco", "⚠️ Com aviso", "✋ Trocadas por você"], horizontal=True,
                      key=f"filtro_{jd.name}")
    sel = [c for c in cenas if filtro == "Todas"
           or (filtro == "🤖 IA" and c.get("fonte", "ia") == "ia")
           or (filtro == "🗂️ Banco" and c.get("fonte") == "banco")
           or (filtro == "⚠️ Com aviso" and c["problemas"])
           or (filtro == "✋ Trocadas por você" and c.get("manual"))]
    POR_PAG = 12
    paginas = max(1, -(-len(sel) // POR_PAG))
    pag = f2.number_input(f"Página (de {paginas})", 1, paginas, 1, key=f"pag_{jd.name}_{filtro}")
    mostrar = sel[(pag - 1) * POR_PAG: pag * POR_PAG]
    rot_fonte = {"ia": "🤖 IA", "banco": "🗂️ Banco", "meu arquivo": "📁 Seu arquivo"}

    def mmss(t):
        return f"{int(t // 60)}:{int(t % 60):02d}" if t is not None else "—"

    cols = st.columns(3)
    for i, c in enumerate(mostrar):
        with cols[i % 3].container(border=True):
            if c["midia"]:
                if c["eh_video"]:
                    st.video(c["midia"])
                else:
                    st.image(c["midia"], use_container_width=True)
            else:
                st.markdown('<div style="aspect-ratio:16/9;border-radius:12px;display:flex;align-items:center;'
                            'justify-content:center;border:2px dashed var(--border);color:var(--muted)">⏳ gerando…</div>',
                            unsafe_allow_html=True)
            dur = c.get("dur_audio")
            st.markdown(f"**Cena {c['id']}** · {rot_fonte.get(c.get('fonte', 'ia'), c.get('fonte', ''))}"
                        f"{' · ✋' if c.get('manual') else ''} · ⏱️ {mmss(c.get('inicio'))}"
                        f"{f' ({dur:.1f}s)' if dur else ''}")
            st.caption(c["texto"][:220] + ("…" if len(c["texto"]) > 220 else ""))
            for pb in c["problemas"]:
                st.warning(pb)
            if editavel and c["midia"]:
                with st.expander("✏️ Trocar esta cena"):
                    k = f"{jd.name}_{c['id']}"
                    if c.get("fonte", "ia") != "banco":
                        novo_p = st.text_area("Prompt da imagem (pode editar)", c.get("image_prompt", ""), height=90, key=f"pr_{k}")
                    else:
                        novo_p = None
                        st.caption(f"Busca usada: *{c.get('search_query', '')}*")
                    b1, b2 = st.columns(2)
                    if b1.button("🤖 Gerar com IA", key=f"ia_{k}", use_container_width=True):
                        with st.spinner("Gerando..."):
                            try:
                                P.regenerar(jd, c["id"], prompt=novo_p, fonte="ia")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                    if b2.button("🗂️ Outra do banco", key=f"bk_{k}", use_container_width=True):
                        with st.spinner("Buscando..."):
                            try:
                                P.regenerar(jd, c["id"], fonte="banco")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))
                    up = st.file_uploader("Ou use um arquivo seu", type=["jpg", "jpeg", "png", "webp", "mp4", "mov", "mkv", "webm"],
                                          key=f"up_{k}")
                    if up is not None and st.button("📁 Usar este arquivo", key=f"us_{k}", use_container_width=True):
                        try:
                            P.substituir(jd, c["id"], up.name, up.getvalue())
                            st.rerun()
                        except Exception as e:
                            st.error(str(e))


# ================================================================== TRABALHOS
def page_jobs():
    hero("📂", "Trabalhos", "Acompanhe o progresso, continue de onde parou e abra os vídeos prontos.")
    jobs = sorted([d for d in C.JOBS_DIR.iterdir() if d.is_dir()], reverse=True)
    if not jobs:
        st.info("Nenhum vídeo gerado ainda.")
        return
    for d in jobs[:30]:
        pr = read_progress(d) or {"status": "?", "pct": 0, "etapa": ""}
        icon = {"concluido": "✅", "erro": "❌", "rodando": "⏳", "aguardando": "👀", "pausado": "⏸️", "cancelado": "⏹️"}.get(pr["status"], "•")
        with st.expander(f"{icon} {d.name} — {pr['etapa']}", expanded=pr["status"] == "aguardando"):
            progress_panel(d, key="jobs")
            if st.button("🗂️ Abrir projeto", key=f"pj{d.name}"):
                abrir_projeto(d)
            if st.button("✏️ Usar opções como base", key=f"b{d.name}"):
                set_job(json.loads((d / "trabalho.json").read_text(encoding="utf-8")))
                st.success("Opções carregadas em Novo vídeo.")


# ================================================================== NICHOS
def page_niches():
    s = load_settings()
    hero("🔎", "BUSCADOR DE NICHOS", "Canais novos crescendo agora — e análise completa de qualquer canal.")
    if not s.get("youtube_key"):
        st.warning("Coloque a chave grátis da **YouTube Data API v3** em **APIs e configurações** para usar o buscador.")
    if "_canal_pending" in st.session_state:
        st.session_state["canal_entrada"] = st.session_state.pop("_canal_pending")
        st.session_state["canal_auto"] = True
        st.session_state["nicho_modo"] = "📊 Analisar canal"
    if "_nicho_modo_pending" in st.session_state:
        st.session_state["nicho_modo"] = st.session_state.pop("_nicho_modo_pending")
    _modos = ["📚 Base de canais", "🔎 Nova busca", "📊 Analisar canal"]
    if st.session_state.get("nicho_modo") not in _modos:
        st.session_state["nicho_modo"] = "📚 Base de canais"
    modo = st.segmented_control("Modo", _modos, key="nicho_modo",
                                label_visibility="collapsed") if hasattr(st, "segmented_control") else \
        st.radio("Modo", _modos, key="nicho_modo", horizontal=True)
    if modo == "📊 Analisar canal":
        page_channel(s)
    elif modo == "🔎 Nova busca":
        page_search(s)
    else:
        page_base(s)


def _k(n) -> str:
    n = n or 0
    for lim, suf in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= lim:
            v = n / lim
            return (f"{v:.1f}".rstrip("0").rstrip(".") if v < 100 else f"{v:.0f}") + suf
    return str(int(n))


def _ha(ts) -> str:
    if not ts:
        return "—"
    d = (datetime.now().date() - datetime.fromtimestamp(ts).date()).days
    return "hoje" if d == 0 else ("ontem" if d == 1 else f"há {d} dias")


DESC_ABAS = {"Todos": "Todos os canais guardados que passam nos filtros",
             "Explodindo Agora": "Vídeo recente ganhando views muito rápido (300+ por hora) ou 20× os inscritos",
             "Subindo Rápido": "Ganhando 50+ inscritos por dia no radar, ou vídeos novos rendendo 2× mais que os antigos",
             "Alta Tração": "1 milhão de views por mês ou mais",
             "Tração Recente": "Canal com até 2 meses e 200 mil views por mês ou mais",
             "Poucos Inscritos, Muitas Views": "Views totais 100× maiores que os inscritos"}


def page_base(s):
    from core import base_canais as BC
    ss = st.session_state
    ss.setdefault("bc_aba", "Todos")
    ss.setdefault("bc_fav", False)
    ss.setdefault("bc_pag", 1)
    ORDENS = {"nota": "Nota do canal (0–100: outlier, ritmo)", "views_mes": "Views por mês", "crescimento": "Crescimento (inscritos/dia)",
              "jovem": "Canal mais novo", "recente": "Adicionado mais recente", "inscritos": "Mais inscritos",
              "faceless": "Mais faceless"}
    filtros = dict(texto=ss.get("bc_texto_ok", ""), categoria=ss.get("bc_cat", "") if ss.get("bc_cat") != "Todos os nichos" else "",
                   idioma=ss.get("bc_idi", "") if ss.get("bc_idi") != "Todos os idiomas" else "",
                   status=ss.get("bc_st", "") if ss.get("bc_st") != "Todos os status" else "",
                   foco=ss.get("bc_foco", "") if ss.get("bc_foco") != "Todos os focos" else "",
                   ordem=ss.get("bc_ord", "nota"), data_campo=ss.get("bc_dcampo", "adicionado"),
                   periodo=ss.get("bc_per", "Todos"), dia=ss.get("bc_dia"), so_favoritos=ss["bc_fav"])
    lst, cont = BC.consultar(aba=ss["bc_aba"], **filtros)

    # ---- abas de status (com contagem) + favoritos
    with st.container(key="bc_abas"):
        cols = st.columns([0.8, 1.45, 1.3, 1.15, 1.3, 2.1, 1.0])
        for col, aba in zip(cols, ["Todos"] + BC.STATUS):
            ic = "☰" if aba == "Todos" else BC.ICONES[aba]
            if col.button(f"{ic} {aba}  ·  {cont.get(aba, 0)}", key=f"bc_tab_{aba}", use_container_width=True,
                          type="primary" if ss["bc_aba"] == aba else "secondary"):
                ss["bc_aba"] = aba
                ss["bc_pag"] = 1
                st.rerun()
        if cols[-1].button(("♥" if ss["bc_fav"] else "♡") + " Favoritos", key="bc_tab_fav", use_container_width=True,
                           type="primary" if ss["bc_fav"] else "secondary"):
            ss["bc_fav"] = not ss["bc_fav"]
            st.rerun()
    st.caption(DESC_ABAS[ss["bc_aba"]] + (" · só favoritos" if ss["bc_fav"] else ""))

    # ---- busca por palavra (com botão, sem Enter)
    c1, c2 = st.columns([6, 1], vertical_alignment="bottom")
    texto = c1.text_input("Filtrar", key="bc_texto", label_visibility="collapsed",
                          placeholder="🔍  filtrar a base por palavra no nome do canal ou nos títulos dos vídeos")
    if c2.button("✓ Filtrar", use_container_width=True, key="bc_texto_btn"):
        ss["bc_texto_ok"] = texto.strip()
        ss["bc_pag"] = 1
        st.rerun()

    # ---- filtros
    with st.container(key="bc_filtros"):
        f = st.columns([1.3, 1.1, 1.2, 1.1, 1.7, 0.9], vertical_alignment="bottom")
        f[0].selectbox("Categoria", ["Todos os nichos"] + BC.categorias(), key="bc_cat")
        f[1].selectbox("Idioma", ["Todos os idiomas"] + BC.idiomas(), key="bc_idi",
                       format_func=lambda x: BC.IDIOMAS.get(x, x))
        f[2].selectbox("Status", ["Todos os status"] + BC.STATUS, key="bc_st")
        f[3].selectbox("Foco", ["Todos os focos", "Faceless (70%+)", "Com rosto", "Favoritos"], key="bc_foco")
        f[4].selectbox("Ordenar", list(ORDENS), format_func=ORDENS.get, key="bc_ord")
        f[5].markdown(f"<p style='text-align:right;font-weight:700;margin:0 0 .6rem'>{len(lst)} resultados</p>",
                      unsafe_allow_html=True)
        g = st.columns([1.2, 1.4, 1.4, 3], vertical_alignment="bottom")
        g[0].selectbox("📅 Data de", ["adicionado", "atualizado"], key="bc_dcampo",
                       format_func={"adicionado": "Coleta", "atualizado": "Atualização"}.get)
        g[1].selectbox("Período", ["Todos", "Hoje", "Últimos 3 dias", "Últimos 7 dias", "Últimos 30 dias", "Data específica"],
                       key="bc_per")
        if ss.get("bc_per") == "Data específica":
            g[2].date_input("Dia", key="bc_dia", format="DD/MM/YYYY")

    # ---- crescimento + IA
    d = BC.ler()
    ua = d.get("ultima_atualizacao")
    c1, c2, c3 = st.columns([1.3, 1.3, 3], vertical_alignment="center")
    if c1.button("🔄 Atualizar crescimento", use_container_width=True, disabled=not s.get("youtube_key") or not d["canais"],
                 help="Relê inscritos e views de todos os canais da base. Custa 1 unidade de cota a cada 50 canais."):
        try:
            with st.spinner("Lendo os canais..."):
                BC.atualizar_todos()
            st.rerun()
        except Exception as e:
            from core import nichos as N
            st.error(N.erro_amigavel(e))
    if c2.button("🤖 Estimar faceless e nicho", use_container_width=True,
                 help="A IA olha as 3 thumbs de cada canal ainda sem estimativa (até 40 por vez)."):
        with st.spinner("A IA está olhando as thumbs..."):
            n = BC.classificar_ia(40, log=lambda m: None)
        st.toast(f"{n} canais classificados" if n else "Nada para classificar (ou falta a IA de texto com imagens).")
        st.rerun()
    if ua:
        c3.caption(f"Crescimento atualizado {_ha(ua['quando'])} às {datetime.fromtimestamp(ua['quando']):%H:%M}: "
                   f"{ua['canais']} canais (gastou {ua['gasto']} de cota). Excluídos ficam de fora.")
    else:
        c3.caption("Atualize o crescimento de tempos em tempos: o programa compara com a leitura anterior e mostra "
                   "quantos inscritos cada canal ganha por dia.")

    if not lst:
        if not d["canais"]:
            st.info("A base ainda está vazia. Vá em **🔎 Nova busca**: todo canal promissor encontrado fica guardado aqui.")
        else:
            st.info("Nenhum canal com esses filtros.")
        return

    # ---- ações em massa
    marcados = [c["id"] for c in lst if ss.get(f"bc_sel_{c['id']}")]
    if marcados:
        a1, a2, a3 = st.columns([1.3, 1.3, 3])
        if a1.button(f"♥ Favoritar {len(marcados)}", use_container_width=True):
            for cid in marcados:
                BC.favoritar(cid, True)
                ss[f"bc_sel_{cid}"] = False
            st.rerun()
        if a2.button(f"🗑️ Excluir {len(marcados)}", use_container_width=True):
            BC.excluir(marcados)
            for cid in marcados:
                ss[f"bc_sel_{cid}"] = False
            st.rerun()

    # ---- grade de cartões (paginada)
    POR = 24
    paginas = max(1, math.ceil(len(lst) / POR))
    ss["bc_pag"] = min(ss["bc_pag"], paginas)
    ini = (ss["bc_pag"] - 1) * POR
    for i in range(ini, min(ini + POR, len(lst)), 3):
        cols = st.columns(3)
        for col, (rank, c) in zip(cols, [(k + 1, lst[k]) for k in range(i, min(i + 3, len(lst)))]):
            with col:
                cartao_canal(c, rank)
    if paginas > 1:
        p1, p2, p3 = st.columns([1, 2, 1], vertical_alignment="center")
        if p1.button("← Anteriores", disabled=ss["bc_pag"] == 1, use_container_width=True):
            ss["bc_pag"] -= 1
            st.rerun()
        p2.markdown(f"<p style='text-align:center;margin:0'>Página {ss['bc_pag']} de {paginas}</p>", unsafe_allow_html=True)
        if p3.button("Próximos →", disabled=ss["bc_pag"] == paginas, use_container_width=True):
            ss["bc_pag"] += 1
            st.rerun()


def cartao_canal(c: dict, rank: int):
    from core import base_canais as BC
    import html as _h
    cid = c["id"]
    link = f"https://www.youtube.com/channel/{cid}"
    with st.container(key=f"cc_{cid}"):
        h1, h2, h3 = st.columns([0.45, 6, 0.75], vertical_alignment="top")
        h1.checkbox("Selecionar", key=f"bc_sel_{cid}", label_visibility="collapsed")
        nicho = c.get("nicho_ia") or c.get("nicho_busca") or "—"
        pal = c.get("palavras") or c.get("termo") or ""
        badge = f'<span class="cc-badge">{BC.CURTO[c["status"][0]]}</span>' if c.get("status") else ""
        av = f'<img class="cc-av" src="{c.get("avatar", "")}">' if c.get("avatar") else '<div class="cc-av"></div>'
        h2.markdown(
            f'<div class="cc-head">{av}<div class="cc-tit"><a class="cc-nome" href="{link}" target="_blank">'
            f'{_h.escape(c.get("nome", ""))}</a> <span class="cc-flag">{BC.bandeira(c.get("pais"))}</span>'
            f'<div class="cc-sub">{("IA: " if c.get("nicho_ia") else "")}{_h.escape(nicho)}'
            f'{(" / palavras: " + _h.escape(pal)) if pal else ""} · {(c.get("idioma") or "?").upper()}</div></div></div>'
            f'<div class="cc-badge-row">{badge}</div>', unsafe_allow_html=True)
        if h3.button("♥" if c.get("favorito") else "♡", key=f"bc_fav_{cid}", help="Favoritar (segue no radar)"):
            BC.favoritar(cid, not c.get("favorito"))
            st.rerun()
        thumbs = "".join(
            f'<a href="https://www.youtube.com/watch?v={v["id"]}" target="_blank" title="{_h.escape(v.get("titulo", ""))}">'
            f'<img src="{v.get("thumb", "")}"><span>{_k(v.get("views"))}</span></a>' for v in (c.get("top") or [])[:3])
        fl = c.get("faceless")
        dias = c.get("dias_postando") or 0
        cresc = c.get("inscritos_dia")
        st.markdown(
            f'<div class="cc-thumbs">{thumbs}</div>'
            f'<div class="cc-stats"><div><b>{_k(c.get("inscritos"))}</b><small>INSCRITOS</small></div>'
            f'<div><b>{_k(c.get("views"))}</b><small>VIEWS</small></div>'
            f'<div><b>{c.get("videos", 0)}</b><small>VÍDEOS</small></div>'
            f'<div><b class="cc-face">{f"{fl}%" if fl is not None else "—"}</b><small>FACELESS</small></div></div>'
            f'<div class="cc-foot">▤ {dias}d postando · {c.get("vids_mes", 0)} vid/mês · {_k(c.get("views_mes"))} views/mês'
            f'{f" · <b>+{_k(cresc)} inscr./dia</b>" if cresc and cresc > 0 else ""}</div>'
            f'<div class="cc-foot2"><span>◷ Adicionado {_ha(c.get("adicionado"))} · atualizado {_ha(c.get("atualizado"))}'
            f'</span><span class="cc-nota" title="Nota do canal">{c.get("nota", 0)}</span></div>', unsafe_allow_html=True)
        f1, f2 = st.columns([5, 1.1], vertical_alignment="center")
        f1.markdown(f'<span class="cc-rank">#{rank}</span>', unsafe_allow_html=True)
        with f2.popover("⋯", use_container_width=True):
            st.link_button("▶ Abrir no YouTube", link, use_container_width=True)
            if st.button("📊 Analisar canal", key=f"bc_an_{cid}", use_container_width=True):
                st.session_state["_canal_pending"] = link
                st.rerun()
            if c.get("top") and st.button("🌍 Fazer a dobra do vídeo top", key=f"bc_db_{cid}", use_container_width=True):
                ir_adaptar(f"https://www.youtube.com/watch?v={c['top'][0]['id']}")
            if st.button("🗑️ Excluir da base", key=f"bc_ex_{cid}", use_container_width=True):
                BC.excluir([cid])
                st.rerun()


def page_search(s):
    from core import nichos as N
    st.caption("Acha nichos NASCENDO agora: canais que começaram há pouco, com vídeos recentes ganhando views muito "
               "rápido e pouca gente fazendo o mesmo no seu idioma.")
    PADRAO = {"nb_dias": 7, "nb_idade": 60, "nb_subs": 20000, "nb_views": 5000}
    for k, v in PADRAO.items():
        st.session_state.setdefault(k, v)
    c_a, c_b = st.columns([1, 2], vertical_alignment="center")
    st.caption("Todo canal promissor encontrado fica guardado na **📚 Base de canais**, com cartões, status e nota.")
    if c_a.button("⚡ Modo chegar cedo", type="primary", use_container_width=True,
                  help="Vídeos dos últimos 3 dias, canais que começaram há até 1 mês, até 20 mil inscritos."):
        st.session_state.update({"nb_dias": 3, "nb_idade": 30, "nb_subs": 20000, "nb_views": 3000})
        st.rerun()
    c_b.caption("Ordena tudo pela nota **Chegou cedo** (0–100): velocidade de views por hora, canal jovem "
                "(pela data do 1º vídeo), poucos vídeos, vídeos novos rendendo mais que os antigos e pouca concorrência no seu idioma.")

    modo = st.radio("Como buscar", ["Explorar nichos prontos", "Pesquisar meus termos"], horizontal=True)
    if modo == "Explorar nichos prontos":
        escolhidos = st.multiselect("Nichos", list(N.NICHOS), default=list(N.NICHOS)[:6])
    else:
        txt = st.text_area("Um termo por linha (cada linha vira um nicho)", "máfia italiana\nmitologia nórdica\nhistórias de sobrevivência", height=110)

    c1, c2, c3 = st.columns(3)
    max_subs = c1.number_input("Máximo de inscritos do canal", 0, 10_000_000, step=1000, key="nb_subs",
                               help="Canal crescendo rápido passa de mil inscritos em poucos dias. 20 mil ainda é 'cedo'.")
    min_views = c2.number_input("Mínimo de views no vídeo", 0, 100_000_000, step=1000, key="nb_views")
    DIAS = {1: "24 horas", 2: "48 horas", 3: "3 dias", 7: "7 dias", 14: "14 dias", 30: "30 dias", 60: "60 dias", 90: "90 dias"}
    dias = c3.selectbox("Vídeos publicados nas últimas", list(DIAS), format_func=DIAS.get, key="nb_dias",
                        help="Quanto mais recente, mais cedo você chega. 3 a 7 dias é o ideal.")
    c1, c2, c3, c4 = st.columns(4)
    regiao = c1.selectbox("Região", list(N.REGIOES))
    duracao = c2.selectbox("Duração", list(N.DURACOES))
    IDADES = {7: "7 dias", 15: "15 dias", 30: "1 mês", 60: "2 meses", 90: "3 meses", 180: "6 meses", 365: "1 ano", 0: "Qualquer"}
    idade = c3.selectbox("Canal começou há no máximo", list(IDADES), format_func=IDADES.get, key="nb_idade",
                         help="Conta a partir do 1º vídeo publicado (não da criação da conta): muitos canais são "
                              "antigos mas começaram a postar agora.")
    paginas = c4.selectbox("Profundidade", [1, 2, 3], format_func=lambda p: f"{p * 50} vídeos por termo")
    c1, c2, c3 = st.columns(3)
    momento = c1.toggle("Medir o momento de cada canal", True,
                        help="Lê os últimos vídeos de cada canal: data do 1º vídeo, aceleração, vídeo fora da curva. "
                             "Custa ~2 unidades por canal.")
    IDI = {"pt": "Português", "en": "Inglês", "es": "Espanhol", "de": "Alemão", "pl": "Polonês", "cs": "Tcheco",
           "da": "Dinamarquês", "no": "Norueguês"}
    idioma_dest = c2.selectbox("Vou levar para", list(IDI), format_func=IDI.get,
                               help="Idioma em que você vai fazer a sua versão. Usado para checar a concorrência.")
    from core.llm import llm_available as _llm_ok
    classif = 40 if _llm_ok() else 0
    top_conc = c3.selectbox("Checar concorrência nesse idioma", [0, 3, 5, 10], index=2,
                            format_func=lambda n: "Não checar" if n == 0 else f"nos {n} melhores (~{n * 101} unidades)",
                            help="Pesquisa o mesmo assunto no seu idioma: 🟢 livre, 🟡 pouca, 🔴 já tem gente.")

    if modo == "Explorar nichos prontos":
        alvo = N.termos_nichos(escolhidos, regiao)
        lang = N.idioma_da_regiao(regiao)
        if alvo:
            with st.expander(f"Termos que serão pesquisados (em {N.IDIOMA_NOME[lang]})"):
                for n, ts in alvo.items():
                    st.markdown(f"**{n}:** " + " · ".join(ts))
    else:
        alvo = {t.strip(): [t.strip()] for t in txt.splitlines() if t.strip()}
        if regiao != "Mundo (sem região)" and N.idioma_da_regiao(regiao) != "pt":
            st.caption(f"Dica: escreva os termos em {N.IDIOMA_NOME[N.idioma_da_regiao(regiao)]} para achar canais desse país.")
    n_termos = sum(len(v) for v in alvo.values())
    custo = N.custo_estimado(n_termos, paginas, momento, top_conc)
    st.caption(f"Custo estimado: ~{custo:,} de 10.000 unidades da cota diária grátis (≈ {10000 // max(custo, 1)} buscas assim por dia).".replace(",", "."))

    if not s.get("youtube_key"):
        st.warning("Falta a chave da **YouTube Data API**. Crie a chave grátis no Google Cloud e cole em **APIs e configurações**.")
    if st.button("🔎 BUSCAR", type="primary", use_container_width=True, disabled=not s.get("youtube_key")) and \
            _tem("x" if alvo else "", "Escolha pelo menos um nicho ou escreva um termo."):
        logs = st.empty()
        msgs = []
        def lg(m):
            msgs.append(m)
            logs.code("\n".join(msgs[-8:]), language=None)
        try:
            with st.spinner("Buscando no YouTube... (com vários nichos pode levar alguns minutos)"):
                linhas, resumo, gasto = N.rodar(alvo, dias, regiao, duracao, int(max_subs), int(min_views), paginas, idade, lg,
                                                momento=momento, idioma_destino=idioma_dest, top_concorrencia=top_conc,
                                                classificar_ia=classif)
            st.session_state["nichos_res"] = (linhas, resumo, gasto, dict(N.FUNIL))
            hist = C.DATA_DIR / "nichos"
            hist.mkdir(exist_ok=True)
            (hist / time.strftime("busca_%Y%m%d_%H%M%S.json")).write_text(
                json.dumps({"linhas": linhas, "resumo": resumo}, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            st.error(str(e))

    res = st.session_state.get("nichos_res")
    if not res:
        return
    linhas, resumo, gasto = res[:3]
    st.success(f"{len(linhas)} vídeos de canais pequenos encontrados · {gasto} unidades de cota usadas")
    if linhas and st.button("📚 Ver os canais na Base de canais", type="primary"):
        st.session_state["_nicho_modo_pending"] = "📚 Base de canais"
        st.session_state.update({"bc_aba": "Todos", "bc_per": "Hoje", "bc_ord": "nota", "bc_pag": 1})
        st.rerun()
    cedo = [l for l in linhas if "🌱" in l.get("Sinais", "") and ("🔥" in l.get("Sinais", "") or "🚀" in l.get("Sinais", ""))]
    if cedo:
        st.markdown(f"**⚡ {len(cedo)} oportunidade(s) bem no início e já em alta:**")
        for l in cedo[:5]:
            st.markdown(f"- {l['Sinais']} **{l['Vídeo']}** — {l['Canal']} · {l['Views/hora']:,} views/hora · "
                        f"1º vídeo há {l['1º vídeo há (dias)'] if l['1º vídeo há (dias)'] is not None else '?'} dias"
                        .replace(",", ".") + (f" · {l['Concorrência no meu idioma'].split(' · ')[0]}" if l.get("Concorrência no meu idioma") else ""))
    if not linhas:
        f = res[3] if len(res) > 3 else {}
        if f.get("videos"):
            st.warning(
                f"O YouTube devolveu **{f['videos']} vídeos**, mas nenhum passou nos filtros:\n"
                f"- {f.get('inscritos', 0)} eram de canais com mais de {int(max_subs):,} inscritos\n"
                f"- {f.get('views', 0)} tinham menos de {int(min_views):,} views\n"
                f"- {f.get('idade', 0)} eram de canais que começaram há mais tempo que o limite\n\n"
                "Afrouxe o filtro que cortou mais: aumente os dias (7 dias), a idade do canal (2 ou 3 meses), "
                "baixe o mínimo de views ou mude a região para 'Mundo (sem região)'.".replace(",", "."))
        else:
            st.info("O YouTube não devolveu nenhum vídeo para esses termos nesse período. Aumente os dias ou troque a região.")
        return
    st.subheader("🏆 Ranking de nichos")
    st.dataframe(resumo, use_container_width=True, hide_index=True)
    st.subheader("📈 Vídeos e canais crescendo")
    nichos_f = st.multiselect("Filtrar nicho", sorted({l["Nicho"] for l in linhas}))
    so_cedo = st.toggle("Mostrar só canais 🌱 bem no início")
    mostrar = [l for l in linhas if (not nichos_f or l["Nicho"] in nichos_f) and (not so_cedo or "🌱" in l.get("Sinais", ""))]
    tabela = [{k: v for k, v in l.items() if not k.startswith("_") and k != "Pontuação"} for l in mostrar]
    ev = st.dataframe(
        tabela, use_container_width=True, hide_index=True, height=520, on_select="rerun", selection_mode="single-row",
        column_config={
            "Thumb": st.column_config.ImageColumn("Thumb", width="small"),
            "Link vídeo": st.column_config.LinkColumn("Vídeo ▶", display_text="abrir"),
            "Link canal": st.column_config.LinkColumn("Canal ▶", display_text="abrir"),
            "Views": st.column_config.NumberColumn(format="%d"),
            "Chegou cedo": st.column_config.ProgressColumn("Chegou cedo", min_value=0, max_value=100, format="%.0f"),
            "Views/hora": st.column_config.NumberColumn(format="%d"),
            "Aceleração": st.column_config.NumberColumn(help="Mediana de views dos 5 vídeos mais novos ÷ mediana dos "
                                                             "antigos. Acima de 1 = os vídeos novos estão rendendo mais."),
        })
    sel = ev.selection.rows if ev and hasattr(ev, "selection") else []
    if sel:
        l = mostrar[sel[0]]
        st.markdown(f"**{l['Vídeo']}** — {l['Canal']} ({l['Inscritos']} inscritos, {l['Views']:,} views)".replace(",", "."))
        b1, b2, b3, b4 = st.columns(4)
        if b4.button("📡 Seguir no radar"):
            N.radar_seguir(l["_cid"], l["Canal"], l["Link canal"], l["Nicho"])
            st.toast("Canal adicionado ao Radar. Atualize o radar nos próximos dias para ver o crescimento.")
        if b3.button("🌍 Fazer a dobra deste vídeo"):
            ir_adaptar(l["Link vídeo"])
        if b1.button("📊 Analisar este canal", type="primary"):
            st.session_state["_canal_pending"] = l["Link canal"]
            st.rerun()
        if b2.button("➡️ Usar este título como base em Novo vídeo"):
            st.session_state["job"]["titulo"] = l["Vídeo"]
            st.session_state["w_titulo"] = l["Vídeo"]
            st.success("Título enviado para Novo vídeo.")

    import csv, io
    buf = io.StringIO()
    _cols = [k for k in linhas[0].keys() if not k.startswith("_")]
    w = csv.DictWriter(buf, fieldnames=_cols, delimiter=";", extrasaction="ignore")
    w.writeheader()
    w.writerows(linhas)
    st.download_button("⬇️ Baixar planilha (CSV para Excel)", buf.getvalue().encode("utf-8-sig"),
                       file_name=time.strftime("nichos_%Y%m%d_%H%M.csv"), mime="text/csv")

    st.subheader("🧠 Análise com IA")
    if st.button("Analisar nichos e sugerir títulos"):
        try:
            with st.spinner("Analisando..."):
                st.session_state["nichos_ia"] = N.analise_ia(linhas, resumo)
        except Exception as e:
            st.error(str(e))
    if st.session_state.get("nichos_ia"):
        st.markdown(st.session_state["nichos_ia"])


def page_radar(s):
    from core import nichos as N
    st.caption("Canais que você marcou para acompanhar. Atualize de vez em quando: o programa compara com a leitura "
               "anterior e mostra quanto cada canal cresceu por dia. Assim você vê quem está decolando de verdade.")
    lista = N.radar_lista()
    c1, c2 = st.columns([1, 2], vertical_alignment="center")
    if c1.button("🔄 Atualizar radar agora", type="primary", use_container_width=True,
                 disabled=not lista or not s.get("youtube_key")):
        try:
            with st.spinner("Lendo os canais..."):
                n = N.radar_atualizar()
            st.toast(f"{n} canais atualizados")
            st.rerun()
        except Exception as e:
            st.error(str(e))
    c2.caption(f"{len(lista)} canais no radar · custa só 1 unidade a cada 50 canais. "
               "O crescimento aparece a partir da segunda leitura (com pelo menos 6 horas de diferença).")
    if not lista:
        st.info("Nenhum canal no radar ainda. No **🔎 Buscar nichos**, clique num resultado e use **📡 Seguir no radar**.")
        return
    ev = st.dataframe([{k: v for k, v in l.items() if k != "id"} for l in lista], use_container_width=True,
                      hide_index=True, on_select="rerun", selection_mode="single-row",
                      column_config={"Link canal": st.column_config.LinkColumn("Canal ▶", display_text="abrir"),
                                     "Inscritos/dia": st.column_config.NumberColumn(format="%+d"),
                                     "Views/dia": st.column_config.NumberColumn(format="%+d")})
    sel = ev.selection.rows if ev and hasattr(ev, "selection") else []
    if sel:
        l = lista[sel[0]]
        b1, b2 = st.columns(2)
        if b1.button("📊 Analisar este canal", type="primary"):
            st.session_state["_canal_pending"] = l["Link canal"]
            st.rerun()
        if b2.button("🗑️ Parar de seguir"):
            N.radar_seguir(l["id"], l["Canal"], l["Link canal"], seguir=False)
            st.rerun()


def page_channel(s):
    from core import canal as K
    st.caption("Cole o link do canal, o @nome, o link de qualquer vídeo dele — ou clique em um canal no resultado da busca.")
    c1, c2, c3 = st.columns([4, 1.3, 1.3])
    entrada = c1.text_input("Canal", key="canal_entrada", placeholder="https://www.youtube.com/@nomedocanal")
    maxv = c2.selectbox("Vídeos analisados", [50, 100, 200, 500], index=2)
    rpm = c3.select_slider("RPM (US$ por mil views)", options=[0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0], value=(1.0, 4.0),
                           help="Dark/curiosidades em PT: ~US$ 0,5–3. Em inglês (EUA/Austrália): ~US$ 3–12.")
    auto = st.session_state.pop("canal_auto", False)
    if not s.get("youtube_key"):
        st.warning("Falta a chave da **YouTube Data API**. Crie a chave grátis no Google Cloud e cole em **APIs e configurações**.")
    if (st.button("📊 ANALISAR CANAL", type="primary", use_container_width=True,
                  disabled=not s.get("youtube_key")) or auto) and _tem(entrada, "Cole o link do canal."):
        try:
            with st.spinner("Lendo o canal..."):
                st.session_state["canal_res"] = K.analisar_canal(entrada, maxv, rpm[0], rpm[1])
                st.session_state.pop("canal_ia", None)
        except Exception as e:
            st.error(str(e))
    a = st.session_state.get("canal_res")
    if not a:
        return
    r = a["resumo"]
    h1, h2 = st.columns([1, 6])
    if r["Foto"]:
        h1.image(r["Foto"], width=90)
    h2.markdown(f"### [{r['Nome']}]({r['Link']})\n{r['País']} · criado em {r['Criado em']} ({r['Idade (meses)']} meses)")
    fmt = lambda n: "oculto" if n is None else f"{n:,}".replace(",", ".")
    m = st.columns(5)
    m[0].metric("Inscritos", fmt(r["Inscritos"]))
    m[1].metric("Views totais", fmt(r["Views totais"]))
    m[2].metric("Vídeos", fmt(r["Vídeos no canal"]))
    m[3].metric("Mediana de views", fmt(r["Mediana de views"]))
    m[4].metric("Tendência", r["Tendência (últimos 10 vs 10 anteriores)"] or "—", help="Mediana dos 10 últimos vídeos comparada aos 10 anteriores")
    m = st.columns(5)
    m[0].metric("Vídeos em 30 dias", r["Vídeos últimos 30 dias"])
    m[1].metric("Posta a cada", f"{r['Posta a cada (dias, mediana)']} dias" if r["Posta a cada (dias, mediana)"] is not None else "—")
    m[2].metric("Inscritos/mês", fmt(r["Inscritos por mês (média)"]))
    m[3].metric("Views por inscrito", r["Views por inscrito"] or "—")
    m[4].metric("Receita 30 dias (US$)", r["Receita estimada 30 dias (US$)"], help="Estimativa grosseira: views dos vídeos postados nos últimos 30 dias × RPM escolhido. Só vale se o canal for monetizado.")

    t1, t2, t3, t4, t5 = st.tabs(["🎬 Vídeos", "📈 Desempenho", "⏱️ Formato e horário", "✍️ Títulos e tags", "🧠 Análise com IA"])
    with t1:
        ordem = st.radio("Ordenar por", ["Mais recentes", "Mais views", "Melhor desempenho (vs mediana)", "Mais views/dia"], horizontal=True)
        vs = list(a["videos"])
        key = {"Mais views": "Views", "Melhor desempenho (vs mediana)": "Desempenho", "Mais views/dia": "Views/dia"}.get(ordem)
        if key:
            vs.sort(key=lambda v: -v[key])
        st.dataframe(vs, use_container_width=True, hide_index=True, height=520, column_config={
            "Thumb": st.column_config.ImageColumn("Thumb", width="small"),
            "Link": st.column_config.LinkColumn("▶", display_text="abrir"),
            "Desempenho": st.column_config.NumberColumn("Desempenho", help="1.0 = mediana do canal; 3.0 = 3x mais views que o normal", format="%.2fx"),
        })
        st.markdown("**🌍 Levar um vídeo deste canal para outro idioma**")
        a1, a2 = st.columns([4, 1.3], vertical_alignment="bottom")
        _ops = sorted(a["videos"], key=lambda v: -v["Desempenho"])
        _esc = a1.selectbox("Vídeo (ordenado pelos que mais performaram)", range(len(_ops)), key="adapt_canal_sel",
                            format_func=lambda i: f"{_ops[i]['Desempenho']}x · {_ops[i]['Título'][:80]}")
        if a2.button("🌍 Adaptar", use_container_width=True, type="primary"):
            ir_adaptar(_ops[_esc]["Link"])
        outliers = [v for v in a["videos"] if v["Desempenho"] >= 3]
        if outliers:
            st.success(f"🔥 {len(outliers)} vídeos viralizaram (3x+ a mediana do canal). São os temas a copiar/adaptar.")
    with t2:
        st.caption("Views de cada vídeo, do mais antigo ao mais recente")
        st.bar_chart({"Views": [v["Views"] for v in reversed(a["videos"])]}, height=300)
        if a["por_tipo"]:
            st.markdown("**Shorts x vídeos longos**")
            st.dataframe([{"Tipo": k, **v} for k, v in a["por_tipo"].items()], hide_index=True)
    with t3:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Mediana de views por duração**")
            if a["por_duracao"]:
                st.bar_chart(a["por_duracao"], height=260)
            st.markdown("**Mediana de views por dia da semana** (horário de Brasília)")
            st.bar_chart(a["por_dia"], height=260)
        with c2:
            st.markdown("**Mediana de views por horário de postagem**")
            st.bar_chart(a["por_hora"], height=260)
            st.markdown("**Quantos vídeos postou em cada dia**")
            st.bar_chart(a["contagem_dia"], height=260)
    with t4:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Padrões dos títulos**")
            st.dataframe([{"Padrão": k, "Valor": v} for k, v in a["padroes"].items()], hide_index=True, use_container_width=True)
            st.markdown("**Palavras que mais aparecem nos títulos que bombaram**")
            st.dataframe([{"Palavra": w, "Vezes": n} for w, n in a["palavras_top"]], hide_index=True, use_container_width=True)
        with c2:
            st.markdown("**Tags mais usadas**")
            if a["tags"]:
                st.dataframe([{"Tag": w, "Vídeos": n} for w, n in a["tags"]], hide_index=True, use_container_width=True)
            else:
                st.caption("O canal não usa tags.")
    with t5:
        if st.button("🧠 Gerar análise estratégica do canal"):
            try:
                with st.spinner("Analisando..."):
                    st.session_state["canal_ia"] = K.analise_ia_canal(a)
            except Exception as e:
                st.error(str(e))
        if st.session_state.get("canal_ia"):
            st.markdown(st.session_state["canal_ia"])
    import csv, io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(a["videos"][0].keys()), delimiter=";")
    w.writeheader()
    w.writerows(a["videos"])
    st.download_button("⬇️ Baixar vídeos do canal (CSV)", buf.getvalue().encode("utf-8-sig"),
                       file_name=f"canal_{r['Nome'][:30]}.csv", mime="text/csv")
    st.caption(f"Cota usada nesta análise: {a['quota']} unidades.")


# ================================================================== PUBLICAR NO YOUTUBE
def page_publish():
    from core import youtube_upload as YT
    hero("📤", "Publicar no YouTube", "Conecte seus canais, envie e agende os vídeos direto do programa.")
    if not YT.bibliotecas_ok():
        st.error("Faltam as bibliotecas do Google. Rode o **INSTALAR.bat** de novo (ele instala tudo) e reabra o programa.")
        return
    t1, t2, t3 = st.tabs(["🚀 Enviar / agendar", "🔗 Contas conectadas", "📅 Envios e agendados"])
    with t1:
        aba_enviar()

    with t2:
        with st.expander("📘 Passo a passo (uma vez só): criar sua chave OAuth no Google Cloud",
                         expanded=not YT.CLIENT_SECRET.exists()):
            st.markdown(
                "1. Em **console.cloud.google.com**, use o mesmo projeto da chave do Buscador (ou crie um).\n"
                "2. **APIs e serviços → Biblioteca →** ative a **YouTube Data API v3**.\n"
                "3. **Tela de consentimento OAuth:** tipo *Externo*, preencha nome e e-mail e adicione seu(s) e-mail(s) em *Usuários de teste*. "
                "Depois clique em **Publicar app** (status *Em produção*). Assim a conexão não expira a cada 7 dias. "
                "Na hora de conectar, o Google vai mostrar 'app não verificado': clique em *Avançado → Acessar*. Isso é normal porque o app é seu.\n"
                "4. **Credenciais → Criar credenciais → ID do cliente OAuth →** tipo **App para computador**.\n"
                "5. Baixe o JSON e envie aqui embaixo.")
            up = st.file_uploader("client_secret.json", type=["json"])
            if up is not None and st.button("💾 Salvar chave OAuth"):
                try:
                    dados = json.loads(up.getvalue())
                    assert "installed" in dados or "web" in dados
                    YT.CLIENT_SECRET.write_bytes(up.getvalue())
                    st.success("Chave salva! Agora conecte sua conta.")
                except Exception:
                    st.error("Esse arquivo não parece um client_secret do Google (tipo App para computador).")
        st.markdown("#### Canais conectados")
        contas = YT.listar_contas()
        if not contas:
            st.info("Nenhum canal conectado ainda.")
        cols = st.columns(3)
        for i, c in enumerate(contas):
            with cols[i % 3].container(border=True):
                if c.get("foto"):
                    st.image(c["foto"], width=64)
                st.markdown(f"**{c['nome']}**  \n{c.get('inscritos', '')} inscritos · conectado em {c.get('conectado_em', '')}")
                if st.button("Desconectar", key=f"rmc_{c['id']}"):
                    YT.remover_conta(c["id"])
                    st.rerun()
        if st.button("➕ Conectar canal do YouTube", type="primary", disabled=not YT.CLIENT_SECRET.exists()):
            with st.spinner("Abrindo o navegador… entre na conta Google e escolha o canal (tem 5 minutos)."):
                try:
                    c = YT.conectar_conta()
                    st.success(f"Canal **{c['nome']}** conectado!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Não conectou: {e}")
        st.caption("Para vários canais, clique de novo e escolha outra conta ou canal na tela do Google.")

    with t3:
        painel_envios()


def aba_enviar():
    from core import youtube_upload as YT
    if True:
        contas = YT.listar_contas()
        if not contas:
            st.warning("Conecte um canal na aba **Contas conectadas** primeiro.")
            modo_manual()
            return
        jobs = [d for d in sorted(C.JOBS_DIR.iterdir(), reverse=True) if (d / "video_final.mp4").exists()]
        if not jobs:
            st.info("Nenhum vídeo pronto ainda.")
            return
        nomes = [str(d) for d in jobs]
        pre = st.session_state.get("publicar_job")
        jd = Path(st.selectbox("Vídeo", nomes, index=nomes.index(pre) if pre in nomes else 0, format_func=lambda p: Path(p).name))
        job = json.loads((jd / "trabalho.json").read_text(encoding="utf-8"))
        desc0 = (jd / "descricao.txt").read_text(encoding="utf-8") if (jd / "descricao.txt").exists() else ""
        tags0 = (jd / "palavras_chave.txt").read_text(encoding="utf-8") if (jd / "palavras_chave.txt").exists() else ""
        k = jd.name
        c1, c2 = st.columns([2, 1])
        with c1:
            _por_id = {c["id"]: c for c in contas}
            conta = _por_id[st.selectbox("Canal", list(_por_id), format_func=lambda i: _por_id[i]["nome"], key=f"pc_{k}")]
            titulo = st.text_input("Título", job["titulo"], max_chars=100, key=f"pt_{k}")
            descricao = st.text_area("Descrição", desc0, height=220, max_chars=5000, key=f"pd_{k}")
            tags = st.text_area("Tags (separadas por vírgula, até 500 letras)", tags0, height=80, key=f"pg_{k}")
        with c2:
            if (jd / "thumbnail.jpg").exists():
                st.image(str(jd / "thumbnail.jpg"), caption="Thumbnail", use_container_width=True)
            usar_thumb = st.checkbox("Enviar thumbnail", value=(jd / "thumbnail.jpg").exists(), key=f"pth_{k}")
            usar_srt = st.checkbox("Enviar legenda .srt", value=(jd / "legendas.srt").exists(), key=f"psr_{k}")
            cat = st.selectbox("Categoria", list(YT.CATEGORIAS), key=f"pca_{k}")
            idi = st.selectbox("Idioma do vídeo", list(YT.IDIOMAS_VIDEO), key=f"pid_{k}")
            kids = st.radio("É conteúdo para crianças?", ["Não", "Sim"], horizontal=True, key=f"pk_{k}") == "Sim"
            sint = st.checkbox("Contém conteúdo realista criado ou alterado por IA", value=job.get("pct_banco", 0) < 100,
                               help="O YouTube pede que você informe quando há cenas realistas geradas por IA.", key=f"psy_{k}")
        quando = st.radio("Publicação", ["📅 Agendar", "🌍 Público agora", "🔗 Não listado", "🔒 Privado"], horizontal=True, key=f"pq_{k}")
        publicar_em = None
        if quando == "📅 Agendar":
            from datetime import datetime as _dt, timedelta as _td
            amanha = _dt.now() + _td(days=1)
            d1, d2 = st.columns(2)
            dia = d1.date_input("Dia", amanha.date(), format="DD/MM/YYYY", key=f"pdia_{k}")
            hora = d2.time_input("Hora (horário do seu PC)", amanha.replace(hour=18, minute=0).time(), step=900, key=f"phora_{k}")
            alvo = _dt.combine(dia, hora)
            if alvo <= _dt.now():
                st.error("Escolha uma data/hora no futuro.")
            else:
                publicar_em = YT.iso_utc(alvo)
                st.caption(f"O vídeo sobe agora como privado e o próprio YouTube publica em {alvo.strftime('%d/%m/%Y às %H:%M')} "
                           "— seu PC não precisa estar ligado.")
        notificar = st.checkbox("Avisar os inscritos", value=True, key=f"pn_{k}")
        priv = {"🌍 Público agora": "public", "🔗 Não listado": "unlisted", "🔒 Privado": "private", "📅 Agendar": "private"}[quando]
        if st.button("📤 ENVIAR PARA O YOUTUBE", type="primary", use_container_width=True,
                     disabled=(quando == "📅 Agendar" and not publicar_em) or not titulo.strip(), key=f"penv_{k}"):
            arq = YT.criar_envio({
                "conta_id": conta["id"], "canal": conta["nome"], "job": str(jd), "video": str(jd / "video_final.mp4"),
                "titulo": titulo, "descricao": descricao, "tags": [t.strip() for t in tags.split(",")],
                "categoria": YT.CATEGORIAS[cat], "idioma": YT.IDIOMAS_VIDEO[idi], "para_criancas": kids,
                "conteudo_sintetico": sint, "privacidade": priv, "publicar_em": publicar_em, "notificar": notificar,
                "thumbnail": str(jd / "thumbnail.jpg") if usar_thumb else None,
                "legenda": str(jd / "legendas.srt") if usar_srt else None})
            flags = 0x08000000 if os.name == "nt" else 0
            from core.utils import env_utf8
            subprocess.Popen([sys.executable, "-m", "core.youtube_upload", str(arq)], cwd=str(C.APP_DIR),
                             stdout=open(arq.with_suffix(".log"), "a", encoding="utf-8"), stderr=subprocess.STDOUT,
                             creationflags=flags, env=env_utf8())
            st.success("Envio iniciado! Acompanhe na aba **Envios e agendados**.")
        with st.expander("Prefere subir manualmente pelo YouTube Studio?"):
            modo_manual(jd)



def modo_manual(jd: Path = None):
    from core import youtube_upload as YT
    st.markdown("Sem API: o programa abre o YouTube Studio e a pasta do vídeo, e você só arrasta o arquivo e cola os textos.")
    c1, c2 = st.columns(2)
    c1.link_button("🎬 Abrir upload do YouTube Studio", YT.LINK_STUDIO_UPLOAD, use_container_width=True)
    if jd and c2.button("📂 Abrir pasta do vídeo", use_container_width=True):
        open_folder(str(jd))
    if jd and (jd / "descricao.txt").exists():
        st.code((jd / "descricao.txt").read_text(encoding="utf-8"), language=None)


@st.fragment(run_every=3)
def painel_envios():
    from core import youtube_upload as YT
    envs = YT.listar_envios()
    if not envs:
        st.info("Nenhum envio ainda.")
        return
    ic = {"na fila": "⏳", "enviando": "📤", "enviado": "✅", "agendado": "📅", "erro": "❌"}
    for e in envs[:30]:
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            quando = ""
            if e.get("publicar_em"):
                try:
                    dt = datetime.fromisoformat(e["publicar_em"].replace("Z", "+00:00")).astimezone()
                    quando = f" · publica em {dt.strftime('%d/%m/%Y %H:%M')}"
                except Exception:
                    pass
            c1.markdown(f"{ic.get(e.get('status'), '•')} **{e['titulo']}**  \n{e.get('canal', '')} · {e.get('criado', '')}{quando}")
            if e.get("link"):
                c2.link_button("▶ Ver no YouTube", e["link"], use_container_width=True)
            if e.get("status") in ("na fila", "enviando"):
                st.progress(min(1.0, (e.get("pct") or 0) / 100))
            if e.get("log"):
                st.caption(e["log"][-1])


# ================================================================== CONFIG
def secao_atualizacao(s):
    from core import atualizador as AT
    from core.versao import NOVIDADES
    with st.expander(f"⬆️ Atualizações do programa · você está na versão {VERSAO}",
                     expanded=bool(st.session_state.pop("upd_auto_abrir", False) or st.session_state.get("upd_res"))):
        if st.session_state.get("upd_res"):
            r = st.session_state["upd_res"]
            st.success(f"Atualizado da versão {r['de']} para a {r['para']}!")
            if AT.pode_reiniciar_sozinho():
                st.info("Reiniciando o programa... a janela reabre sozinha em alguns segundos.")
                if not st.session_state.get("upd_reiniciando"):
                    st.session_state["upd_reiniciando"] = True
                    AT.reiniciar()
            else:
                st.warning("Feche o programa (⏻ Sair do programa) e abra de novo pelo atalho para usar a nova versão.")
            return
        info = st.session_state.get("upd_info") or {}
        t1, t2 = st.tabs(["🌐 Atualizar pela internet", "📦 Atualizar por arquivo .zip"])
        with t1:
            if not (s.get("atualizacao_repo") or "").strip():
                st.caption("Para atualizar com um clique, informe o repositório do GitHub onde as versões novas são "
                           "publicadas (ex.: seuusuario/AutoVideoStudio). Se ele for privado, cole também um token de leitura.")
            c1, c2 = st.columns(2)
            with c1:
                a_, b_ = st.columns([5, 1.4], vertical_alignment="bottom")
                repo = a_.text_input("Repositório das atualizações", s.get("atualizacao_repo", ""), key="upd_repo",
                                     placeholder="usuario/AutoVideoStudio")
                ok1 = b_.button("✓ Confirmar", key="upd_repo_ok", use_container_width=True)
            with c2:
                a_, b_ = st.columns([5, 1.4], vertical_alignment="bottom")
                tok = a_.text_input("Token (só se o repositório for privado)", s.get("atualizacao_token", ""),
                                    key="upd_tok", type="password")
                ok2 = b_.button("✓ Confirmar", key="upd_tok_ok", use_container_width=True)
            if ok1 or ok2:
                s["atualizacao_repo"], s["atualizacao_token"] = repo.strip(), tok.strip()
                save_settings(s)
                st.session_state.pop("upd_info", None)
                st.toast("✓ Salvo")
                st.rerun()
            auto = st.toggle("Procurar versão nova sempre que abrir o programa", s.get("atualizacao_auto", True),
                             key="upd_auto")
            if auto != s.get("atualizacao_auto", True):
                s["atualizacao_auto"] = auto
                save_settings(s)
            b1, b2 = st.columns([1, 2], vertical_alignment="center")
            if b1.button("🔎 Procurar atualização", use_container_width=True, disabled=not s.get("atualizacao_repo")):
                with st.spinner("Conferindo..."):
                    st.session_state["upd_info"] = info = AT.verificar_online()
            if info.get("erro") and info["erro"] != "sem_repo":
                b2.error(info["erro"])
            elif info.get("versao") and not info.get("nova"):
                b2.success(f"Você já está na versão mais nova ({VERSAO}).")
            if info.get("nova"):
                st.markdown(f"### 🎉 Versão {info['versao']} disponível")
                if info.get("novidades"):
                    st.markdown("\n".join(f"- {n}" for n in info["novidades"]))
                if st.button(f"⬆️ Instalar a versão {info['versao']} agora", type="primary"):
                    try:
                        with st.status("Atualizando...", expanded=True) as stt:
                            dados = AT.baixar_online(stt.write)
                            st.session_state["upd_res"] = AT.instalar_zip(dados, stt.write)
                            stt.update(label="Atualização instalada", state="complete")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Não consegui atualizar: {e}")
        with t2:
            st.caption("Escolha o arquivo AutoVideoStudio.zip da nova versão. Não precisa extrair nem copiar nada: "
                       "o programa instala sozinho e reinicia.")
            arq = st.file_uploader("Arquivo da nova versão (.zip)", type=["zip"], key="upd_zip")
            if arq is not None:
                dados = arq.getvalue()
                try:
                    ver = AT.versao_do_zip(dados)
                    aviso = "" if AT.mais_nova(ver, VERSAO) else " (não é mais nova que a sua: vai reinstalar)"
                    st.info(f"Arquivo da versão **{ver}**{aviso}.")
                    if st.button(f"⬆️ Instalar a versão {ver}", type="primary", key="upd_zip_btn"):
                        with st.status("Atualizando...", expanded=True) as stt:
                            st.session_state["upd_res"] = AT.instalar_zip(dados, stt.write)
                            stt.update(label="Atualização instalada", state="complete")
                        st.rerun()
                except Exception as e:
                    st.error(str(e))
        st.caption("Suas chaves, projetos e vídeos (pasta dados) nunca são mexidos. Antes de cada atualização o "
                   "programa guarda uma cópia da versão atual.")
        b = AT.ultimo_backup()
        if b and st.button("↩️ Voltar para a versão anterior", help=b.name):
            try:
                with st.status("Voltando...", expanded=True) as stt:
                    st.session_state["upd_res"] = AT.voltar_versao(stt.write)
                st.rerun()
            except Exception as e:
                st.error(str(e))
        if os.name == "nt" and st.button("🖼️ Recriar o atalho da Área de Trabalho com o logo"):
            import subprocess
            import sys as _sys
            raiz = Path(__file__).resolve().parent
            py = Path(_sys.executable)
            if py.name.lower() == "pythonw.exe" and (py.parent / "python.exe").exists():
                py = py.parent / "python.exe"
            r = subprocess.run([str(py), str(raiz / "criar_atalhos.py")], cwd=str(raiz), capture_output=True,
                               text=True, creationflags=0x08000000)
            st.success("Atalho recriado com o logo.") if r.returncode == 0 else st.error(r.stdout + r.stderr)
        if NOVIDADES.get(VERSAO):
            st.markdown(f"**Novidades da versão {VERSAO}:** " + " · ".join(NOVIDADES[VERSAO]))


def page_settings():
    s = load_settings()

    def ent(alvo, campo, label, valor="", **kw):
        """Campo com botão ✓ Confirmar ao lado (salva na hora, sem precisar de Enter)."""
        a_, b_ = alvo.columns([5, 1.4], vertical_alignment="bottom")
        kw["key"] = f"cfg_{campo}_{kw.get('key', '')}"
        v = a_.text_input(label, valor, **kw)
        if b_.button("✓ Confirmar", key=f"ok{kw['key']}", use_container_width=True):
            st.session_state["_salvar_cfg"] = label
        return v

    hero("⚙️", "APIs e configurações", "Conecte seus serviços. As chaves ficam salvas só no seu PC.")
    st.caption(f"As chaves ficam salvas só no seu PC, em {C.SETTINGS_FILE}")
    pw = dict(type="password")
    secao_atualizacao(s)

    st.subheader("🧠 IA de texto (divide o roteiro e cria os prompts)")
    opts = ["nenhum", "anthropic", "openai_compat", "gemini"]
    labels = {"nenhum": "Nenhuma", "anthropic": "Claude (Anthropic)", "openai_compat": "OpenAI / OpenRouter / DeepSeek / Groq / Ollama",
              "gemini": "Google Gemini"}
    s["llm_provider"] = st.radio("Provedor", opts, index=opts.index(s["llm_provider"]), format_func=labels.get, horizontal=True)
    if s["llm_provider"] == "anthropic":
        s["anthropic_key"] = ent(st, "anthropic_key", "Chave Anthropic", s["anthropic_key"], **pw)
        s["anthropic_model"] = ent(st, "anthropic_model", "Modelo", s["anthropic_model"])
        s["roteiro_model_anthropic"] = ent(st, "roteiro_model_anthropic", "Modelo do roteirista (mais forte, só para escrever roteiros)",
                                                     s.get("roteiro_model_anthropic", "claude-sonnet-5-5"))
    elif s["llm_provider"] == "openai_compat":
        s["openai_compat_base"] = ent(st, "openai_compat_base", "URL base", s["openai_compat_base"],
                                                help="OpenAI: https://api.openai.com/v1 · OpenRouter: https://openrouter.ai/api/v1 · "
                                                     "DeepSeek: https://api.deepseek.com/v1 · Ollama (grátis, local): http://localhost:11434/v1")
        s["openai_compat_key"] = ent(st, "openai_compat_key", "Chave", s["openai_compat_key"], **pw)
        s["openai_compat_model"] = ent(st, "openai_compat_model", "Modelo", s["openai_compat_model"])
    elif s["llm_provider"] == "gemini":
        s["gemini_key"] = ent(st, "gemini_key", "Chave Gemini (Google AI Studio)", s["gemini_key"], **pw)
        s["gemini_model"] = ent(st, "gemini_model", "Modelo", s["gemini_model"])

    st.subheader("🔎 YouTube Data API (Buscador de Nichos)")
    s["youtube_key"] = ent(st, "youtube_key", "Chave da YouTube Data API v3", s.get("youtube_key", ""), **pw,
                                     help="Grátis: console.cloud.google.com → criar projeto → ativar 'YouTube Data API v3' → "
                                          "Credenciais → Criar chave de API. Cota: 10.000 unidades/dia.")

    st.subheader("🎙️ Narração")
    c1, c2 = st.columns(2)
    s["elevenlabs_key"] = ent(c1, "elevenlabs_key", "Chave ElevenLabs", s["elevenlabs_key"], **pw)
    s["fishaudio_key"] = ent(c2, "fishaudio_key", "Chave Fish Audio", s["fishaudio_key"], **pw)

    st.subheader("📚 Bancos de imagens e clipes (grátis)")
    c1, c2 = st.columns(2)
    s["pexels_key"] = ent(c1, "pexels_key", "Chave Pexels", s["pexels_key"], **pw, help="pexels.com/api")
    s["pixabay_key"] = ent(c2, "pixabay_key", "Chave Pixabay", s["pixabay_key"], **pw, help="pixabay.com/api/docs")

    st.subheader("🎨 Geradores de imagem")
    st.caption("Pollinations funciona sem chave. Para os outros, cole a chave e (se quiser) troque o modelo.")
    rows = [("Replicate", "replicate_key", "replicate_model"), ("fal.ai", "fal_key", "fal_model"),
            ("Together AI", "together_key", "together_model"), ("Black Forest Labs", "bfl_key", "bfl_model")]
    for name, k, m in rows:
        c1, c2 = st.columns([3, 2])
        s[k] = ent(c1, k, f"Chave {name}", s[k], **pw)
        s[m] = ent(c2, m, f"Modelo {name}", s[m])
    with st.container(border=True):
        st.markdown("**🟢 ChatGPT (gerador de imagens da OpenAI)**")
        st.caption("É o mesmo gerador de imagens do ChatGPT, usado pela API. A chave é criada em platform.openai.com → "
                   "API keys, e a conta precisa ter crédito. A assinatura do ChatGPT Plus não vale para a API. "
                   "Na primeira vez a OpenAI pode pedir a verificação da organização para liberar os modelos de imagem.")
        c1, c2, c3 = st.columns([3, 2, 2])
        s["openai_images_key"] = ent(c1, "openai_images_key", "Chave OpenAI", s["openai_images_key"], **pw)
        s["openai_images_model"] = ent(c2, "openai_images_model", "Modelo", s["openai_images_model"],
                                                 help="Ex.: gpt-image-1.5 · gpt-image-1 · gpt-image-1-mini (mais barato). "
                                                      "Se a OpenAI lançar um modelo novo, é só digitar o nome aqui.")
        _q = {"low": "Baixa (mais barata)", "medium": "Média (recomendada)", "high": "Alta (mais cara)"}
        s["openai_images_quality"] = c3.selectbox("Qualidade", list(_q), format_func=_q.get,
                                                  index=list(_q).index(s.get("openai_images_quality", "medium")))
    c1, c2 = st.columns([3, 2])
    if s["llm_provider"] != "gemini":
        s["gemini_key"] = ent(c1, "gemini_key", "Chave Gemini (para o Google Imagen)", s["gemini_key"], **pw, key="gk2")
    else:
        c1.caption("Google Imagen usa a mesma chave Gemini informada acima.")
    s["imagen_model"] = ent(c2, "imagen_model", "Modelo Imagen", s["imagen_model"])
    with st.expander("➕ Gerador personalizado (qualquer API no padrão OpenAI /images/generations)"):
        s["custom_img_base"] = ent(st, "custom_img_base", "URL base", s["custom_img_base"], placeholder="https://.../v1")
        s["custom_img_key"] = ent(st, "custom_img_key", "Chave", s["custom_img_key"], **pw)
        s["custom_img_model"] = ent(st, "custom_img_model", "Modelo", s["custom_img_model"])

    st.subheader("⚙️ Sistema")
    c1, c2, c3 = st.columns([3, 1, 1])
    s["ffmpeg_path"] = ent(c1, "ffmpeg_path", "Pasta do FFmpeg (vazio = automático)", s["ffmpeg_path"])
    s["threads_api"] = c2.number_input("Imagens em paralelo", 1, 10, int(s["threads_api"]))
    s["threads_render"] = c3.number_input("Cenas renderizando juntas", 1, 8, int(s["threads_render"]),
                                          help="No notebook, 2 a 4 é um bom valor.")
    from core.utils import run
    try:
        v = run(["ffmpeg", "-version"]).stdout.splitlines()[0]
        st.success(f"FFmpeg encontrado: {v[:60]}")
    except Exception:
        st.error("FFmpeg não encontrado. Rode o INSTALAR.bat de novo ou informe a pasta acima.")

    if st.button("💾 Salvar todas as configurações", type="primary"):
        st.session_state["_salvar_cfg"] = "Configurações"
    if st.session_state.pop("_salvar_cfg", None) is not None:
        save_settings(s)
        st.toast("✓ Salvo!")
        st.success("Configurações salvas.")


{"Novo vídeo": page_new, "Dobra de canais": page_dobra, "Fila de vídeos": page_fila, "BUSCADOR DE NICHOS": page_niches, "Trabalhos": page_jobs, "Publicar no YouTube": page_publish, "APIs e configurações": page_settings}[page]()
