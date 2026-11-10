"""Gerador de thumbnail 1280x720 com texto chamativo."""
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\impact.ttf", r"C:\Windows\Fonts\ariblk.ttf", r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


def _font(size):
    for f in FONT_CANDIDATES:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


def _wrap(draw, text, font, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def compose(bg: Path, text: str, out: Path) -> Path:
    im = Image.open(bg).convert("RGB")
    W, H = 1280, 720
    r = max(W / im.width, H / im.height)
    im = im.resize((int(im.width * r) + 1, int(im.height * r) + 1), Image.LANCZOS)
    l, t = (im.width - W) // 2, (im.height - H) // 2
    im = im.crop((l, t, l + W, t + H))
    im = ImageEnhance.Contrast(im).enhance(1.15)
    im = ImageEnhance.Color(im).enhance(1.2)
    text = (text or "").strip().upper()
    if text:
        # gradiente escuro do lado esquerdo para o texto ler bem
        grad = Image.new("L", (W, H))
        gd = ImageDraw.Draw(grad)
        for x in range(W):
            gd.line([(x, 0), (x, H)], fill=int(max(0, 200 * (1 - x / (W * 0.7)))))
        im = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), im, grad)
        d = ImageDraw.Draw(im)
        size = 150
        while size > 50:
            f = _font(size)
            lines = _wrap(d, text, f, W * 0.55)
            if len(lines) <= 3:
                break
            size -= 10
        y = (H - len(lines) * size * 1.05) / 2
        colors = [(255, 255, 255), (255, 214, 0), (255, 255, 255)]
        for i, line in enumerate(lines):
            shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            sd = ImageDraw.Draw(shadow)
            sd.text((60 + 6, y + 6), line, font=f, fill=(0, 0, 0, 200))
            im.paste(shadow.filter(ImageFilter.GaussianBlur(6)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(6)))
            d = ImageDraw.Draw(im)
            d.text((60, y), line, font=f, fill=colors[i % 3], stroke_width=max(4, size // 18), stroke_fill=(0, 0, 0))
            y += size * 1.05
    im.save(out, quality=95)
    return out
