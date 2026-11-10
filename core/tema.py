"""Visual do AutoVideo Studio: temas escuro (azul-marinho) e claro (vermelho), cartões e efeitos."""
import base64
from pathlib import Path

import streamlit as st

ASSETS = Path(__file__).resolve().parent.parent / "assets"

TEMAS = {
    "escuro": {
        "base": "dark", "bg": "#070F24", "bg2": "#0B1633", "card": "#0F1D42", "card2": "#132554",
        "input": "#0A1530", "border": "#1E3270", "text": "#EAF0FF", "muted": "#8FA3D1",
        "accent": "#2F7BFF", "accent2": "#5BA3FF", "glow": "rgba(47,123,255,.45)", "brand": "#F42B03",
        "grad": "linear-gradient(135deg,#1D4ED8 0%,#2F7BFF 55%,#38BDF8 100%)",
        "hero": "radial-gradient(1200px 300px at 0% 0%, rgba(47,123,255,.35), transparent 60%),"
                "radial-gradient(800px 260px at 100% 0%, rgba(244,43,3,.18), transparent 60%), #0B1633",
        "app": "radial-gradient(1400px 700px at 80% -10%, rgba(47,123,255,.16), transparent 60%), #070F24",
        "side": "linear-gradient(180deg,#0A1636 0%,#06102A 100%)",
        "shadow": "0 10px 30px rgba(0,0,0,.45)", "logo": "logo_escuro.png",
    },
    "claro": {
        "base": "light", "bg": "#F6F7FB", "bg2": "#FFFFFF", "card": "#FFFFFF", "card2": "#FFF5F2",
        "input": "#F3F4F8", "border": "#E6E8F0", "text": "#0A1230", "muted": "#5B6380",
        "accent": "#F42B03", "accent2": "#FF5A36", "glow": "rgba(244,43,3,.35)", "brand": "#F42B03",
        "grad": "linear-gradient(135deg,#D91F00 0%,#F42B03 50%,#FF6A3D 100%)",
        "hero": "radial-gradient(1200px 300px at 0% 0%, rgba(244,43,3,.14), transparent 60%),"
                "radial-gradient(800px 260px at 100% 0%, rgba(10,18,48,.06), transparent 60%), #FFFFFF",
        "app": "radial-gradient(1400px 700px at 80% -10%, rgba(244,43,3,.07), transparent 60%), #F6F7FB",
        "side": "linear-gradient(180deg,#FFFFFF 0%,#FFF6F3 100%)",
        "shadow": "0 10px 28px rgba(10,18,48,.08)", "logo": "logo_claro.png",
    },
}


def _b64(path: Path) -> str:
    try:
        return base64.b64encode(path.read_bytes()).decode()
    except Exception:
        return ""


def aplicar_tema(nome: str):
    t = TEMAS.get(nome, TEMAS["escuro"])
    # Também ajusta as cores nativas (tabelas, gráficos, sliders) quando a versão do Streamlit permite
    try:
        for k, v in {"base": t["base"], "primaryColor": t["accent"], "backgroundColor": t["bg"],
                     "secondaryBackgroundColor": t["card"], "textColor": t["text"]}.items():
            if st._config.get_option(f"theme.{k}") != v:
                st._config.set_option(f"theme.{k}", v)
    except Exception:
        pass
    css = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap');
:root {{ --accent:{t['accent']}; --text:{t['text']}; --muted:{t['muted']}; --card:{t['card']}; --border:{t['border']}; }}
html, body, .stApp, [class*="css"], p, label, li, input, textarea, button, h1, h2, h3, h4 {{ font-family:'Poppins',sans-serif !important; }}
.stApp {{ background:{t['app']} !important; color:{t['text']}; }}
[data-testid="stHeader"] {{ background:transparent !important; }}
/* esconde as marcas do Streamlit para parecer um programa próprio */
[data-testid="stToolbar"], [data-testid="stAppDeployButton"], [data-testid="stDecoration"], #MainMenu, footer,
[data-testid="stMainMenu"], [data-testid="InputInstructions"] {{ display:none !important; visibility:hidden !important; }}
[data-testid="stStatusWidget"] {{ background:{t['card']}; border:1px solid {t['border']}; border-radius:10px; padding:2px 8px; }}
.block-container {{ padding-top:1.4rem; max-width:1250px; }}
.stApp p, .stApp label, .stApp li, .stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"] p {{ color:{t['text']}; }}
[data-testid="stCaptionContainer"], .stApp small {{ color:{t['muted']} !important; }}

/* ---------- barra lateral ---------- */
[data-testid="stSidebar"] {{ background:{t['side']} !important; border-right:1px solid {t['border']}; }}
[data-testid="stSidebar"] .stButton > button {{
  justify-content:flex-start; text-align:left; padding:.85rem 1rem; margin:.15rem 0; border-radius:14px;
  font-size:1.02rem; font-weight:600; background:transparent; border:1px solid transparent; color:{t['text']};
  transition:all .2s ease; }}
[data-testid="stSidebar"] .stButton > button p {{ font-size:1.02rem; font-weight:600; }}
[data-testid="stSidebar"] .stButton > button:hover {{ background:{t['card']}; border-color:{t['border']};
  transform:translateX(4px); color:{t['accent']}; }}
[data-testid="stSidebar"] .stButton > button[kind="primary"], [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {{
  background:{t['grad']} !important; color:#fff !important; border:none; box-shadow:0 8px 22px {t['glow']}; }}
[data-testid="stSidebar"] .stButton > button[kind="primary"] p, [data-testid="stSidebar"] [data-testid="stBaseButton-primary"] p {{ color:#fff !important; }}
.av-logo {{ width:100%; margin:.2rem 0 1.4rem 0; filter:drop-shadow(0 6px 18px {t['glow']}); }}
.av-side-foot {{ font-size:.8rem; color:{t['muted']}; margin-top:1rem; line-height:1.5; }}

/* ---------- cabeçalho (hero) ---------- */
.av-hero {{ background:{t['hero']}; border:1px solid {t['border']}; border-radius:22px; padding:1.4rem 1.8rem;
  margin-bottom:1.3rem; display:flex; align-items:center; gap:1.2rem; box-shadow:{t['shadow']};
  animation:avIn .45s ease both; }}
.av-hero .ic {{ font-size:2.6rem; width:76px; height:76px; border-radius:20px; display:flex; align-items:center;
  justify-content:center; background:{t['grad']}; box-shadow:0 10px 26px {t['glow']}; flex-shrink:0; }}
.av-hero h1 {{ font-size:2rem !important; font-weight:800 !important; margin:0 !important; padding:0 !important;
  color:{t['text']} !important; letter-spacing:-.5px; }}
.av-hero p {{ margin:.25rem 0 0 0; color:{t['muted']} !important; font-size:1rem; }}
@keyframes avIn {{ from {{ opacity:0; transform:translateY(8px); }} to {{ opacity:1; transform:none; }} }}

/* ---------- cartões ---------- */
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) ,
[data-testid="stExpander"] details, [data-testid="stMetric"], [data-baseweb="tab-panel"] {{
  background:{t['card']}; border:1px solid {t['border']} !important; border-radius:18px !important;
  box-shadow:{t['shadow']}; transition:transform .2s ease, box-shadow .2s ease, border-color .2s ease; }}
[data-baseweb="tab-panel"] {{ padding:1.4rem 1.5rem !important; margin-top:.6rem; animation:avIn .35s ease both; }}
[data-testid="stMetric"] {{ padding:1rem 1.1rem; }}
[data-testid="stMetric"]:hover, [data-testid="stExpander"] details:hover {{ transform:translateY(-3px);
  border-color:{t['accent']} !important; box-shadow:0 14px 34px {t['glow']}; }}
[data-testid="stMetricValue"] {{ font-weight:700; color:{t['text']}; }}
[data-testid="stMetricLabel"] p {{ color:{t['muted']} !important; }}
[data-testid="stExpander"] summary {{ font-weight:600; padding:.9rem 1rem; }}
[data-testid="stExpander"] summary:hover {{ color:{t['accent']}; }}
.av-card {{ background:{t['card']}; border:1px solid {t['border']}; border-radius:18px; padding:1.1rem 1.2rem;
  box-shadow:{t['shadow']}; transition:all .2s ease; min-height:128px; }}
.av-card:hover {{ transform:translateY(-4px); border-color:{t['accent']}; box-shadow:0 16px 36px {t['glow']}; }}
.av-card .ic {{ font-size:1.9rem; }}
.av-card b {{ display:block; font-size:1.05rem; margin-top:.35rem; color:{t['text']}; }}
.av-card span {{ font-size:.86rem; color:{t['muted']}; }}
h3 {{ border-left:5px solid {t['accent']}; padding-left:.7rem !important; font-weight:700 !important; }}

/* ---------- abas ---------- */
[data-baseweb="tab-list"] {{ gap:.2rem; background:{t['card']}; padding:.45rem; border-radius:16px;
  border:1px solid {t['border']}; flex-wrap:wrap; }}
[data-baseweb="tab"] {{ border-radius:12px !important; padding:.6rem .8rem !important; height:auto !important;
  transition:all .2s ease; background:transparent; }}
[data-baseweb="tab"] p {{ font-size:1rem !important; font-weight:600; color:{t['muted']}; }}
[data-baseweb="tab"]:hover p {{ color:{t['accent']}; }}
[data-baseweb="tab"][aria-selected="true"] {{ background:{t['grad']} !important; box-shadow:0 6px 18px {t['glow']}; }}
[data-baseweb="tab"][aria-selected="true"] p {{ color:#fff !important; }}
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{ display:none !important; }}

/* ---------- campos ---------- */
[data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="select"] > div, [data-baseweb="base-input"] {{
  background:{t['input']} !important; border-color:{t['border']} !important; border-radius:12px !important; }}
[data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within, [data-baseweb="select"] > div:focus-within {{
  border-color:{t['accent']} !important; box-shadow:0 0 0 3px {t['glow']} !important; }}
input, textarea, [data-baseweb="select"] div {{ color:{t['text']} !important; -webkit-text-fill-color:{t['text']} !important; }}
[data-baseweb="popover"] ul, [data-baseweb="menu"] {{ background:{t['card']} !important; }}
[data-baseweb="popover"] li {{ color:{t['text']} !important; }}
[data-baseweb="tag"] {{ background:{t['grad']} !important; border-radius:8px !important; }}
[data-baseweb="tag"] span {{ color:#fff !important; }}
[role="slider"] {{ background:{t['accent']} !important; box-shadow:0 0 0 6px {t['glow']} !important; }}

/* ---------- botões ---------- */
.stButton > button, .stDownloadButton > button {{ border-radius:12px; font-weight:600; border:1px solid {t['border']};
  background:{t['card']}; color:{t['text']}; transition:all .2s ease; }}
.stButton > button:hover, .stDownloadButton > button:hover {{ border-color:{t['accent']}; color:{t['accent']};
  transform:translateY(-2px); box-shadow:0 8px 20px {t['glow']}; }}
.main .stButton > button[kind="primary"], [data-testid="stMain"] [data-testid="stBaseButton-primary"] {{
  background:{t['grad']} !important; color:#fff !important; border:none !important; padding:.95rem 1.2rem;
  font-size:1.12rem; font-weight:700; letter-spacing:.3px; box-shadow:0 10px 28px {t['glow']};
  background-size:200% 200% !important; animation:avPulse 3.5s ease infinite; }}
[data-testid="stMain"] [data-testid="stBaseButton-primary"] p {{ color:#fff !important; font-size:1.12rem; font-weight:700; }}
[data-testid="stMain"] [data-testid="stBaseButton-primary"]:hover {{ transform:translateY(-3px) scale(1.01);
  box-shadow:0 16px 38px {t['glow']}; }}
@keyframes avPulse {{ 0%,100% {{ box-shadow:0 10px 28px {t['glow']}; }} 50% {{ box-shadow:0 10px 40px {t['glow']}; }} }}

/* ---------- progresso, alertas, tabelas ---------- */
[data-testid="stProgress"] > div > div > div > div {{ background:{t['grad']} !important; }}
[data-testid="stProgress"] > div > div > div {{ height:12px !important; border-radius:8px; }}
[data-testid="stAlert"] {{ border-radius:14px; }}
[data-testid="stDataFrame"] {{ border:1px solid {t['border']}; border-radius:14px; overflow:hidden; }}
[data-testid="stCode"] pre, pre {{ background:{t['input']} !important; border-radius:12px; }}
hr {{ border-color:{t['border']} !important; }}
::-webkit-scrollbar {{ width:10px; height:10px; }} ::-webkit-scrollbar-thumb {{ background:{t['border']}; border-radius:8px; }}
/* ---------- etapas do Novo vídeo (lista estilo "pipeline") ---------- */
@keyframes avSlide {{ from {{ opacity:0; transform:translateY(14px) scale(.985); }} to {{ opacity:1; transform:none; }} }}
@keyframes avPulseDot {{ 0%,100% {{ box-shadow:0 0 0 0 {t['glow']}; }} 50% {{ box-shadow:0 0 0 7px rgba(0,0,0,0); }} }}
@keyframes avShine {{ from {{ background-position:-200% 0; }} to {{ background-position:200% 0; }} }}
@keyframes avOpen {{ from {{ opacity:0; transform:translateY(-6px); }} to {{ opacity:1; transform:none; }} }}
[class*="st-key-etapa_"] {{ background:{t['card']}; border:1px solid {t['border']}; border-radius:18px; padding:.55rem .9rem;
  margin-bottom:.15rem; transition:all .25s ease; animation:avSlide .45s ease both; position:relative; overflow:hidden; }}
[class*="st-key-etapa_"]:hover {{ border-color:{t['accent']}; box-shadow:0 10px 30px {t['glow']}; transform:translateY(-2px); }}
[class*="st-key-etapa_"]::before {{ content:""; position:absolute; left:0; top:0; bottom:0; width:4px; background:transparent;
  transition:background .25s ease; }}
[class*="st-key-etapa_"]:hover::before {{ background:{t['grad']}; }}
.st-key-etapa_1 {{ animation-delay:.03s; }} .st-key-etapa_2 {{ animation-delay:.07s; }} .st-key-etapa_3 {{ animation-delay:.11s; }}
.st-key-etapa_4 {{ animation-delay:.15s; }} .st-key-etapa_5 {{ animation-delay:.19s; }} .st-key-etapa_6 {{ animation-delay:.23s; }}
.st-key-etapa_7 {{ animation-delay:.27s; }} .st-key-etapa_8 {{ animation-delay:.31s; }} .st-key-etapa_9 {{ animation-delay:.35s; }}
.st-key-etapa_10 {{ animation-delay:.39s; }}
.av-row {{ display:flex; align-items:center; gap:1rem; min-height:56px; }}
.av-row .ico {{ width:46px; height:46px; border-radius:14px; display:flex; align-items:center; justify-content:center;
  font-size:1.35rem; background:{t['input']}; border:1px solid {t['border']}; position:relative; flex-shrink:0;
  transition:transform .25s ease, background .25s ease; }}
[class*="st-key-etapa_"]:hover .av-row .ico {{ transform:rotate(-6deg) scale(1.08); background:{t['card2']}; }}
.av-row .ico .dot {{ position:absolute; top:-4px; right:-4px; width:12px; height:12px; border-radius:50%;
  background:{t['muted']}; border:2px solid {t['card']}; }}
.av-row .ico .dot.ok {{ background:#21C354; animation:avPulseDot 2.2s infinite; }}
.av-row .ico .dot.aberta {{ background:{t['accent']}; animation:avPulseDot 1.4s infinite; }}
.av-row .tx b {{ font-size:1.06rem; color:{t['text']}; }} .av-row .tx .n {{ color:{t['muted']}; margin-right:.35rem; font-weight:600; }}
.av-row .tx .res {{ display:block; font-size:.86rem; color:{t['muted']}; margin-top:.1rem; white-space:nowrap; overflow:hidden;
  text-overflow:ellipsis; max-width:820px; }}
.av-badge {{ font-size:.66rem; font-weight:700; letter-spacing:.6px; padding:.15rem .5rem; border-radius:6px; margin-left:.5rem;
  vertical-align:middle; background:{t['card2']}; color:{t['accent2']}; border:1px solid {t['border']}; }}
[class*="st-key-corpo_"][class*="_off"] {{ display:none !important; }}
[class*="st-key-corpo_"][class*="_on"] {{ animation:avOpen .35s ease both; border-top:1px dashed {t['border']}; padding-top:.9rem;
  margin-top:.4rem; }}
.st-key-titulo_card {{ background:{t['card']}; border:1px solid {t['border']}; border-radius:20px; padding:1rem 1.2rem;
  box-shadow:{t['shadow']}; animation:avSlide .4s ease both; margin-bottom:.8rem; }}

/* ---------- botões de confirmar e efeitos gerais ---------- */
[data-testid="stFormSubmitButton"] > button {{ border-radius:12px; font-weight:700; background:{t['grad']} !important;
  color:#fff !important; border:none !important; background-size:200% 100% !important; transition:all .2s ease;
  box-shadow:0 6px 16px {t['glow']}; }}
[data-testid="stFormSubmitButton"] > button p {{ color:#fff !important; font-weight:700; white-space:nowrap; }}
[data-testid="stFormSubmitButton"] > button {{ white-space:nowrap; min-height:42px; }}
[data-testid="stFormSubmitButton"] > button:hover {{ transform:translateY(-2px) scale(1.03); animation:avShine 1.2s linear infinite; }}
[data-testid="stForm"] {{ border:none !important; padding:0 !important; }}
[data-testid="stToast"] {{ border-radius:14px !important; border:1px solid {t['accent']} !important; }}
[data-baseweb="radio"] > div:first-child, [data-baseweb="checkbox"] > div:first-child {{ transition:transform .2s ease; }}
[data-baseweb="radio"]:hover > div:first-child, [data-baseweb="checkbox"]:hover > div:first-child {{ transform:scale(1.15); }}
[data-testid="stSlider"] [role="slider"] {{ transition:transform .15s ease; }}
[data-testid="stSlider"] [role="slider"]:hover {{ transform:scale(1.25); }}
[data-testid="stImage"] img, [data-testid="stVideo"] video {{ border-radius:12px; transition:transform .3s ease; }}
[data-testid="stImage"] img:hover {{ transform:scale(1.02); }}
[data-testid="stProgress"] > div > div > div > div {{ background-size:40px 40px !important;
  background-image:linear-gradient(45deg,rgba(255,255,255,.18) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.18) 50%,
  rgba(255,255,255,.18) 75%,transparent 75%,transparent), {t['grad']} !important; animation:avStripes 1s linear infinite; }}
@keyframes avStripes {{ from {{ background-position:0 0, 0 0; }} to {{ background-position:40px 0, 0 0; }} }}
/* ---- Base de canais (cartões do Buscador de Nichos) ---- */
[class*="st-key-cc_"] {{ background:{t['card']}; border:1px solid {t['border']}; border-top:3px solid {t['brand']};
  border-radius:10px; padding:12px 14px 6px; box-shadow:{t['shadow']}; transition:transform .15s, box-shadow .15s;
  animation:avSlide .35s ease both; gap:.45rem !important; }}
[class*="st-key-cc_"]:hover {{ transform:translateY(-2px); box-shadow:0 14px 34px {t['glow']}; }}
.cc-head {{ display:flex; gap:10px; align-items:center; }}
.cc-av {{ width:40px; height:40px; border-radius:50%; object-fit:cover; flex:none; background:{t['input']}; border:1px solid {t['border']}; }}
.cc-tit {{ min-width:0; }}
.stApp a.cc-nome {{ font-weight:800; font-size:16px; color:{t['text']} !important; text-decoration:none; }}
.stApp a.cc-nome:hover {{ color:{t['accent']} !important; }}
.cc-flag {{ font-size:15px; }}
.stApp .cc-sub {{ font-size:12px; color:{t['muted']}; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }}
.cc-badge-row {{ text-align:right; margin-top:-2px; height:22px; }}
.cc-badge {{ display:inline-block; font-size:12px; font-weight:700; color:{t['brand']}; background:rgba(244,43,3,.12);
  border:1px solid rgba(244,43,3,.35); border-radius:4px; padding:1px 8px; }}
.cc-thumbs {{ display:grid; grid-template-columns:repeat(3,1fr); gap:6px; margin:2px 0 8px; }}
.cc-thumbs a {{ position:relative; display:block; border-radius:6px; overflow:hidden; aspect-ratio:16/9; background:{t['input']}; }}
.cc-thumbs img {{ width:100%; height:100%; object-fit:cover; display:block; transition:transform .2s; }}
.cc-thumbs a:hover img {{ transform:scale(1.06); }}
.cc-thumbs span {{ position:absolute; right:4px; bottom:4px; background:rgba(0,0,0,.78); color:#fff; font-size:11px;
  font-weight:700; padding:1px 5px; border-radius:3px; }}
.cc-stats {{ display:grid; grid-template-columns:repeat(4,1fr); border:1px solid {t['border']}; border-radius:6px;
  background:{t['bg2']}; padding:9px 4px; text-align:center; margin-bottom:8px; }}
.cc-stats b {{ display:block; font-size:16px; font-weight:800; color:{t['text']}; }}
.cc-stats small {{ display:block; font-size:9.5px; letter-spacing:.06em; color:{t['muted']}; margin-top:2px; }}
.stApp .cc-stats b.cc-face {{ color:#F59E0B; }}
.stApp .cc-foot {{ font-size:12px; color:{t['muted']}; margin:0 0 4px; }}
.stApp .cc-foot b {{ color:#22C55E; }}
.stApp .cc-foot2 {{ display:flex; justify-content:space-between; align-items:center; font-size:12px; color:{t['muted']}; }}
.cc-nota {{ font-weight:800; font-size:12px; color:#fff; background:{t['grad']}; border-radius:999px; padding:1px 9px; }}
.stApp .cc-rank {{ font-size:12px; color:{t['muted']}; font-weight:700; }}
[class*="st-key-cc_"] [data-testid="stPopover"] button, [class*="st-key-cc_"] [class*="st-key-bc_fav_"] button {{
  min-height:30px; padding:2px 8px; border-radius:6px; }}
[class*="st-key-cc_"] [class*="st-key-bc_fav_"] button p {{ font-size:18px !important; color:{t['brand']}; }}
.st-key-bc_abas button {{ min-height:38px; padding:4px 8px; }}
.st-key-bc_abas button p {{ font-size:13px !important; white-space:nowrap; }}
.st-key-bc_filtros {{ background:{t['card']}; border:1px solid {t['border']}; border-radius:10px; padding:10px 14px; }}
[class*="st-key-fila_item"] {{ animation:avSlide .35s ease both; background:{t['card']}; border:1px solid {t['border']};
  border-radius:20px; padding:1.1rem 1.3rem .8rem; margin-bottom:.8rem; transition:all .25s ease; }}
[class*="st-key-fila_item"]:hover {{ border-color:{t['accent']}; box-shadow:0 12px 32px {t['glow']}; }}
.pj-top {{ display:flex; justify-content:space-between; gap:1rem; }}
.pj-badge {{ font-size:.72rem; font-weight:800; letter-spacing:1px; padding:.2rem .6rem; border-radius:7px; border:1px solid; }}
.pj-tempo {{ font-size:.82rem; color:{t['muted']}; margin-left:.6rem; }}
.pj-tit {{ font-size:1.25rem; font-weight:800; color:{t['text']}; margin-top:.45rem; }}
.pj-sub {{ font-size:.9rem; color:{t['muted']}; margin-top:.15rem; }}
.pj-pct {{ text-align:right; font-size:2.4rem; font-weight:800; color:{t['text']}; line-height:1; white-space:nowrap; }}
.pj-pct small {{ font-size:1rem; color:{t['muted']}; }} .pj-pct span {{ display:block; font-size:.7rem; letter-spacing:2px; color:{t['muted']}; margin-top:.4rem; }}
.pj-bar {{ height:7px; border-radius:6px; background:{t['input']}; margin:.9rem 0 .7rem; overflow:hidden; }}
.pj-bar div {{ height:7px; border-radius:6px; background:{t['grad']}; transition:width .6s ease; }}
.pj-pills {{ display:grid; grid-template-columns:repeat(5,1fr); gap:.5rem; }}
.pj-pills .pill {{ text-align:center; font-size:.82rem; font-weight:600; padding:.45rem; border-radius:10px; background:{t['input']};
  color:{t['muted']}; border:1px solid {t['border']}; }}
.pj-pills .pill.ok {{ background:rgba(33,195,84,.13); color:#4ADE80; border-color:rgba(33,195,84,.35); }}
.pj-pills .pill.agora {{ background:{t['card2']}; color:{t['accent2']}; border-color:{t['accent']}; animation:avPulseDot 1.6s infinite; }}
.pj-mets {{ display:grid; grid-template-columns:repeat(4,1fr); gap:.7rem; margin:.9rem 0 .8rem; }}
.pj-mets div {{ background:{t['input']}; border:1px solid {t['border']}; border-radius:14px; padding:.7rem .9rem; }}
.pj-mets small {{ display:block; font-size:.7rem; letter-spacing:1.2px; color:{t['muted']}; font-weight:700; }}
.pj-mets b {{ display:block; font-size:1.35rem; color:{t['text']}; margin:.2rem 0 .1rem; }}
.pj-mets span {{ font-size:.78rem; color:{t['muted']}; }}
.st-key-projeto_aberto_box {{ animation:avOpen .35s ease both; border-color:{t['accent']} !important; }}
[class*="st-key-etapa_"] [data-testid="stBaseButton-primary"], [class*="st-key-etapa_"] [data-testid="stBaseButton-secondary"] {{
  padding:.45rem .6rem !important; font-size:.9rem !important; animation:none !important; min-height:0; }}
[class*="st-key-etapa_"] [data-testid="stBaseButton-primary"] p, [class*="st-key-etapa_"] [data-testid="stBaseButton-secondary"] p {{
  font-size:.9rem !important; }}
</style>"""
    st.markdown(css, unsafe_allow_html=True)
    return t


def logo_sidebar(nome: str):
    t = TEMAS.get(nome, TEMAS["escuro"])
    b = _b64(ASSETS / t["logo"])
    if b:
        st.sidebar.markdown(f'<img class="av-logo" src="data:image/png;base64,{b}">', unsafe_allow_html=True)
    else:
        st.sidebar.title("AutoVideo Studio")


def hero(icone: str, titulo: str, subtitulo: str = ""):
    st.markdown(f'<div class="av-hero"><div class="ic">{icone}</div><div><h1>{titulo}</h1>'
                f'<p>{subtitulo}</p></div></div>', unsafe_allow_html=True)


def cartoes(itens):
    """itens = [(ícone, título, texto)] mostrados como cartões lado a lado."""
    cols = st.columns(len(itens))
    for c, (ic, tt, tx) in zip(cols, itens):
        c.markdown(f'<div class="av-card"><div class="ic">{ic}</div><b>{tt}</b><span>{tx}</span></div>',
                   unsafe_allow_html=True)
