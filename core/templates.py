"""Templates visuais do vídeo: abertura com título, encerramento, moldura, tratamento de cor e legenda.
Todos os desenhos são gerados aqui (PIL) em 1920x1080 e aplicados pelo FFmpeg."""
import os
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1920, 1080
WIN = r"C:\Windows\Fonts"
LNX = "/usr/share/fonts/truetype"

FONTES = {  # (arquivos candidatos, nome para a legenda .ass)
    "serif": ([f"{WIN}\\georgiab.ttf", f"{WIN}\\georgia.ttf", f"{LNX}/google-fonts/Lora-Variable.ttf",
               f"{LNX}/dejavu/DejaVuSerif-Bold.ttf"], "Georgia"),
    "serif_it": ([f"{WIN}\\georgiai.ttf", f"{WIN}\\georgiaz.ttf", f"{LNX}/google-fonts/Lora-Italic-Variable.ttf",
                  f"{LNX}/dejavu/DejaVuSerif-Italic.ttf"], "Georgia"),
    "pesada": ([f"{WIN}\\ariblk.ttf", f"{WIN}\\impact.ttf", f"{LNX}/google-fonts/Poppins-Bold.ttf",
                f"{LNX}/dejavu/DejaVuSans-Bold.ttf"], "Arial Black"),
    "impacto": ([f"{WIN}\\impact.ttf", f"{WIN}\\ariblk.ttf", f"{LNX}/google-fonts/Poppins-Bold.ttf",
                 f"{LNX}/dejavu/DejaVuSans-Bold.ttf"], "Impact"),
    "grotesca": ([f"{WIN}\\bahnschrift.ttf", f"{WIN}\\segoeuib.ttf", f"{WIN}\\arialbd.ttf",
                  f"{LNX}/google-fonts/Poppins-Bold.ttf", f"{LNX}/dejavu/DejaVuSans-Bold.ttf"], "Segoe UI"),
    "texto": ([f"{WIN}\\segoeui.ttf", f"{WIN}\\arial.ttf", f"{LNX}/google-fonts/Poppins-Regular.ttf",
               f"{LNX}/dejavu/DejaVuSans.ttf"], "Segoe UI"),
    "mono": ([f"{WIN}\\courbd.ttf", f"{WIN}\\cour.ttf", f"{LNX}/liberation/LiberationMono-Bold.ttf",
              f"{LNX}/dejavu/DejaVuSansMono-Bold.ttf"], "Courier New"),
}


def fonte(tipo, tam):
    for f in FONTES[tipo][0]:
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, tam)
            except Exception:
                continue
    return ImageFont.load_default()


def _ass(rgb, alpha=0):
    r, g, b = rgb
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


# ------------------------------------------------------------------ catálogo
TEMPLATES = {
    "Nenhum": dict(desc="Sem abertura, moldura ou tratamento — só as imagens e a legenda escolhida.", layout=None),
    "Pergaminho Solar": dict(
        desc="Papel creme com brilho amarelo, serifa azul-marinho elegante.", layout="serif_grande",
        bg=(238, 232, 220), tinta=(28, 36, 104), acento=(240, 226, 60), titulo="serif", moldura="papel",
        cor="eq=saturation=0.92:contrast=1.03,colorbalance=rs=.03:bs=-.03",
        legenda=dict(font="serif", primary=(255, 255, 255), outline=(28, 36, 104), box=False)),
    "Neo-Brutal": dict(
        desc="Bordas pretas grossas, sombra dura deslocada, letras enormes.", layout="brutal",
        bg=(255, 251, 239), tinta=(10, 10, 10), acento=(255, 196, 0), titulo="pesada", moldura="brutal", cor="",
        legenda=dict(font="pesada", primary=(10, 10, 10), outline=(255, 251, 239), box=True, boxcor=(255, 196, 0))),
    "Cobalto Executivo": dict(
        desc="Creme sóbrio com um único azul cobalto forte. Profissional.", layout="linha_rotulo",
        bg=(251, 248, 233), tinta=(20, 20, 30), acento=(46, 59, 255), titulo="grotesca", moldura="nenhuma",
        cor="eq=contrast=1.04",
        legenda=dict(font="grotesca", primary=(255, 255, 255), outline=(20, 20, 60), box=True, boxcor=(46, 59, 255))),
    "Pôster Vermelho": dict(
        desc="Pôster de revista: letras gordas pretas e vermelhas no creme.", layout="poster",
        bg=(255, 253, 248), tinta=(20, 16, 14), acento=(214, 20, 20), titulo="pesada", moldura="nenhuma",
        cor="eq=contrast=1.06:saturation=1.05",
        legenda=dict(font="pesada", primary=(255, 255, 255), outline=(214, 20, 20), box=False)),
    "Laranja Industrial": dict(
        desc="Fundo laranja-fogo, tipografia preta maciça, rótulos de máquina.", layout="bloco_cor",
        bg=(232, 98, 42), tinta=(18, 14, 12), acento=(255, 240, 220), titulo="pesada", moldura="nenhuma",
        cor="eq=contrast=1.08:saturation=1.1",
        legenda=dict(font="pesada", primary=(18, 14, 12), outline=(232, 98, 42), box=True, boxcor=(232, 98, 42))),
    "Cápsula Doce": dict(
        desc="Editorial com etiquetas em pílula e paleta doce (rosa, coral, amarelo).", layout="pilula",
        bg=(246, 232, 228), tinta=(24, 18, 18), acento=(236, 98, 80), acento2=(246, 214, 92), titulo="serif",
        moldura="nenhuma", cor="eq=saturation=1.05,colorbalance=rh=.03",
        legenda=dict(font="serif", primary=(255, 255, 255), outline=(236, 98, 80), box=False)),
    "Linha Única": dict(
        desc="Minimalista: muito espaço, serifa grande e uma palavra em itálico.", layout="minimal",
        bg=(236, 232, 225), tinta=(26, 24, 22), acento=(26, 24, 22), titulo="serif", moldura="nenhuma",
        cor="eq=saturation=0.85",
        legenda=dict(font="serif_it", primary=(250, 248, 244), outline=(26, 24, 22), box=False)),
    "Grade Azul": dict(
        desc="Papel quadriculado creme com serifa azul elétrico.", layout="grade",
        bg=(244, 240, 226), tinta=(40, 50, 230), acento=(40, 50, 230), titulo="serif", moldura="nenhuma",
        cor="eq=contrast=1.03",
        legenda=dict(font="serif", primary=(255, 255, 255), outline=(40, 50, 230), box=False)),
    "Dossiê Noir": dict(
        desc="Preto e branco com grão, máquina de escrever e carimbo vermelho. Para crime e máfia.", layout="noir",
        bg=(12, 12, 12), tinta=(236, 232, 222), acento=(200, 24, 24), titulo="mono", moldura="vinheta",
        cor="hue=s=0,eq=contrast=1.15:brightness=-0.02,noise=alls=9:allf=t",
        legenda=dict(font="mono", primary=(240, 236, 228), outline=(0, 0, 0), box=True, boxcor=(0, 0, 0))),
    "Arquivo Sépia": dict(
        desc="Ficha antiga envelhecida em sépia, tarjas de censura. Para história e mistério.", layout="arquivo",
        bg=(214, 196, 160), tinta=(52, 36, 22), acento=(120, 28, 20), titulo="mono", moldura="vinheta",
        cor="colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,eq=contrast=1.05,noise=alls=6:allf=t",
        legenda=dict(font="serif", primary=(245, 232, 205), outline=(52, 36, 22), box=False)),
    "Cinema Épico": dict(
        desc="Faixas pretas de cinema, título dourado centralizado e cor de filme.", layout="cinema",
        bg=(0, 0, 0), tinta=(232, 196, 120), acento=(232, 196, 120), titulo="serif", moldura="letterbox",
        cor="eq=contrast=1.08:saturation=1.08,colorbalance=rs=.05:bs=-.06:rh=.04:bh=-.05",
        legenda=dict(font="serif", primary=(245, 238, 220), outline=(0, 0, 0), box=False)),
}


def _quebrar(d, texto, f, largura):
    linhas, cur = [], ""
    for p in texto.split():
        t = (cur + " " + p).strip()
        if d.textlength(t, font=f) <= largura or not cur:
            cur = t
        else:
            linhas.append(cur)
            cur = p
    if cur:
        linhas.append(cur)
    return linhas


def _ajustar(d, texto, tipo, largura, max_linhas, tam_max, tam_min=40):
    tam = tam_max
    while tam > tam_min:
        f = fonte(tipo, tam)
        ls = _quebrar(d, texto, f, largura)
        if len(ls) <= max_linhas:
            return f, ls, tam
        tam -= 6
    f = fonte(tipo, tam_min)
    return f, _quebrar(d, texto, f, largura)[:max_linhas], tam_min


def _fundo(t):
    im = Image.new("RGBA", (W, H), t["bg"] + (255,))
    return im, ImageDraw.Draw(im)


def desenhar_cartela(nome: str, titulo: str, rotulo: str = "", sub: str = "") -> Image.Image:
    """Cartela 1920x1080 (abertura ou encerramento) no estilo do template."""
    t = TEMPLATES[nome]
    L = t["layout"]
    rot = (rotulo or "").upper()
    if L == "serif_grande":
        im, d = _fundo(t)
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([W * .25, H * .2, W * .85, H * 1.1], fill=t["acento"] + (190,))
        im.alpha_composite(glow.filter(ImageFilter.GaussianBlur(160)))
        d = ImageDraw.Draw(im)
        d.text((150, 300), rot, font=fonte("grotesca", 30), fill=t["tinta"])
        f, ls, tam = _ajustar(d, titulo, "serif", W - 300, 3, 170)
        y = 370
        for i, l in enumerate(ls):
            d.text((150, y), l, font=fonte("serif_it", tam) if i == len(ls) - 1 and len(ls) > 1 else f, fill=t["tinta"])
            y += tam * 1.08
        if sub:
            d.text((150, y + 30), sub, font=fonte("texto", 38), fill=t["tinta"])
    elif L == "brutal":
        im, d = _fundo(t)
        d.rectangle([60, 60, W - 60, H - 60], outline=(10, 10, 10), width=14)
        if rot:
            fr = fonte("mono", 30)
            wr = d.textlength(rot, font=fr)
            d.rectangle([150 + 8, 150 + 8, 150 + wr + 48, 210 + 8], fill=(10, 10, 10))
            d.rectangle([150, 150, 150 + wr + 40, 210], fill=(255, 255, 255), outline=(10, 10, 10), width=5)
            d.text((170, 162), rot, font=fr, fill=(10, 10, 10))
        f, ls, tam = _ajustar(d, titulo.upper(), "pesada", W - 360, 3, 190)
        y = 270
        for l in ls:
            d.text((150 + 10, y + 10), l, font=f, fill=t["acento"])
            d.text((150, y), l, font=f, fill=t["tinta"])
            y += tam * 1.02
        d.polygon([(W - 230, 160), (W - 200, 230), (W - 125, 235), (W - 185, 280), (W - 160, 355), (W - 230, 310),
                   (W - 300, 355), (W - 275, 280), (W - 335, 235), (W - 260, 230)], fill=t["acento"], outline=(10, 10, 10))
        if sub:
            d.text((150, H - 200), sub.upper(), font=fonte("mono", 36), fill=t["tinta"])
    elif L == "linha_rotulo":
        im, d = _fundo(t)
        d.rectangle([150, 330, 260, 338], fill=t["acento"])
        d.text((150, 370), rot, font=fonte("grotesca", 28), fill=(120, 120, 130))
        f, ls, tam = _ajustar(d, titulo, "grotesca", W - 420, 3, 130)
        y = 430
        for l in ls:
            d.text((150, y), l, font=f, fill=t["tinta"])
            y += tam * 1.15
        if sub:
            d.text((150, y + 30), sub, font=fonte("texto", 36), fill=(90, 90, 100))
    elif L == "poster":
        im, d = _fundo(t)
        d.text((150, 120), rot, font=fonte("mono", 28), fill=t["acento"])
        f, ls, tam = _ajustar(d, titulo, "pesada", W - 300, 3, 210)
        y = 220
        for i, l in enumerate(ls):
            d.text((150, y), l, font=f, fill=t["acento"] if i % 2 else t["tinta"])
            y += tam * 1.05
        if sub:
            d.text((150, H - 170), sub, font=fonte("serif_it", 44), fill=t["tinta"])
    elif L == "bloco_cor":
        im, d = _fundo(t)
        d.text((150, 120), "No. 01", font=fonte("mono", 30), fill=t["tinta"])
        d.rectangle([150, 470, 230, 476], fill=t["tinta"])
        d.text((150, 500), rot, font=fonte("mono", 28), fill=t["tinta"])
        f, ls, tam = _ajustar(d, titulo.lower() + ".", "pesada", W - 300, 3, 200)
        y = 560
        for l in ls:
            d.text((150, y), l, font=f, fill=t["tinta"])
            y += tam * 0.98
        if sub:
            d.text((150, H - 110), sub, font=fonte("texto", 34), fill=t["tinta"])
    elif L == "pilula":
        im = Image.new("RGBA", (W, H))
        g = ImageDraw.Draw(im)
        for x in range(W):
            k = x / W
            g.line([(x, 0), (x, H)], fill=(int(246 - 6 * k), int(232 + 6 * k), int(228 + 10 * k), 255))
        d = ImageDraw.Draw(im)
        fp = fonte("grotesca", 30)
        if rot:
            wr = d.textlength(rot, font=fp)
            d.rounded_rectangle([W - 260 - wr, 200, W - 200, 262], radius=31, fill=t["acento2"], outline=t["tinta"], width=3)
            d.text((W - 230 - wr, 212), rot, font=fp, fill=t["tinta"])
        d.rounded_rectangle([150, 180, 400, 236], radius=28, fill=t["acento"], outline=t["tinta"], width=3)
        d.text((178, 190), "EDITORIAL", font=fonte("grotesca", 28), fill=(255, 255, 255))
        f, ls, tam = _ajustar(d, titulo, "serif", W - 300, 3, 180)
        y = 340
        for i, l in enumerate(ls):
            ff = fonte("serif_it", tam) if i == len(ls) - 1 and len(ls) > 1 else f
            d.text((150, y), l, font=ff, fill=t["acento"] if i == len(ls) - 1 and len(ls) > 1 else t["tinta"])
            y += tam * 1.08
        d.ellipse([150, H - 190, 230, H - 110], fill=(246, 190, 160), outline=t["tinta"], width=3)
        if sub:
            d.text((260, H - 172), sub, font=fonte("texto", 36), fill=t["tinta"])
    elif L == "minimal":
        im, d = _fundo(t)
        d.line([(110, 0), (110, H)], fill=(205, 200, 192), width=2)
        d.text((180, 260), rot, font=fonte("grotesca", 26), fill=(130, 125, 118))
        palavras = titulo.split()
        f, ls, tam = _ajustar(d, titulo, "serif", W - 520, 3, 160)
        y = 330
        for i, l in enumerate(ls):
            if i == len(ls) - 1 and len(palavras) > 1:
                ps = l.split()
                inicio = " ".join(ps[:-1])
                d.text((180, y), inicio, font=f, fill=t["tinta"])
                x = 180 + (d.textlength(inicio + " ", font=f) if inicio else 0)
                d.text((x, y), ps[-1], font=fonte("serif_it", tam), fill=t["tinta"])
            else:
                d.text((180, y), l, font=f, fill=t["tinta"])
            y += tam * 1.08
        d.arc([W - 520, H - 760, W + 320, H + 80], 150, 250, fill=(205, 200, 192), width=2)
        if sub:
            d.text((180, y + 30), sub, font=fonte("serif_it", 40), fill=(90, 86, 80))
    elif L == "grade":
        im, d = _fundo(t)
        for x in range(0, W, 48):
            d.line([(x, 0), (x, H)], fill=(222, 218, 214), width=1)
        for y_ in range(0, H, 48):
            d.line([(0, y_), (W, y_)], fill=(222, 218, 214), width=1)
        d.line([(150, 60), (W - 60, 60)], fill=t["tinta"], width=3)
        d.text((150, 90), "GRADE / " + (rot or "DOCUMENTÁRIO"), font=fonte("mono", 26), fill=t["tinta"])
        d.text((150, 440), rot or "", font=fonte("grotesca", 26), fill=(200, 40, 60))
        f, ls, tam = _ajustar(d, titulo, "serif", W - 300, 3, 170)
        y = 490
        for l in ls:
            d.text((150, y), l, font=f, fill=t["tinta"])
            y += tam * 1.0
        if sub:
            d.text((150, y + 20), sub, font=fonte("serif_it", 42), fill=t["tinta"])
    elif L == "noir":
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, H], fill=(0, 0, 0, 175))
        d.text((150, 300), rot or "ARQUIVO", font=fonte("mono", 34), fill=(180, 176, 168))
        f, ls, tam = _ajustar(d, titulo.upper(), "mono", W - 300, 3, 110)
        y = 380
        for l in ls:
            d.text((150, y), l, font=f, fill=t["tinta"])
            y += tam * 1.2
        selo = Image.new("RGBA", (620, 170), (0, 0, 0, 0))
        sd = ImageDraw.Draw(selo)
        sd.rectangle([6, 6, 614, 164], outline=t["acento"] + (230,), width=10)
        sd.text((40, 38), "CONFIDENCIAL", font=fonte("mono", 78), fill=t["acento"] + (230,))
        im.alpha_composite(selo.rotate(-8, expand=True, resample=Image.BICUBIC), (W - 820, H - 360))
        if sub:
            d.text((150, y + 40), sub, font=fonte("mono", 38), fill=(200, 196, 188))
    elif L == "arquivo":
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, H], fill=(30, 20, 10, 120))
        ficha = Image.new("RGBA", (1400, 720), t["bg"] + (255,))
        fd = ImageDraw.Draw(ficha)
        rnd = random.Random(7)
        for _ in range(9000):
            x, y_ = rnd.randrange(1400), rnd.randrange(720)
            c = rnd.randrange(-25, 10)
            fd.point((x, y_), fill=(t["bg"][0] + c, t["bg"][1] + c, t["bg"][2] + c, 255))
        fd.rectangle([20, 20, 1380, 700], outline=t["tinta"], width=3)
        fd.text((70, 60), "FICHA Nº 0137 — " + (rot or "ARQUIVO HISTÓRICO"), font=fonte("mono", 32), fill=t["tinta"])
        fd.rectangle([70, 120, 1330, 124], fill=t["tinta"])
        f, ls, tam = _ajustar(fd, titulo.upper(), "mono", 1240, 3, 92)
        yy = 170
        for l in ls:
            fd.text((70, yy), l, font=f, fill=t["tinta"])
            yy += tam * 1.25
        for i in range(3):
            fd.rectangle([70, 540 + i * 34, 70 + rnd.randrange(450, 900), 562 + i * 34], fill=(20, 14, 8))
        fd.text((1060, 600), "SECRETO", font=fonte("mono", 52), fill=t["acento"])
        ficha = ficha.rotate(-1.5, expand=True, resample=Image.BICUBIC)
        sh = Image.new("RGBA", ficha.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle([20, 20, ficha.size[0] - 10, ficha.size[1] - 10], fill=(0, 0, 0, 140))
        im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(18)), (250, 190))
        im.alpha_composite(ficha, (250, 170))
        if sub:
            d = ImageDraw.Draw(im)
            d.text((260, H - 110), sub, font=fonte("serif_it", 40), fill=(245, 232, 205))
    elif L == "cinema":
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, H], fill=(0, 0, 0, 120))
        f, ls, tam = _ajustar(d, titulo.upper(), "serif", W - 400, 2, 120)
        tot = len(ls) * tam * 1.15
        y = (H - tot) / 2 - 20
        if rot:
            fr = fonte("grotesca", 30)
            d.text(((W - d.textlength(rot, font=fr)) / 2, y - 80), rot, font=fr, fill=(200, 190, 170))
        for l in ls:
            x = (W - d.textlength(l, font=f)) / 2
            d.text((x + 3, y + 4), l, font=f, fill=(0, 0, 0, 200))
            d.text((x, y), l, font=f, fill=t["tinta"])
            y += tam * 1.15
        d.line([(W / 2 - 160, y + 30), (W / 2 + 160, y + 30)], fill=t["acento"], width=2)
        if sub:
            fs = fonte("serif_it", 40)
            d.text(((W - d.textlength(sub, font=fs)) / 2, y + 60), sub, font=fs, fill=(230, 222, 205))
    else:
        return None
    return im


def desenhar_moldura(nome: str):
    """Camada fixa sobre o vídeo inteiro (ou None)."""
    t = TEMPLATES[nome]
    m = t.get("moldura", "nenhuma")
    if m in (None, "nenhuma"):
        return None
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if m == "vinheta":
        v = Image.new("L", (W, H), 0)
        ImageDraw.Draw(v).ellipse([W * .02, -H * .08, W * .98, H * 1.08], fill=255)
        v = v.filter(ImageFilter.GaussianBlur(180))
        a = Image.eval(v, lambda p: int((255 - p) * 0.85))
        im = Image.new("RGBA", (W, H), (0, 0, 0, 255))
        im.putalpha(a)
    elif m == "papel":
        v = Image.new("L", (W, H), 0)
        ImageDraw.Draw(v).rounded_rectangle([40, 40, W - 40, H - 40], radius=40, fill=255)
        v = v.filter(ImageFilter.GaussianBlur(40))
        a = Image.eval(v, lambda p: int((255 - p) * 0.85))
        im = Image.new("RGBA", (W, H), t["bg"] + (255,))
        im.putalpha(a)
    elif m == "brutal":
        d.rectangle([0, 0, W - 1, H - 1], outline=(10, 10, 10, 255), width=22)
        d.rectangle([22, 22, W - 23, H - 23], outline=t["acento"] + (255,), width=6)
    elif m == "letterbox":
        barra = int((H - W / 2.39) / 2)
        d.rectangle([0, 0, W, barra], fill=(0, 0, 0, 255))
        d.rectangle([0, H - barra, W, H], fill=(0, 0, 0, 255))
    return im


def legenda_override(nome: str) -> dict:
    """Ajustes do estilo de legenda (.ass) para combinar com o template."""
    t = TEMPLATES.get(nome, {})
    lg = t.get("legenda")
    if not lg:
        return {}
    o = {"font": FONTES[lg["font"]][1], "primary": _ass(lg["primary"]), "outline_c": _ass(lg["outline"])}
    if lg.get("box"):
        o.update(border_style=3, back=_ass(lg.get("boxcor", (0, 0, 0)), 0x30), outline_c=_ass(lg.get("boxcor", (0, 0, 0)), 0x30),
                 outline=10, shadow=0)
    if t.get("moldura") == "letterbox":
        o["margin_v"] = int((H - W / 2.39) / 2) + 30
    return o


def preparar(nome: str, pasta: Path, titulo: str, rotulo: str, fim_titulo: str, fim_sub: str) -> dict:
    """Gera os PNGs do template para um vídeo. Retorna caminhos e filtro de cor."""
    pasta = Path(pasta)
    t = TEMPLATES.get(nome)
    if not t or not t.get("layout"):
        return {}
    out = {"cor": t.get("cor", "")}
    ab = desenhar_cartela(nome, titulo, rotulo)
    if ab:
        ab.save(pasta / "tpl_abertura.png")
        out["abertura"] = pasta / "tpl_abertura.png"
    fe = desenhar_cartela(nome, fim_titulo or "Obrigado por assistir", rotulo, fim_sub)
    if fe:
        fe.save(pasta / "tpl_encerramento.png")
        out["encerramento"] = pasta / "tpl_encerramento.png"
    mo = desenhar_moldura(nome)
    if mo:
        mo.save(pasta / "tpl_moldura.png")
        out["moldura"] = pasta / "tpl_moldura.png"
    return out


def previa(nome: str, pasta: Path, titulo="O Último Chefão de Palermo", rotulo="DOCUMENTÁRIO · EP. 01") -> Path:
    """Miniatura 640x360 para a galeria (fica em cache)."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    import hashlib
    arq = pasta / f"tpl_{hashlib.md5((nome + titulo + rotulo).encode()).hexdigest()[:10]}.png"
    if arq.exists():
        return arq
    t = TEMPLATES[nome]
    base = Image.new("RGBA", (W, H))
    g = ImageDraw.Draw(base)  # "cena" de exemplo atrás das cartelas transparentes
    for y in range(H):
        k = y / H
        g.line([(0, y), (W, y)], fill=(int(70 - 40 * k), int(56 - 30 * k), int(44 - 20 * k), 255))
    g.ellipse([W * .45, H * .15, W * .95, H * .9], fill=(150, 98, 60, 255))
    base = base.filter(ImageFilter.GaussianBlur(60))
    if t.get("layout"):
        mo = desenhar_moldura(nome)
        if mo:
            base.alpha_composite(mo)
        base.alpha_composite(desenhar_cartela(nome, titulo, rotulo))
    else:
        d = ImageDraw.Draw(base)
        f = fonte("texto", 70)
        d.text((W / 2 - d.textlength("Sem template", font=f) / 2, H / 2 - 40), "Sem template", font=f, fill=(230, 230, 230))
    base.convert("RGB").resize((640, 360), Image.LANCZOS).save(arq)
    return arq
