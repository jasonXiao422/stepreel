"""Titles drawn onto rendered frames with Pillow (portable: no ffmpeg font support needed)."""
import glob
import os
import sys

from PIL import Image, ImageDraw, ImageFont

from .config import STYLES

FONT_CANDIDATES = {
    "bold": [
        "C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc", "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    ],
    "regular": [
        "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Light.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    ],
}


def find_font(weight, user):
    if user and user != "auto":
        return user
    for p in FONT_CANDIDATES[weight]:
        if os.path.exists(p):
            return p
    hits = glob.glob("/usr/share/fonts/**/*CJK*", recursive=True)
    if hits:
        return hits[0]
    print("[stepreel] 没找到中文字体，请在配置里设置 font: 字体路径", file=sys.stderr)
    return None


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _alpha(t, a, b, fade=0.4):
    if t < a or t > b:
        return 0.0
    return max(0.0, min(1.0, (t - a) / fade, (b - t) / fade))


def _font(path, size):
    return ImageFont.truetype(path, size) if path else ImageFont.load_default(size)


def draw_titles(img, t, titles, style, font_cfg, accent=None):
    if not titles:
        return img
    W, H = img.size
    u = min(W, H) / 1080  # scale unit
    st = STYLES[style]
    fb, fr = find_font("bold", font_cfg), find_font("regular", font_cfg)
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    margin = int(80 * u)
    stacks = {}
    for ti in titles:
        a = _alpha(t, ti.get("start", 0), ti.get("end", 1e9))
        if a <= 0:
            continue
        kind = ti.get("style", "title")
        pos = ti.get("position", "bottom-left")
        if kind == "stat":
            lines = [(ti["text"], _font(fb, int(110 * u)), st["text"]),
                     (ti.get("caption", ""), _font(fr, int(32 * u)), st["text_dim"])]
        elif kind == "subtitle":
            lines = [(ti["text"], _font(fr, int(28 * u)), accent or st["accent"])]
        elif kind == "caption":
            lines = [(ti["text"], _font(fr, int(30 * u)), st["text_dim"])]
        else:
            lines = [(ti["text"], _font(fb, int(72 * u)), st["text"])]
        for text, font, color in lines:
            if not text:
                continue
            bx = d.textbbox((0, 0), text, font=font)
            tw, th = bx[2] - bx[0], bx[3] - bx[1]
            off = stacks.get(pos, 0)
            if pos.startswith("top"):
                y = margin + off
            elif pos.startswith("bottom"):
                y = None
            else:
                y = (H - th) // 2 + off
            if pos.endswith("left"):
                x = margin
            elif pos.endswith("right"):
                x = W - margin - tw
            else:
                x = (W - tw) // 2
            if y is None:  # bottom: collect then lay out upward later
                stacks.setdefault("_bottom_" + pos, []).append((text, font, color, x, tw, th, bx, a))
                continue
            d.text((x - bx[0], y - bx[1]), text, font=font, fill=(*_rgb(color), int(255 * a)))
            stacks[pos] = off + th + int(18 * u)
    for key, items in stacks.items():
        if not str(key).startswith("_bottom_"):
            continue
        y = H - margin
        for text, font, color, x, tw, th, bx, a in reversed(items):
            y -= th
            d.text((x - bx[0], y - bx[1]), text, font=font, fill=(*_rgb(color), int(255 * a)))
            y -= int(18 * u)
    return Image.alpha_composite(img.convert("RGBA"), layer).convert("RGB")


# ------------------------------------------------------------------ color grade (post, engine independent)
def grade(img, name="neutral", vignette=0.0):
    import numpy as np
    if name == "neutral" and not vignette:
        return img
    a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    luma = (a * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True)

    def sat(x, k):
        l = (x * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True)
        return l + (x - l) * k

    def scurve(x, k):
        return np.clip(0.5 + (x - 0.5) * k - (k - 1) * (x - 0.5) ** 3 * 2, 0, 1)

    if name == "contrast":
        a = sat(scurve(a, 1.25), 1.12)
    elif name == "cool":
        shadows = (1 - luma) ** 2
        a = a + shadows * np.array([-0.035, 0.04, 0.085]) + luma ** 2 * np.array([-0.035, 0.01, 0.06])
        a = sat(scurve(a, 1.1), 0.92)
    elif name == "warm":
        a = a * 0.94 + 0.035                      # lifted blacks, film fade
        a = a + luma ** 1.5 * np.array([0.05, 0.02, -0.04])
        a = sat(a, 0.9)
        rng = np.random.default_rng(int(a.sum() * 1000) % 2**32)
        a = a + rng.normal(0, 0.012, a.shape[:2])[..., None]  # light grain
    elif name == "tealorange":
        shadows = (1 - luma) ** 1.6
        a = a + shadows * np.array([-0.05, 0.03, 0.06]) + luma ** 1.4 * np.array([0.07, 0.025, -0.05])
        a = sat(scurve(a, 1.15), 1.05)
    elif name == "mono":
        l = (a * [0.2126, 0.7152, 0.0722]).sum(-1, keepdims=True)
        a = scurve(np.repeat(l, 3, -1), 1.3)
    if vignette:
        h, w = a.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w]
        r = np.sqrt(((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2) / np.sqrt(2)
        a = a * (1 - vignette * r[..., None] ** 2)
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"))
