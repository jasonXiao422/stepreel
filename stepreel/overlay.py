"""Titles drawn onto rendered frames with Pillow (portable: no ffmpeg font support needed).

Typography is driven by the `text` config block: a style template (layout, fonts, decoration),
color, size, position, entrance animation and a soft shadow for readability.
"""
import glob
import math
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .config import STYLES

FONT_CANDIDATES = {
    "black": [
        "C:/Windows/Fonts/msyhbd.ttc", "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc", "/usr/share/fonts/noto-cjk/NotoSansCJK-Black.ttc",
    ],
    "bold": [
        "C:/Windows/Fonts/msyhbd.ttc", "C:/Windows/Fonts/simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Medium.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc", "/usr/share/fonts/noto-cjk/NotoSansCJK-Bold.ttc",
    ],
    "regular": [
        "C:/Windows/Fonts/msyh.ttc", "C:/Windows/Fonts/simhei.ttf",
        "/System/Library/Fonts/PingFang.ttc", "/System/Library/Fonts/STHeiti Light.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc", "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
    ],
    "light": [
        "C:/Windows/Fonts/msyhl.ttc", "/System/Library/Fonts/PingFang.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Light.ttc", "/usr/share/fonts/noto-cjk/NotoSansCJK-Light.ttc",
    ],
    "serif": [
        "C:/Windows/Fonts/simsunb.ttf", "C:/Windows/Fonts/STSONG.TTF", "C:/Windows/Fonts/simsun.ttc",
        "/System/Library/Fonts/Supplemental/Songti.ttc", "/System/Library/Fonts/Songti.ttc",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", "/usr/share/fonts/noto-cjk/NotoSerifCJK-Bold.ttc",
    ],
    "mono": [  # Latin-only; CJK text falls back to regular automatically
        "C:/Windows/Fonts/bahnschrift.ttf", "C:/Windows/Fonts/consola.ttf",
        "/System/Library/Fonts/SFNSMono.ttf", "/System/Library/Fonts/Menlo.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ],
}
FALLBACK = {"black": "bold", "light": "regular", "serif": "regular", "mono": "regular", "bold": "regular"}
_FONT_PATHS, _FONTS = {}, {}


def find_font(weight, user=None):
    if user and user != "auto":
        return user
    if weight in _FONT_PATHS:
        return _FONT_PATHS[weight]
    path = next((p for p in FONT_CANDIDATES.get(weight, []) if os.path.exists(p)), None)
    if path is None and weight in FALLBACK:
        path = find_font(FALLBACK[weight])
    if path is None:
        hits = glob.glob("/usr/share/fonts/**/*CJK*", recursive=True)
        path = hits[0] if hits else None
        if path is None:
            print("[stepreel] 没找到中文字体，请在配置里设置 font: 字体路径", file=sys.stderr)
    _FONT_PATHS[weight] = path
    return path


def _font(path, size):
    size = max(6, int(size))
    key = (path, size)
    if key not in _FONTS:
        _FONTS[key] = ImageFont.truetype(path, size) if path else ImageFont.load_default(size)
    return _FONTS[key]


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _lum(h):
    r, g, b = _rgb(h)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


_CJK = re.compile(r"[\u3000-\u9fff\uac00-\ud7af\uff00-\uffef]")


# ------------------------------------------------------------------ text styles
# Sizes are in units of 1/1080 of the short frame edge. track = extra letter spacing in em.
TEXT_STYLES = {
    "classic": {
        "name": "经典", "desc": "粗标题加彩色副标题，稳妥通用",
        "pos": "bottom-left", "anim": "rise",
        "title": ("bold", 72, 0.0), "sub": ("bold", 36, 0.04), "stat": ("bold", 88, 0.0),
        "cap": ("regular", 38, 0.02), "end": ("regular", 34, 0.04),
    },
    "minimal": {
        "name": "极简细字", "desc": "细字体加宽字距，居中，留白多，高级感",
        "pos": "bottom", "anim": "fade", "upper_sub": True,
        "title": ("light", 64, 0.08), "sub": ("regular", 30, 0.32), "stat": ("light", 80, 0.04),
        "cap": ("regular", 30, 0.26), "end": ("regular", 30, 0.26),
    },
    "impact": {
        "name": "粗体冲击", "desc": "超粗大字配主色色块，短视频抢眼",
        "pos": "bottom-left", "anim": "expand", "bar": True, "tag": True, "upper_title": True,
        "title": ("black", 100, -0.01), "sub": ("bold", 38, 0.06), "stat": ("black", 120, -0.02),
        "cap": ("bold", 42, 0.02), "end": ("bold", 38, 0.04), "stat_accent": True,
    },
    "tech": {
        "name": "科技标注", "desc": "等宽字体、括号和刻度线，像工程标注",
        "pos": "bottom-left", "anim": "type", "brackets": True, "ruler": True, "upper_sub": True,
        "title": ("mono", 68, 0.02), "sub": ("mono", 32, 0.1), "stat": ("mono", 88, 0.0),
        "cap": ("mono", 32, 0.08), "end": ("mono", 30, 0.1),
    },
    "editorial": {
        "name": "杂志衬线", "desc": "衬线大标题加细分隔线，像杂志封面",
        "pos": "bottom-left", "anim": "rise", "rule": True, "upper_sub": True,
        "title": ("serif", 84, 0.0), "sub": ("regular", 32, 0.22), "stat": ("serif", 96, 0.0),
        "cap": ("regular", 34, 0.14), "end": ("serif", 36, 0.04),
    },
    "cinema": {
        "name": "电影字幕", "desc": "上下黑边加居中字幕，电影预告片气质",
        "pos": "bottom", "anim": "fade", "letterbox": 0.13, "upper_title": True, "in_bars": True,
        "title": ("bold", 50, 0.22), "sub": ("regular", 28, 0.3), "stat": ("bold", 50, 0.06),
        "cap": ("regular", 28, 0.24), "end": ("regular", 30, 0.28),
    },
}
# Ready-made copy for the example lift arm. Facts only (part count, gear ratio, materials), no invented specs.
TEXT_SAMPLES = {
    "launch_cn": {"label": "中文发布", "name": "壁面起降臂 V2", "sub": "碳纤维连杆 · 一级齿轮减速",
                  "stat": "165", "statcap": "个零件", "end": "SolidWorks 建模 · 代码渲染"},
    "launch_en": {"label": "English", "name": "Lift Arm V2", "sub": "Carbon Fiber Linkage System",
                  "stat": "165", "statcap": "Parts in one assembly", "end": "Designed in SolidWorks"},
    "spec_cn": {"label": "参数介绍", "name": "一级减速机械臂", "sub": "总线舵机驱动 · 自润滑轴套",
                "stat": "12:72", "statcap": "齿轮减速比", "end": "38 种零件 · 3D 打印 + 碳纤维"},
    "spec_en": {"label": "Specs", "name": "ARM-02", "sub": "Gear-reduced lift mechanism",
                "stat": "1:6", "statcap": "Reduction ratio", "end": "Carbon fiber · Nylon · Steel"},
    "minimal": {"label": "极简", "name": "起降臂", "sub": "LIFT ARM",
                "stat": "", "statcap": "", "end": "2026"},
    "teaser": {"label": "预告片", "name": "Coming Soon", "sub": "A new way to lift",
               "stat": "", "statcap": "", "end": "Stay tuned"},
}
STYLE_SAMPLE = {"classic": "launch_cn", "minimal": "minimal", "impact": "spec_cn",
                "tech": "spec_en", "editorial": "launch_en", "cinema": "teaser"}
TEXT_POSITIONS = {"auto": "跟随样式", "bottom-left": "左下", "bottom": "底部居中", "center": "正中", "top-left": "左上"}
TEXT_ANIMS = {"auto": "跟随样式", "fade": "淡入", "rise": "上滑", "type": "打字机", "expand": "展开"}
TEXT_COLORS = {"auto": "自动", "white": "白色", "black": "黑色", "accent": "主色"}
TEXT_BACKDROPS = {"shadow": "阴影", "plate": "半透明底板", "none": "无"}
TEXT_DEFAULTS = {"enabled": True, "style": "classic", "color": "auto", "size": 1.0, "position": "auto",
                 "animation": "auto", "backdrop": "shadow", "clean_copy": False}


def _palette(style, text_cfg, accent):
    st = STYLES[style]
    accent = accent or st["accent"]
    c = (text_cfg.get("color") or "auto").lower()
    if c == "white":
        main, dim = "#FFFFFF", "#D9DBDF"
    elif c == "black":
        main, dim = "#111317", "#3D424B"
    elif c == "accent":
        main, dim = accent, st["text_dim"]
    elif c.startswith("#") and len(c) == 7:
        main, dim = c, st["text_dim"]
    else:
        main, dim = st["text"], st["text_dim"]
    sub = accent if _lum(accent) > 40 or _lum(main) < 128 else dim
    if c == "accent":
        sub = st["text"]
    return {"main": main, "dim": dim, "sub": sub, "accent": accent}


def _ease(x):
    x = min(1.0, max(0.0, x))
    return 1 - (1 - x) ** 3


class _Line:
    def __init__(self, text, role, spec, color, u, size_mult, upper=False):
        weight, size, track = spec
        if upper:
            text = text.upper()
        if weight == "mono" and _CJK.search(text):
            weight = "regular"
        self.text, self.role, self.color = text, role, color
        self.font = _font(find_font(weight), size * u * size_mult)
        self.track_em = track
        self.size = self.font.size
        asc, desc = self.font.getmetrics()
        self.asc, self.h = asc, asc + desc

    def width(self, chars=None, extra=0.0):
        t = self.text if chars is None else self.text[:chars]
        tr = (self.track_em + extra) * self.size
        if not t:
            return 0
        if abs(tr) < 0.01:
            return self.font.getlength(t)
        return sum(self.font.getlength(ch) for ch in t) + tr * (len(t) - 1)

    def draw(self, d, x, y, alpha, chars=None, extra=0.0):
        t = self.text if chars is None else self.text[:chars]
        fill = (*_rgb(self.color), int(255 * alpha))
        tr = (self.track_em + extra) * self.size
        if abs(tr) < 0.01:
            d.text((x, y + self.asc), t, font=self.font, fill=fill, anchor="ls")
            return
        for ch in t:
            d.text((x, y + self.asc), ch, font=self.font, fill=fill, anchor="ls")
            x += self.font.getlength(ch) + tr


def _anim_state(t, start, end, kind, n_chars):
    """alpha, y offset factor (0..1), visible chars, extra tracking em."""
    if t < start or t > end:
        return None
    dur = 0.55
    if kind == "type":
        dur = min(0.7, max(0.3, 0.03 * n_chars))
    p = (t - start) / dur
    out = min(1.0, (end - t) / 0.35)
    a = min(_ease(p), out)
    if a <= 0:
        return None
    if kind == "rise":
        return a, 1 - _ease(p), None, 0.0
    if kind == "type":
        return min(1.0, out, 0.4 + 2 * p), 0.0, max(1, math.ceil(n_chars * min(1.0, p))), 0.0
    if kind == "expand":
        return a, 0.0, None, 0.45 * (1 - _ease(p))
    return a, 0.0, None, 0.0


def letterbox_height(text_cfg, H, t):
    st = TEXT_STYLES.get((text_cfg or {}).get("style", "classic"), {})
    if not (text_cfg or {}).get("enabled", True) or not st.get("letterbox"):
        return 0
    frac = st["letterbox"] * max(1.0, float((text_cfg or {}).get("size", 1.0) or 1.0))
    return int(H * frac * _ease(t / 0.8))


def draw_titles(img, t, titles, style, font_cfg=None, accent=None, text_cfg=None):
    text_cfg = {**TEXT_DEFAULTS, **(text_cfg or {})}
    if not text_cfg.get("enabled", True):
        return img
    if font_cfg and font_cfg != "auto":
        for k in FONT_CANDIDATES:
            _FONT_PATHS[k] = font_cfg
    ts = TEXT_STYLES.get(text_cfg.get("style", "classic"), TEXT_STYLES["classic"])
    W, H = img.size
    u = min(W, H) / 1080
    mult = float(text_cfg.get("size", 1.0) or 1.0)
    pal = _palette(style, text_cfg, accent)
    base = img.convert("RGBA")
    bars = letterbox_height(text_cfg, H, t)
    if bars:
        bd = ImageDraw.Draw(base)
        bd.rectangle([0, 0, W, bars], fill=(0, 0, 0, 255))
        bd.rectangle([0, H - bars, W, H], fill=(0, 0, 0, 255))
    if not titles:
        return base.convert("RGB")
    anim = text_cfg.get("animation", "auto")
    anim = ts["anim"] if anim in (None, "auto") else anim
    pos_cfg = text_cfg.get("position", "auto")
    title_pos = ts["pos"] if pos_cfg in (None, "auto") else pos_cfg
    margin = int(84 * u)
    top_m, bot_m = margin + bars, margin + bars

    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    deco = Image.new("RGBA", base.size, (0, 0, 0, 0))
    d, dd = ImageDraw.Draw(layer), ImageDraw.Draw(deco)
    plates = []

    groups = {"title": [], "stat": [], "end": []}
    for ti in titles:
        kind = ti.get("style", "title")
        if kind == "stat":
            groups["stat"].append((ti, [
                _Line(str(ti.get("text", "")), "stat", ts["stat"], pal["accent"] if ts.get("stat_accent") else pal["main"], u, mult),
                _Line(str(ti.get("caption", "")), "cap", ts["cap"], pal["dim"], u, mult, ts.get("upper_sub"))]))
        elif kind == "subtitle":
            groups["title"].append((ti, [_Line(str(ti["text"]), "sub", ts["sub"], pal["sub"], u, mult, ts.get("upper_sub"))]))
        elif kind == "caption":
            groups["end"].append((ti, [_Line(str(ti["text"]), "end", ts["end"], pal["dim"], u, mult)]))
        else:
            groups["title"].append((ti, [_Line(str(ti["text"]), "title", ts["title"], pal["main"], u, mult, ts.get("upper_title"))]))

    stat_pos = "top-right" if title_pos == "top-left" else "top-left"
    if title_pos == "center":
        stat_pos = "top-left"
    if ts.get("in_bars"):
        stat_pos = "top"
    places = {"title": title_pos, "stat": stat_pos, "end": "bottom" if title_pos != "bottom" or not groups["title"] else "bottom"}

    gap = int(14 * u * mult)
    for gname, items in groups.items():
        rows = [(ti, ln) for ti, lines in items for ln in lines if ln.text]
        if not rows:
            continue
        pos = places[gname]
        if gname == "end" and title_pos == "bottom":
            pos = "bottom"
        # extra room for decorations
        rule_h = int(22 * u * mult) if ts.get("rule") and gname == "title" and len(rows) > 1 else 0
        ruler_h = int(16 * u * mult) if ts.get("ruler") and gname == "title" else 0
        tag_pad = int(8 * u * mult) if ts.get("tag") else 0
        heights = [ln.h + (2 * tag_pad if ln.role == "sub" else 0) for _, ln in rows]
        total = sum(heights) + gap * (len(rows) - 1) + rule_h + ruler_h
        widths = [ln.width() for _, ln in rows]
        maxw = max(widths)
        if ts.get("in_bars") and bars and pos != "center":
            full = int(H * ts["letterbox"] * max(1.0, mult))
            y = (full - total) // 2 if pos.startswith("top") else H - full + (full - total) // 2
        elif pos.startswith("top"):
            y = top_m
        elif pos == "center":
            y = (H - total) // 2
        else:
            y = H - bot_m - total
        bar_w = int(10 * u * mult) if ts.get("bar") and gname == "title" else 0
        if pos.endswith("left"):
            x0 = margin + (bar_w + int(18 * u) if bar_w else 0)
        elif pos == "top":
            x0 = None
        elif pos.endswith("right"):
            x0 = W - margin - maxw
        else:
            x0 = None  # centered per line
        group_alpha = 0.0
        ytop = y
        gx0, gx1 = W, 0
        for idx, ((ti, ln), hgt) in enumerate(zip(rows, heights)):
            stt = _anim_state(t, ti.get("start", 0), ti.get("end", 1e9), anim, len(ln.text))
            if idx > 0 and rows[idx - 1][1].role == "title" and rule_h:
                if stt:
                    ry = y - gap + rule_h // 2
                    rw = int(120 * u * mult * _ease(stt[0]))
                    rx = x0 if x0 is not None else (W - rw) // 2
                    dd.rectangle([rx, ry, rx + rw, ry + max(1, int(2 * u))], fill=(*_rgb(pal["accent"]), int(255 * stt[0])))
                y += rule_h
            if stt:
                a, dy, chars, extra = stt
                group_alpha = max(group_alpha, a)
                w = ln.width(chars, extra)
                lx = x0 if x0 is not None else (W - ln.width(None, extra)) / 2
                if pos.endswith("right"):
                    lx = W - margin - ln.width()
                ly = y + dy * 30 * u
                gx0, gx1 = min(gx0, lx), max(gx1, lx + ln.width(None, extra))
                if ln.role == "sub" and ts.get("tag"):
                    dd.rectangle([lx - tag_pad, ly, lx + w + tag_pad, ly + hgt], fill=(*_rgb(pal["accent"]), int(235 * a)))
                    ln.color = "#FFFFFF" if _lum(pal["accent"]) < 170 else "#111317"
                    ln.draw(d, lx, ly + tag_pad, a, chars, extra)
                elif ln.role in ("sub", "cap", "end") and ts.get("brackets"):
                    bw = ln.font.getlength("[ ")
                    ln.draw(d, lx, ly, a, chars, extra)
                    fill = (*_rgb(pal["accent"]), int(255 * a))
                    d.text((lx - bw, ly + ln.asc), "[", font=ln.font, fill=fill, anchor="ls")
                    d.text((lx + w + bw * 0.35, ly + ln.asc), "]", font=ln.font, fill=fill, anchor="ls")
                else:
                    ln.draw(d, lx, ly, a, chars, extra)
            y += hgt + gap
        if group_alpha > 0:
            plates.append((gx0, ytop, gx1, y - gap, group_alpha))
        if group_alpha > 0 and bar_w:
            bh = int((y - gap - ytop) * _ease(group_alpha))
            dd.rectangle([margin, ytop, margin + bar_w, ytop + bh], fill=(*_rgb(pal["accent"]), int(255 * group_alpha)))
        if group_alpha > 0 and ruler_h and gname == "title":
            ry = y - gap + ruler_h // 2
            rx = x0 if x0 is not None else (W - maxw) // 2
            rw = int(maxw * _ease(group_alpha))
            fill = (*_rgb(pal["dim"]), int(200 * group_alpha))
            dd.line([rx, ry, rx + rw, ry], fill=fill, width=max(1, int(1.5 * u)))
            step = max(6, int(24 * u))
            for k, tx in enumerate(range(int(rx), int(rx + rw), step)):
                th = int((9 if k % 5 == 0 else 4) * u)
                dd.line([tx, ry, tx, ry - th], fill=fill, width=max(1, int(1.2 * u)))
        if group_alpha > 0 and ts.get("brackets") and gname == "stat":
            # corner brackets around the stat block
            bx0, by0 = x0 - int(16 * u), ytop - int(12 * u)
            bx1, by1 = x0 + maxw + int(16 * u), y - gap + int(10 * u)
            L = int(22 * u)
            fill = (*_rgb(pal["accent"]), int(255 * group_alpha))
            wdt = max(1, int(2 * u))
            for (cx, cy, sx, sy) in ((bx0, by0, 1, 1), (bx1, by0, -1, 1), (bx0, by1, 1, -1), (bx1, by1, -1, -1)):
                dd.line([cx, cy, cx + sx * L, cy], fill=fill, width=wdt)
                dd.line([cx, cy, cx, cy + sy * L], fill=fill, width=wdt)

    backdrop = text_cfg.get("backdrop") or ("shadow" if text_cfg.get("shadow", True) else "none")
    if backdrop == "plate" and plates:
        dark_text = _lum(pal["main"]) < 110
        pl = Image.new("RGBA", base.size, (0, 0, 0, 0))
        pd = ImageDraw.Draw(pl)
        pad = int(22 * u)
        col = (255, 255, 255) if dark_text else (8, 10, 14)
        for x0_, y0_, x1_, y1_, ga in plates:
            pd.rounded_rectangle([x0_ - pad, y0_ - pad, x1_ + pad, y1_ + pad], radius=int(6 * u),
                                 fill=(*col, int(150 * ga)))
        base.alpha_composite(pl)
    if backdrop == "shadow":
        alpha = Image.alpha_composite(deco, layer).getchannel("A")
        dark_text = _lum(pal["main"]) < 110
        strength = 0.35 if dark_text else 0.8
        sh = alpha.point(lambda v: int(v * strength)).filter(ImageFilter.GaussianBlur(max(1, 4.5 * u)))
        shadow_rgb = (255, 255, 255) if dark_text else (0, 0, 0)
        shadow = Image.new("RGBA", base.size, (*shadow_rgb, 0))
        shadow.putalpha(sh)
        off = max(1, int(2 * u))
        base.alpha_composite(shadow, (off, off))
    base.alpha_composite(deco)
    base.alpha_composite(layer)
    return base.convert("RGB")


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
