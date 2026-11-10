"""Estilos de vídeo com miniatura de exemplo.

Cada estilo tem:
- prompt:  a "receita" visual que vai em TODAS as imagens geradas (cenas e thumbnail);
- direcao: instrução para a IA que escreve os prompts das cenas, para que o conteúdo
           combine com o estilo (ex.: no Mapa de Busca toda cena vira um mapa);
- foto:    True se o estilo é fotográfico (combina com imagens de banco). Nos estilos
           desenhados, misturar com fotos de banco quebra a identidade do vídeo.
"""
from pathlib import Path

PASTA = Path(__file__).resolve().parent.parent / "assets" / "estilos"

ESTILOS = {
    "Motion Graphics": {
        "slug": "motion_graphics",
        "desc": "Vetor plano, gradientes e brilhos. Ótimo para explicar.",
        "prompt": ("flat vector motion graphics illustration, clean geometric shapes, smooth color gradients, "
                   "layered parallax depth, bold limited palette of deep navy blue, cyan, coral orange and magenta, "
                   "soft glows and light beams, simplified faceless characters, stylized waves and clouds, "
                   "dashed path lines and glowing location markers, modern explainer animation look"),
        "direcao": "Simplify every scene into clear shapes and symbols; use paths, markers and icons to show movement or ideas.",
        "foto": False,
    },
    "3D Cinematográfico": {
        "slug": "3d_cinematografico",
        "desc": "CGI realista, névoa, contraluz dourado. Épico e dramático.",
        "prompt": ("hyper-detailed cinematic 3D render, photoreal CGI, volumetric fog and god rays, dramatic golden-hour "
                   "backlight against cold stormy blue shadows, wet glossy textures, shallow depth of field, "
                   "anamorphic widescreen film look, epic atmosphere, subtle film grain"),
        "direcao": "Use cinematic camera angles (over-the-shoulder, low angle, wide establishing shots) and strong practical light sources.",
        "foto": True,
    },
    "Cartoon 2D": {
        "slug": "cartoon_2d",
        "desc": "Desenho com contorno preto e rostos expressivos.",
        "prompt": ("2D cartoon illustration, thick black outlines, flat cel-shaded colors with soft grain texture, "
                   "expressive exaggerated faces with big eyes, warm muted palette of mustard yellow, burnt orange and "
                   "teal green, painterly simplified backgrounds, modern adult animated series look"),
        "direcao": "Favor character close-ups with clear emotions (fear, surprise, joy) and simple readable backgrounds.",
        "foto": False,
    },
    "Stickman": {
        "slug": "stickman",
        "desc": "Bonequinho de palito a lápis, cinza com um toque laranja.",
        "prompt": ("hand-drawn stick figure sketch, round-headed stickman with simple line limbs and no facial details, "
                   "black charcoal and ink pencil strokes on off-white paper, crosshatched pencil shading, monochrome grey "
                   "with a single vivid orange accent color, rough sketchbook doodle explainer style"),
        "direcao": "Every person must be a simple stickman; keep scenes uncluttered, use orange only for the key element of the scene.",
        "foto": False,
    },
    "Webdoc Investigativo": {
        "slug": "webdoc_investigativo",
        "desc": "Foto antiga presa em mapa, marcações em vermelho. Clima de dossiê.",
        "prompt": ("investigative documentary collage, aged black and white photograph with cracked torn edges pinned with a "
                   "red pushpin onto vintage parchment maps on an old wooden desk, red marker circles and dashed red lines, "
                   "sepia paper textures, brass compass and rope props, detective evidence-board aesthetic, top-down flat lay"),
        "direcao": "Show the scene as an old photograph or document placed on a desk with maps and clues; circle key places in red.",
        "foto": False,
    },
    "Quadrinho Animado": {
        "slug": "quadrinho_animado",
        "desc": "HQ com hachuras, retícula e vermelho forte.",
        "prompt": ("gritty graphic novel comic panel, bold ink linework and heavy crosshatching, halftone dot shading, "
                   "limited palette of deep navy, cream and vivid red-orange, dynamic dramatic angle, textured printed paper "
                   "look, vintage pulp comic art"),
        "direcao": "Compose like a comic panel: dramatic angles, foreground figure seen from behind or in profile, action in the background.",
        "foto": False,
    },
    "Recortes de Papel": {
        "slug": "recortes_de_papel",
        "desc": "Colagem de papel rasgado em camadas. Artesanal.",
        "prompt": ("layered torn paper collage, handmade cut-paper craft art, visible paper fibers and deckled torn edges, "
                   "soft drop shadows between paper layers, muted teal, mustard yellow and terracotta palette, "
                   "tactile craft texture, warm soft lighting"),
        "direcao": "Build each scene from a few large paper layers (sky, land, water, figures); keep shapes simple.",
        "foto": False,
    },
    "Pixel Art": {
        "slug": "pixel_art",
        "desc": "Jogo retrô 16-bit, noite azul-petróleo e luz laranja.",
        "prompt": ("16-bit pixel art, retro video game scene, visible chunky pixels, limited palette of dark teal and warm "
                   "peach orange, dithered gradients, glowing light sources, moody atmospheric night, side-scroller game "
                   "background composition"),
        "direcao": "Compose like a side-view game screen; include one warm glowing light source in every scene.",
        "foto": False,
    },
    "Stop Motion": {
        "slug": "stop_motion",
        "desc": "Massinha (claymation), cenário em miniatura.",
        "prompt": ("claymation stop-motion style, handmade plasticine characters with visible fingerprints and sculpted "
                   "texture, miniature physical set, cartoonish expressive features, warm practical lighting with soft "
                   "haze, tilt-shift macro photography, shallow depth of field"),
        "direcao": "Treat every scene as a handmade miniature set with clay characters showing big readable expressions.",
        "foto": False,
    },
    "Avatar de Culinária": {
        "slug": "avatar_culinaria",
        "desc": "Apresentador(a) fixo(a) numa cozinha aconchegante, foto realista.",
        "prompt": ("warm photorealistic lifestyle photography, friendly presenter cooking in a cozy rustic home kitchen, "
                   "colorful patterned wall tiles, wooden shelves with jars and plants, bright natural window light, "
                   "vibrant warm colors, appetizing food close-ups with rising steam, 50mm lens, shallow depth of field"),
        "direcao": ("The SAME presenter appears in most scenes (use the recurring character description exactly); "
                    "alternate between the presenter talking to camera and close-ups of ingredients and food."),
        "foto": True,
        "personagem": "a cheerful elderly woman with curly grey hair, red-framed glasses, gold hoop earrings, olive green blouse and mustard yellow apron",
    },
    "Diorama Isométrico": {
        "slug": "diorama_isometrico",
        "desc": "Bloco 3D em miniatura com corte do solo e da água.",
        "prompt": ("isometric 3D miniature diorama, cross-section cube block of land and sea floating on a plain cream "
                   "background, visible soil and rock layers on the cut sides, translucent cut-away water, tiny highly "
                   "detailed models, tilt-shift miniature look, soft studio lighting, clean product render"),
        "direcao": "Show each place as a small isometric block seen from above at 45 degrees; people and vehicles are tiny.",
        "foto": False,
    },
    "Gravura Animada": {
        "slug": "gravura_animada",
        "desc": "Xilogravura antiga em sépia, traço fino e hachuras.",
        "prompt": ("antique woodcut engraving illustration, fine ink linework and dense crosshatching, sepia brown ink on "
                   "aged parchment paper, 19th century book illustration, dramatic composition, hand-engraved texture"),
        "direcao": "Compose like an old history book plate: dramatic action, figures in period clothing, detailed waves, skies and textures.",
        "foto": False,
    },
    "Mapa de Relevo 3D": {
        "slug": "mapa_relevo_3d",
        "desc": "Vista aérea de drone/relevo. Ótimo para lugares.",
        "prompt": ("aerial drone photograph with 3D terrain relief, high altitude oblique view, dramatic topography, lush "
                   "green ridges and rugged cliffs, deep blue ocean, crisp sunlight with long shadows, ultra detailed "
                   "landscape, nature documentary style"),
        "direcao": "Show the location of the scene from high above (aerial or orbital view); people are not visible or very small.",
        "foto": True,
    },
    "Mapa de Busca": {
        "slug": "mapa_de_busca",
        "desc": "Satélite com grade, rotas e alvo. Clima de missão.",
        "prompt": ("satellite map view from space, dark blue ocean and green landmasses, thin cyan coordinate grid lines, "
                   "glowing cyan HUD overlay graphics, search pattern routes with arrows, orange target cross marker, "
                   "tactical mission briefing infographic, clean modern data visualization"),
        "direcao": "Every scene is a top-down satellite map of the relevant region with routes, zones and a target marker.",
        "foto": False,
    },
    "Pintura Digital": {
        "slug": "pintura_digital",
        "desc": "Pinceladas digitais largas, céu rosa e roxo. Atmosférico.",
        "prompt": ("painterly digital concept art, broad visible brushstrokes, loose impressionistic strokes, "
                   "dramatic sunset sky in coral red, magenta and deep violet, soft atmospheric haze, warm glowing "
                   "lantern light, simplified silhouettes, moody cinematic matte painting"),
        "direcao": "Compose like a concept-art matte painting: big sky, figure in the foreground often seen from behind, one warm light source.",
        "foto": False,
    },
    "Aquarela": {
        "slug": "aquarela",
        "desc": "Aquarela suave em azul e turquesa, papel texturizado.",
        "prompt": ("delicate watercolor painting on textured cold-press paper, soft wet-on-wet washes and blooms, "
                   "pigment bleeding edges, pale misty background fading to white paper, palette of cerulean blue, "
                   "turquoise and soft indigo with touches of warm ochre, gentle diffused light, calm poetic mood"),
        "direcao": "Keep compositions airy with lots of soft empty space and mist; details only on the main subject.",
        "foto": False,
    },
    "Óleo sobre Tela": {
        "slug": "oleo_sobre_tela",
        "desc": "Óleo com empasto grosso, tempestade azul e luz dourada.",
        "prompt": ("thick impasto oil painting on canvas, heavy palette-knife strokes, visible canvas weave texture, "
                   "dramatic stormy night in deep navy and slate blue, glowing golden lantern and beam light, "
                   "rich chiaroscuro, classical maritime painting mood, expressive textured brushwork"),
        "direcao": "Compose like a classical dramatic painting: strong contrast between dark stormy areas and one golden light source.",
        "foto": False,
    },
}


def miniatura(nome: str):
    e = ESTILOS.get(nome)
    if not e:
        return None
    p = PASTA / f"{e['slug']}.jpg"
    return p if p.exists() else None


def info(nome: str) -> dict:
    return ESTILOS.get(nome, {})


def eh_desenhado(nome: str) -> bool:
    """True para estilos que não combinam com fotos de banco."""
    e = ESTILOS.get(nome)
    return bool(e) and not e.get("foto", False)
