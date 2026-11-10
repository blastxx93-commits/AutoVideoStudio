"""Configurações, presets e caminhos do AutoVideo Studio."""
import json
import os
import shutil
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = APP_DIR / "dados"
SETTINGS_FILE = DATA_DIR / "configuracoes.json"
PROFILES_DIR = DATA_DIR / "perfis"
JOBS_DIR = DATA_DIR / "trabalhos"
ASSETS_DIR = APP_DIR / "assets"
SKILLS_DIR = APP_DIR / "skills"
SFX_DIR = ASSETS_DIR / "efeitos_sonoros"
MUSIC_DIR = ASSETS_DIR / "musicas"

for d in (DATA_DIR, PROFILES_DIR, JOBS_DIR, SFX_DIR, MUSIC_DIR):
    d.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT, FPS = 1920, 1080, 30
RESOLUCOES = {"1080p (Full HD)": (1920, 1080), "2K (1440p)": (2560, 1440)}

# ----------------------------------------------------------------- APIs
DEFAULT_SETTINGS = {
    # Cérebro (divide roteiro em cenas e cria prompts)
    "llm_provider": "nenhum",          # nenhum | anthropic | openai_compat | gemini
    "anthropic_key": "",
    "anthropic_model": "claude-haiku-5-5",
    "openai_compat_key": "",
    "openai_compat_base": "https://api.openai.com/v1",
    "openai_compat_model": "gpt-4o-mini",
    "gemini_key": "",
    "gemini_model": "gemini-2.5-flash",
    # Roteirista (modelo mais forte para escrever o roteiro)
    "roteiro_model_anthropic": "claude-sonnet-5-5",
    "roteiro_model_outro": "",
    # YouTube Data API (Buscador de Nichos)
    "youtube_key": "",
    "atualizacao_repo": "blastxx93-commits/AutoVideoStudio",      # repositório do GitHub com as atualizações (ex.: usuario/AutoVideoStudio)
    "atualizacao_token": "",     # só se o repositório for privado (token de leitura)
    "atualizacao_ramo": "main",
    "atualizacao_auto": True,    # procurar versão nova ao abrir o programa
    # Narração
    "elevenlabs_key": "",
    "fishaudio_key": "",
    # Bancos de imagens/clipes
    "pexels_key": "",
    "pixabay_key": "",
    # Geradores de imagem
    "replicate_key": "",
    "replicate_model": "black-forest-labs/flux-schnell",
    "fal_key": "",
    "fal_model": "fal-ai/flux/schnell",
    "together_key": "",
    "together_model": "black-forest-labs/FLUX.1-schnell",
    "openai_images_key": "",
    "openai_images_model": "gpt-image-1.5",
    "openai_images_quality": "medium",   # low | medium | high
    "bfl_key": "",
    "bfl_model": "flux-pro-1.1",
    # Imagen do Google (mesma família do Google Flow) via Gemini API
    "imagen_model": "imagen-4.0-generate-001",
    # Gerador personalizado (qualquer API compatível com OpenAI /images/generations)
    "custom_img_name": "Meu gerador",
    "custom_img_base": "",
    "custom_img_key": "",
    "custom_img_model": "",
    # Sistema
    "tema": "escuro",
    "ffmpeg_path": "",
    "threads_api": 4,
    "threads_render": 2,
}


def load_settings() -> dict:
    s = dict(DEFAULT_SETTINGS)
    if SETTINGS_FILE.exists():
        try:
            s.update(json.loads(SETTINGS_FILE.read_text(encoding="utf-8")))
        except Exception:
            pass
    return s


def save_settings(s: dict):
    s = {k: (v.strip().strip('"').strip("'") if isinstance(v, str) else v) for k, v in s.items()}
    SETTINGS_FILE.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")


def ffmpeg_bin(name="ffmpeg") -> str:
    s = load_settings()
    p = (s.get("ffmpeg_path") or "").strip().strip('"')
    if p:
        cand = Path(p)
        if cand.is_dir():
            exe = cand / (name + (".exe" if os.name == "nt" else ""))
            if exe.exists():
                return str(exe)
        elif cand.exists() and name == "ffmpeg":
            return str(cand)
        elif cand.exists():
            sib = cand.parent / (name + cand.suffix)
            if sib.exists():
                return str(sib)
    found = shutil.which(name)
    return found or name


# ----------------------------------------------------------------- Presets
# Estilos visuais (texto adicionado ao prompt das imagens geradas por IA)
# Estilos clássicos (só texto). Os 14 estilos com miniatura vêm de core/estilos.py e ficam em primeiro.
_ESTILOS_CLASSICOS = {
    "Cinematográfico": "cinematic film still, dramatic lighting, shallow depth of field, anamorphic lens, rich color grading, highly detailed, 35mm",
    "Documentário dark": "dark moody documentary photograph, low key lighting, deep shadows, desaturated, gritty film grain, mysterious atmosphere",
    "Webdoc / foto histórica": "realistic archival documentary photograph, vintage photo, film grain, natural lighting, historical accuracy, editorial journalism style",
    "Desenho animado 2D": "2D cartoon illustration, flat colors, bold outlines, vibrant, expressive characters, animated explainer style",
    "Animação 3D": "3D animated movie style render, soft global illumination, stylized characters, vibrant colors, high quality CGI",
    "Anime": "anime style illustration, detailed background art, cel shading, dramatic sky, studio quality",
    "Pintura a óleo / mitologia": "epic classical oil painting, renaissance style, dramatic chiaroscuro, mythological scene, museum masterpiece, rich textures",
    "Ilustração de livro": "detailed storybook illustration, watercolor and ink, warm colors, whimsical",
    "Noir preto e branco": "black and white film noir photograph, high contrast, hard shadows, 1940s, smoke, cinematic",
    "Realista (foto)": "ultra realistic photograph, natural light, DSLR, sharp focus, 8k",
    "Personalizado": "",
}

from .estilos import ESTILOS as _ESTILOS  # noqa: E402
VISUAL_STYLES = {**{n: e["prompt"] for n, e in _ESTILOS.items()}, **_ESTILOS_CLASSICOS}

NEGATIVE_HINT = "no text, no watermark, no logo, no letters, no captions"

# Movimento das imagens
MOTIONS = ["Aleatório", "Zoom in", "Zoom out", "Pan esquerda→direita", "Pan direita→esquerda", "Pan cima→baixo", "Estático"]

# Transições (nomes do xfade do FFmpeg)
TRANSITIONS = {
    "Corte seco (sem transição)": None,
    "Fade (dissolver)": "fade",
    "Fade pelo preto": "fadeblack",
    "Fade pelo branco": "fadewhite",
    "Deslizar esquerda": "slideleft",
    "Deslizar direita": "slideright",
    "Empurrar (smooth)": "smoothleft",
    "Wipe esquerda": "wipeleft",
    "Círculo abrindo": "circleopen",
    "Desfoque (zoom)": "zoomin",
    "Pixelizar": "pixelize",
    "Radial": "radial",
    "Aleatório": "random",
}
RANDOM_POOL = ["fade", "fadeblack", "slideleft", "smoothleft", "wipeleft", "circleopen", "dissolve", "radial", "smoothright"]

# Estilos de legenda (ASS). Cores no formato &HAABBGGRR
SUBTITLE_STYLES = {
    "Clássica (branca, contorno preto)": dict(font="Arial", size=58, bold=1, primary="&H00FFFFFF", outline_c="&H00000000",
                                             back="&H80000000", border_style=1, outline=3, shadow=1, align=2, margin_v=70,
                                             words=7, karaoke=False, upper=False, highlight=None),
    "Amarela forte": dict(font="Arial Black", size=60, bold=1, primary="&H0000E6FF", outline_c="&H00000000",
                          back="&H80000000", border_style=1, outline=4, shadow=2, align=2, margin_v=70,
                          words=6, karaoke=False, upper=False, highlight=None),
    "Caixa preta (estilo TV)": dict(font="Arial", size=52, bold=1, primary="&H00FFFFFF", outline_c="&H64000000",
                                    back="&H64000000", border_style=3, outline=8, shadow=0, align=2, margin_v=60,
                                    words=8, karaoke=False, upper=False, highlight=None),
    "Karaokê (palavra destacada)": dict(font="Arial Black", size=64, bold=1, primary="&H0000E6FF", secondary="&H00FFFFFF",
                                        outline_c="&H00000000", back="&H80000000", border_style=1, outline=4, shadow=2,
                                        align=2, margin_v=80, words=5, karaoke=True, upper=True, highlight=None),
    "Impacto central (estilo Shorts)": dict(font="Impact", size=96, bold=0, primary="&H00FFFFFF", outline_c="&H00000000",
                                            back="&H80000000", border_style=1, outline=6, shadow=3, align=5, margin_v=0,
                                            words=3, karaoke=False, upper=True, highlight=None),
    "Cinema (itálico discreto)": dict(font="Georgia", size=50, bold=0, italic=1, primary="&H00F0F0F0", outline_c="&H00101010",
                                      back="&H80000000", border_style=1, outline=2, shadow=1, align=2, margin_v=55,
                                      words=9, karaoke=False, upper=False, highlight=None),
}

ELEVEN_MODELS = ["eleven_multilingual_v2", "eleven_v3", "eleven_turbo_v2_5", "eleven_flash_v2_5"]
FISH_MODELS = ["s2.1-pro-free", "s2-pro", "s1"]

IMAGE_PROVIDERS = [
    "Pollinations (Flux grátis, sem chave)",
    "Replicate (Flux e outros)",
    "fal.ai (Flux e outros)",
    "Together AI (Flux)",
    "Black Forest Labs (Flux oficial)",
    "ChatGPT / OpenAI (gpt-image)",
    "Google Imagen (mesma família do Flow)",
    "Gerador personalizado",
]

STOCK_SOURCES = ["Pexels", "Pixabay", "Pasta do meu PC"]


def pct_banco(job: dict) -> int:
    """Compatível com trabalhos antigos que só tinham modo_visual."""
    if "pct_banco" in job and job.get("pct_banco") is not None:
        return int(job["pct_banco"])
    return 100 if job.get("modo_visual") == "Banco" else 0


def default_job() -> dict:
    return {
        "titulo": "",
        "roteiro": "",
        "modo_roteiro": "Já tenho",
        "ad_link": "",
        "ad_idioma": "English",
        "ad_angulo": "Automático (a IA escolhe o ângulo mais forte e diferente)",
        "ad_minutos": 0,
        "ad_extras": "",
        "gr_tema": "",
        "gr_idioma": "Português (Brasil)",
        "gr_minutos": 10,
        "gr_tom": "Documentário dark / mistério",
        "gr_publico": "",
        "gr_referencia": "",
        "gr_extras": "",
        "gr_pesquisa": True,
        "skills_ativas": ["roteiro-narrado-retencao", "documentario-dark-edicao-titulos"],
        "idioma": "Português (Brasil)",
        "modo_visual": "IA",                 # (antigo) IA | Banco — hoje vale pct_banco
        "pct_banco": 0,                      # % de cenas com banco de imagens; o resto é IA
        "distribuicao_mix": "Intercalado",   # Intercalado | Aleatório | Blocos
        "img_provider": IMAGE_PROVIDERS[0],
        "img_provider_thumb": IMAGE_PROVIDERS[0],
        "estilo_visual": "3D Cinematográfico",
        "estilo_personalizado": "",
        "personagem_fixo": "",
        "ref_link": "",          # vídeo de referência de edição
        "ref_direcao": "",       # jeito de enquadrar copiado da referência
        "banco_fontes": ["Pexels", "Pixabay"],
        "banco_tipo": "Misto (clipes + fotos)",  # Clipes | Fotos | Misto
        "pasta_midia_local": "",
        "segundos_por_cena": 6,
        "tts_provider": "ElevenLabs",        # ElevenLabs | Fish Audio
        "voz_id": "",
        "voz_nome": "",
        "eleven_model": ELEVEN_MODELS[0],
        "fish_model": FISH_MODELS[0],
        "velocidade_voz": 1.0,
        "legendas": True,
        "estilo_legenda": list(SUBTITLE_STYLES)[0],
        "exportar_srt": True,
        "movimento": "Aleatório",
        "intensidade_movimento": "Média",
        "transicao": "Fade (dissolver)",
        "duracao_transicao": 0.5,
        "template": "Nenhum",
        "template_rotulo": "DOCUMENTÁRIO",
        "template_abertura": True,
        "template_dur_abertura": 4.0,
        "template_encerramento": True,
        "template_fim": "Obrigado por assistir",
        "template_fim_sub": "Inscreva-se no canal e ative o sininho",
        "template_moldura": True,
        "template_cor": True,
        "template_legenda": True,
        "efeitos_sonoros": True,
        "volume_sfx": 0.35,
        "trilha_modo": "Automático",         # Sem música | Automático | Tema | Arquivo ou pasta
        "trilha_tema": "Dramático",
        "musica": "",                        # arquivo ou pasta (modo "Arquivo ou pasta")
        "volume_musica": 0.12,
        "revisao": True,
        "revisao_auto_corrigir": True,
        "revisao_ia_visao": False,
        "thumbnail": True,
        "thumb_texto": "",
        "thumb_prompt": "",
        "pasta_saida": str(Path.home() / "Videos" / "AutoVideo"),
        "revisar_antes": True,
        "resolucao": "1080p (Full HD)",
        "seo": True,
        "seo_idioma": "Automático (mesmo do roteiro)",
        "seo_qtd_hashtags": 5,
        "seo_capitulos": True,
        "seo_texto_fixo": "",
        "seo_checar_api": False,
    }
