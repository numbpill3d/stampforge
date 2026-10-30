#!/usr/bin/env python3
"""StampForge — a tiny editor for web stamps, 88×31 buttons and blinkies."""
from __future__ import annotations

import colorsys
import json
import math
import os
import random
import shutil
import sys
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont
from PySide6.QtCore import Qt, QSize, QTimer, QPoint, Signal
from PySide6.QtGui import QAction, QColor, QImage, QPainter, QPalette, QPen, QPixmap, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QSpinBox, QTabWidget, QVBoxLayout, QWidget,
)

ROOT = Path(__file__).resolve().parent
TEMPLATES = ROOT / "templates"
FILES = ROOT / "files"
CONFIG = Path.home() / ".config" / "stampforge" / "config.json"
for _folder in (TEMPLATES, TEMPLATES / "buttons", TEMPLATES / "blinkies", FILES):
    _folder.mkdir(parents=True, exist_ok=True)

ASSET_FOLDERS = {
    "my files": FILES,
    "PNG": Path("/home/scorn/Pictures/GRAPHICS/PNG"),
    "DIV": Path("/home/scorn/Pictures/GRAPHICS/DIV"),
    "GIF": Path("/home/scorn/Pictures/GRAPHICS/GIF"),
    "BACKGROUND TILES": Path("/home/scorn/Pictures/GRAPHICS/BACKGROUND TILES"),
    "FAVICON": Path("/home/scorn/Pictures/GRAPHICS/FAVICON"),
}
IMAGE_EXTENSIONS = {".png", ".gif", ".jpg", ".jpeg", ".webp"}
IMAGE_FILTER = "Images (*.png *.gif *.jpg *.jpeg *.webp)"

# Default canvas (the original web stamp). Kept as module constants for tests.
W, H = 94, 50


@dataclass(frozen=True)
class Format:
    key: str
    label: str
    w: int
    h: int
    templates: Path
    noun: str


FORMATS = {
    "stamp": Format("stamp", "web stamp  94×50", 94, 50, TEMPLATES, "stamp"),
    "button": Format("button", "button  88×31", 88, 31, TEMPLATES / "buttons", "button"),
    "button32": Format("button32", "button  88×32", 88, 32, TEMPLATES / "buttons", "button"),
    "blinkie": Format("blinkie", "blinkie  150×20", 150, 20, TEMPLATES / "blinkies", "blinkie"),
}

_FONT_FILES = [
    ("pixel (built-in)", None),
    ("Terminess", Path.home() / ".local/share/fonts/Terminus/TerminessNerdFont-Regular.ttf"),
    ("Terminess bold", Path.home() / ".local/share/fonts/Terminus/TerminessNerdFont-Bold.ttf"),
    ("ProggyClean", Path.home() / ".local/share/fonts/ProggyClean/ProggyCleanNerdFont-Regular.ttf"),
    ("DejaVu Sans", Path("/usr/share/fonts/TTF/DejaVuSans.ttf")),
    ("DejaVu Sans bold", Path("/usr/share/fonts/TTF/DejaVuSans-Bold.ttf")),
    ("DejaVu Sans Mono", Path("/usr/share/fonts/TTF/DejaVuSansMono.ttf")),
    ("DejaVu Serif", Path("/usr/share/fonts/TTF/DejaVuSerif.ttf")),
]
FONTS = {name: path for name, path in _FONT_FILES if path is None or path.exists()}

COLOR_EFFECTS = ["none", "blink", "flash 2 colours", "colour cycle", "rainbow", "sparkle"]
MOTIONS = ["none", "scroll left", "scroll right", "wave"]
PATTERNS = [
    "solid", "gradient →", "gradient ↓", "stripes", "checker", "glitter", "scanlines", "dots", "stars",
    "grid", "diagonal", "plaid", "noise", "polka", "sunburst", "halftone",
]
BORDERS = [
    "none", "solid", "double", "raised bevel", "sunken bevel",
    "dashed", "dotted", "postage", "inset line", "pixel corners", "shadow frame", "neon frame",
]

DEFAULT_TEXT = {
    "stamp": dict(font="DejaVu Sans bold", size=10),
    "button": dict(font="pixel (built-in)", size=11),
    "button32": dict(font="pixel (built-in)", size=11),
    "blinkie": dict(font="Terminess", size=12),
}

# Small, opinionated recipes for the formats that benefit most from a quick start.
# These are deliberately plain data so adding another web-era look does not require
# touching the UI or renderer.
STYLE_PRESETS = {
    "button": [
        ("Candy chrome", "gradient →", "#ff7fc8", "#fff3fb", "raised bevel", "#ff4fa8"),
        ("Webring blue", "stripes", "#1464c4", "#8ed7ff", "double", "#061b4a"),
        ("Guestbook green", "checker", "#4eaa65", "#c8f58b", "sunken bevel", "#194c2b"),
        ("Night mode", "scanlines", "#17152e", "#6d5cff", "solid", "#b7a9ff"),
        ("Rainbow rave", "gradient ↓", "#ff4f9a", "#57e7ff", "double", "#6d1e8f"),
        ("Pixel lemon", "dots", "#ffe66d", "#fffbd8", "raised bevel", "#a86b00"),
        ("Goth doll", "checker", "#25152f", "#e84b9b", "sunken bevel", "#f6b6df"),
        ("Aqua fan", "stripes", "#0b7285", "#8ff3e5", "solid", "#043b4a"),
    ],
    "button32": [
        ("Candy chrome", "gradient →", "#ff7fc8", "#fff3fb", "raised bevel", "#ff4fa8"),
        ("Webring blue", "stripes", "#1464c4", "#8ed7ff", "double", "#061b4a"),
        ("Guestbook green", "checker", "#4eaa65", "#c8f58b", "sunken bevel", "#194c2b"),
        ("Night mode", "scanlines", "#17152e", "#6d5cff", "solid", "#b7a9ff"),
        ("Rainbow rave", "gradient ↓", "#ff4f9a", "#57e7ff", "double", "#6d1e8f"),
        ("Pixel lemon", "dots", "#ffe66d", "#fffbd8", "raised bevel", "#a86b00"),
        ("Goth doll", "checker", "#25152f", "#e84b9b", "sunken bevel", "#f6b6df"),
        ("Aqua fan", "stripes", "#0b7285", "#8ff3e5", "solid", "#043b4a"),
    ],
    "blinkie": [
        ("Starry webring", "stars", "#11133d", "#ffe66d", "double", "#ff73c8"),
        ("Candy scroll", "gradient →", "#ff4fa8", "#ffd0ec", "raised bevel", "#7a1857"),
        ("Cyber scan", "scanlines", "#071b2d", "#49e7ff", "solid", "#49e7ff"),
        ("Glitter diary", "glitter", "#6c2c91", "#fff0a8", "sunken bevel", "#311047"),
        ("Rainbow rave", "gradient ↓", "#ff4f9a", "#57e7ff", "double", "#6d1e8f"),
        ("Pink alert", "stripes", "#ff2f77", "#ffd0e5", "solid", "#9e1248"),
        ("Forest net", "dots", "#164a3b", "#b8f29a", "raised bevel", "#0b2a22"),
        ("Aqua fan", "checker", "#0b7285", "#8ff3e5", "sunken bevel", "#043b4a"),
    ],
    "stamp": [
        ("Paper sticker", "dots", "#ffe9f4", "#ff8bc4", "solid", "#d33d7d"),
        ("Webring blue", "stripes", "#1464c4", "#8ed7ff", "double", "#061b4a"),
        ("Night mode", "scanlines", "#17152e", "#6d5cff", "solid", "#b7a9ff"),
    ],
}

# A second, larger recipe pack is shared across every canvas type. Keeping the
# recipe shape identical means each format gets the same creative vocabulary,
# while the renderer still adapts the pattern to its exact pixel dimensions.
EXTRA_STYLE_PRESETS = [
    ("Cyber rainbow", "gradient →", "#ff3cac", "#2b86c5", "double", "#190f3d"),
    ("Lavender web", "checker", "#b48cff", "#f1e8ff", "raised bevel", "#6841a8"),
    ("Flame guestbook", "stripes", "#e34234", "#ffd166", "solid", "#7d1d17"),
    ("Ocean dots", "dots", "#075985", "#7dd3fc", "sunken bevel", "#032f4f"),
    ("Terminal mono", "scanlines", "#071a12", "#67f56a", "solid", "#2ecc40"),
    ("Bubblegum glitter", "glitter", "#ff80bf", "#fff0fa", "raised bevel", "#b51e70"),
    ("Lemon stars", "stars", "#5f4b00", "#fff27a", "double", "#ffcf33"),
    ("Sunset 2000", "gradient ↓", "#ff7b54", "#ffd166", "sunken bevel", "#8c3024"),
    ("Arcade checker", "checker", "#301934", "#00e5ff", "solid", "#ff4fd8"),
    ("Midnight glitter", "glitter", "#101828", "#8b5cf6", "double", "#c4b5fd"),
]
for _format_key in STYLE_PRESETS:
    STYLE_PRESETS[_format_key].extend(EXTRA_STYLE_PRESETS)

PREMIUM_STYLE_PRESETS = [
    ("Windows 98", "grid", "#b8c8d8", "#f4f8ff", "raised bevel", "#486070"),
    ("Y2K chrome", "diagonal", "#d6f7ff", "#ff8de1", "double", "#245d8a"),
    ("Bubble tea", "polka", "#ffb4d8", "#fff0a8", "sunken bevel", "#b54478"),
    ("Red alert", "halftone", "#8f102b", "#ffcfda", "solid", "#4a0617"),
    ("Faux denim", "plaid", "#24527a", "#8ac6d1", "raised bevel", "#102d47"),
    ("Candy hearts", "polka", "#ff5c8a", "#ffd1e0", "double", "#9c1748"),
    ("Cyber grid", "grid", "#041b2d", "#00f5d4", "solid", "#00a896"),
    ("Vaporwave", "sunburst", "#5b2a86", "#ff6ec7", "sunken bevel", "#25103f"),
    ("Pixel sunset", "diagonal", "#ff6b35", "#ffd166", "raised bevel", "#913817"),
    ("Haunted web", "halftone", "#17121f", "#a855f7", "double", "#5b21b6"),
    ("Space dust", "noise", "#09111f", "#8be9fd", "solid", "#315b80"),
    ("Limewire", "plaid", "#b7f34a", "#193b2b", "sunken bevel", "#507f22"),
]
for _format_key in STYLE_PRESETS:
    STYLE_PRESETS[_format_key].extend(PREMIUM_STYLE_PRESETS)

STAMP_BORDER_PRESETS = [
    ("Postage pink", "polka", "#fff0f7", "#ff72b6", "postage", "#bd2d77"),
    ("Pixel museum", "grid", "#e8e1cf", "#5e574b", "pixel corners", "#332e28"),
    ("Neon shrine", "scanlines", "#101226", "#ff4fd8", "neon frame", "#55e7ff"),
    ("Soft shadow", "gradient ↓", "#d7efff", "#ffffff", "shadow frame", "#315d82"),
    ("Inset label", "halftone", "#f6c8a8", "#9e3f48", "inset line", "#6b222b"),
    ("Dotted diary", "dots", "#fffbd8", "#e8a93a", "dotted", "#a56700"),
]
STYLE_PRESETS["stamp"].extend(STAMP_BORDER_PRESETS)


# ---------------------------------------------------------------- rendering

def rgba(color) -> tuple[int, int, int, int]:
    if isinstance(color, tuple): return color if len(color) == 4 else (*color, 255)
    value = ImageColor.getrgb(color)
    return value if len(value) == 4 else (*value, 255)


def load_font(name: str, size: int):
    path = FONTS.get(name)
    if path is None:
        return ImageFont.load_default_imagefont()
    return ImageFont.truetype(str(path), size)


def _hue_shift(color, amount: float):
    r, g, b, a = rgba(color)
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    if s < 0.15: s, v = 0.85, max(v, 0.9)
    r, g, b = colorsys.hsv_to_rgb((h + amount) % 1, s, v)
    return (round(r * 255), round(g * 255), round(b * 255), a)


def _rainbow(position: float):
    r, g, b = colorsys.hsv_to_rgb(position % 1, 0.8, 1)
    return (round(r * 255), round(g * 255), round(b * 255), 255)


def _glyph_image(style: dict, color_fn, dy_fn, amp: int) -> Image.Image:
    """Draw the text one glyph at a time so colour and offset can vary per letter."""
    text = style.get("text") or " "
    fnt = load_font(style.get("font", "pixel (built-in)"), int(style.get("size", 11)))
    probe = ImageDraw.Draw(Image.new("L", (1, 1)))
    left, top, right, bottom = probe.textbbox((0, 0), text, font=fnt)
    pad = 1 if style.get("outline") else 0
    shadow = (2 if style.get("outline") else 1) if style.get("shadow") else 0
    width = max(1, right - left + pad * 2 + shadow)
    height = max(1, bottom - top + pad * 2 + shadow + amp * 2)
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image); draw.fontmode = "1"
    xs = [round(fnt.getlength(text[:i])) for i in range(len(text))]
    ox, oy = pad - left, pad - top + amp
    passes = []
    if shadow: passes.append(((shadow, shadow), rgba(style.get("shadow_color", "#000000"))))
    if pad:
        oc = rgba(style.get("outline_color", "#000000"))
        passes += [((dx, dy), oc) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
    for (px, py), colour in passes:
        for i, ch in enumerate(text): draw.text((ox + xs[i] + px, oy + dy_fn(i) + py), ch, fill=colour, font=fnt)
    for i, ch in enumerate(text): draw.text((ox + xs[i], oy + dy_fn(i)), ch, fill=color_fn(i), font=fnt)
    return image


def _sparkle(image: Image.Image, colour, seed: int) -> Image.Image:
    out = image.copy(); px = out.load(); rnd = random.Random(seed)
    w, h = out.size
    for _ in range(max(2, (w * h) // 70)):
        x, y = rnd.randrange(w), rnd.randrange(h)
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)) if rnd.random() < 0.35 else ((0, 0),):
            if 0 <= x + dx < w and 0 <= y + dy < h: px[x + dx, y + dy] = colour
    return out


def ensure_builtin_templates():
    """Seed the empty format folders with selectable, editable starter art."""
    for key in ("stamp", "button", "button32", "blinkie"):
        fmt = FORMATS[key]
        for name, pattern, color, color2, border, border_color in STYLE_PRESETS[key]:
            slug = "".join(ch.lower() if ch.isalnum() else "_" for ch in name).strip("_")
            path = fmt.templates / f"builtin_{slug}.png"
            if path.exists():
                continue
            frame = render_pattern_frames(
                dict(pattern=pattern, color=color, color2=color2, animated=False, hold=1), fmt.w, fmt.h
            )[0]
            apply_border(frame, border, border_color).save(path, "PNG")


def render_text_frames(style: dict, canvas_w: int) -> list[Image.Image]:
    """Build every animation frame for a text layer from its style."""
    effect = style.get("effect", "none"); motion = style.get("motion", "none")
    hold = max(1, int(style.get("hold", 2)))
    c1, c2 = rgba(style.get("color", "#111111")), rgba(style.get("color2", "#ffffff"))
    text = style.get("text") or " "
    colour_steps = {"blink": 2, "flash 2 colours": 2, "colour cycle": 12, "rainbow": 12, "sparkle": 6}.get(effect, 1)
    amp = 2 if motion == "wave" else 0

    def glyphs(step: int, wave_phase: float | None = None):
        if effect == "flash 2 colours": cf = (lambda i: c1) if step % 2 == 0 else (lambda i: c2)
        elif effect == "colour cycle": cf = lambda i: _hue_shift(c1, step / 12)
        elif effect == "rainbow": cf = lambda i: _rainbow(i / max(6, len(text)) + step / 12)
        else: cf = lambda i: c1
        df = (lambda i: round(amp * math.sin(2 * math.pi * (wave_phase + i / 6)))) if wave_phase is not None else (lambda i: 0)
        image = _glyph_image(style, cf, df, amp)
        if effect == "blink" and step % 2 == 1: image = Image.new("RGBA", image.size, (0, 0, 0, 0))
        if effect == "sparkle": image = _sparkle(image, c2, step)
        return image

    frames: list[Image.Image] = []
    if motion in ("scroll left", "scroll right"):
        cache = [glyphs(s) for s in range(colour_steps)]
        tw, th = cache[0].size
        steps = math.ceil((canvas_w + tw) / 2)
        steps = math.ceil(steps / 24) * 24  # a short blank gap keeps 2/4/6/8/12/24-step cycles seamless
        for k in range(steps):
            pos = canvas_w - k * 2 if motion == "scroll left" else -tw + k * 2
            frame = Image.new("RGBA", (canvas_w, th), (0, 0, 0, 0))
            frame.alpha_composite(cache[k % colour_steps], (pos, 0)) if -tw < pos < canvas_w else None
            frames += [frame] * hold
        return frames
    steps = math.lcm(colour_steps, 8) if motion == "wave" else colour_steps
    for k in range(steps):
        frames += [glyphs(k, k / 8 if motion == "wave" else None)] * hold
    return frames


def render_pattern_frames(style: dict, w: int, h: int) -> list[Image.Image]:
    kind = style.get("pattern", "solid"); hold = max(1, int(style.get("hold", 2)))
    c1, c2 = rgba(style.get("color", "#ff9ad5")), rgba(style.get("color2", "#ffffff"))
    animated = bool(style.get("animated", True))

    def mix(t):
        return tuple(round(a + (b - a) * t) for a, b in zip(c1, c2))

    def make(step: int) -> Image.Image:
        image = Image.new("RGBA", (w, h), c1); px = image.load()
        if kind == "gradient →":
            for x in range(w):
                col = mix(x / max(1, w - 1))
                for y in range(h): px[x, y] = col
        elif kind == "gradient ↓":
            for y in range(h):
                col = mix(y / max(1, h - 1))
                for x in range(w): px[x, y] = col
        elif kind == "stripes":
            for y in range(h):
                for x in range(w):
                    if (x + y + step) % 8 < 4: px[x, y] = c2
        elif kind == "checker":
            for y in range(h):
                for x in range(w):
                    if ((x + step) // 4 + y // 4) % 2: px[x, y] = c2
        elif kind == "glitter":
            rnd = random.Random(step * 7919 + 1)
            for y in range(h):
                for x in range(w):
                    r = rnd.random()
                    if r < 0.12: px[x, y] = c2
                    elif r < 0.17: px[x, y] = (255, 255, 255, 255)
                    elif r < 0.30: px[x, y] = mix(0.5)
        elif kind == "scanlines":
            for y in range((step % 2), h, 2):
                for x in range(w): px[x, y] = c2
        elif kind == "dots":
            for y in range(1, h, 4):
                for x in range(1 + (step % 4), w, 4): px[x, y] = c2
        elif kind == "stars":
            rnd = random.Random(42)
            stars = [(rnd.randrange(w), rnd.randrange(h), rnd.randrange(4)) for _ in range(max(3, w * h // 90))]
            for x, y, phase in stars:
                bright = (phase + step) % 4
                px[x, y] = c2 if bright else (255, 255, 255, 255)
                if bright == 0:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        if 0 <= x + dx < w and 0 <= y + dy < h: px[x + dx, y + dy] = c2
        elif kind == "grid":
            for y in range(h):
                for x in range(w):
                    if x % 8 in (0, 1) or y % 8 in (0, 1): px[x, y] = c2
        elif kind == "diagonal":
            for y in range(h):
                for x in range(w):
                    if (x + y + step * 2) % 12 < 3: px[x, y] = c2
        elif kind == "plaid":
            for y in range(h):
                for x in range(w):
                    if x % 12 < 2 or y % 8 < 2: px[x, y] = c2
                    elif x % 12 in (5, 6) and y % 8 in (3, 4): px[x, y] = mix(0.5)
        elif kind == "noise":
            rnd = random.Random(1234 + step)
            for y in range(h):
                for x in range(w):
                    if rnd.random() < 0.18: px[x, y] = c2
                    elif rnd.random() < 0.12: px[x, y] = mix(0.5)
        elif kind == "polka":
            for y in range(h):
                for x in range(w):
                    dx, dy = (x % 12) - 5, (y % 12) - 5
                    if dx * dx + dy * dy <= 7: px[x, y] = c2
        elif kind == "sunburst":
            cx, cy = w / 2, h / 2
            for y in range(h):
                for x in range(w):
                    angle = (math.atan2(y - cy, x - cx) + math.pi) / (2 * math.pi)
                    if int((angle * 12) + step) % 2 == 0: px[x, y] = c2
        elif kind == "halftone":
            for y in range(h):
                for x in range(w):
                    dx, dy = (x % 6) - 2, (y % 6) - 2
                    if dx * dx + dy * dy <= 3: px[x, y] = c2
        return image

    steps = {"stripes": 8, "checker": 8, "glitter": 4, "scanlines": 2, "dots": 4, "stars": 4,
             "diagonal": 6, "noise": 4, "sunburst": 6}.get(kind, 1) if animated else 1
    frames = []
    for k in range(steps): frames += [make(k)] * (hold if steps > 1 else 1)
    return frames


def apply_border(image: Image.Image, kind: str, colour) -> Image.Image:
    if kind == "none": return image
    out = image.copy(); d = ImageDraw.Draw(out); w, h = out.size; c = rgba(colour)
    if kind == "solid":
        d.rectangle((0, 0, w - 1, h - 1), outline=c)
    elif kind == "double":
        d.rectangle((0, 0, w - 1, h - 1), outline=c); d.rectangle((2, 2, w - 3, h - 3), outline=c)
    elif kind in ("raised bevel", "sunken bevel"):
        light, dark = (255, 255, 255, 255), (64, 64, 64, 255)
        soft_light, soft_dark = (220, 220, 220, 255), (128, 128, 128, 255)
        if kind == "sunken bevel": light, dark, soft_light, soft_dark = dark, light, soft_dark, soft_light
        d.line((0, 0, w - 1, 0), fill=light); d.line((0, 0, 0, h - 1), fill=light)
        d.line((0, h - 1, w - 1, h - 1), fill=dark); d.line((w - 1, 0, w - 1, h - 1), fill=dark)
        d.line((1, 1, w - 2, 1), fill=soft_light); d.line((1, 1, 1, h - 2), fill=soft_light)
        d.line((1, h - 2, w - 2, h - 2), fill=soft_dark); d.line((w - 2, 1, w - 2, h - 2), fill=soft_dark)
    elif kind in ("dashed", "postage"):
        dash, gap = (5, 3) if kind == "dashed" else (2, 2)
        for start in range(0, w, dash + gap): d.line((start, 0, min(w - 1, start + dash - 1), 0), fill=c)
        for start in range(0, w, dash + gap): d.line((start, h - 1, min(w - 1, start + dash - 1), h - 1), fill=c)
        for start in range(0, h, dash + gap): d.line((0, start, 0, min(h - 1, start + dash - 1)), fill=c)
        for start in range(0, h, dash + gap): d.line((w - 1, start, w - 1, min(h - 1, start + dash - 1)), fill=c)
    elif kind == "dotted":
        for x in range(1, w - 1, 3): d.point((x, 0), fill=c); d.point((x, h - 1), fill=c)
        for y in range(1, h - 1, 3): d.point((0, y), fill=c); d.point((w - 1, y), fill=c)
    elif kind == "inset line":
        if w > 4 and h > 4: d.rectangle((2, 2, w - 3, h - 3), outline=c)
    elif kind == "pixel corners":
        corner = min(5, max(2, min(w, h) // 5))
        for x1, y1, x2, y2 in ((0, 0, corner, 0), (0, 0, 0, corner), (w - 1, 0, w - 1 - corner, 0), (w - 1, 0, w - 1, corner),
                               (0, h - 1, corner, h - 1), (0, h - 1, 0, h - 1 - corner), (w - 1, h - 1, w - 1 - corner, h - 1), (w - 1, h - 1, w - 1, h - 1 - corner)):
            d.line((x1, y1, x2, y2), fill=c)
    elif kind == "shadow frame":
        shadow = (0, 0, 0, 150)
        if w > 3 and h > 3: d.rectangle((2, 2, w - 1, h - 1), outline=shadow)
        d.rectangle((0, 0, w - 3, h - 3), outline=c)
    elif kind == "neon frame":
        glow = tuple(min(255, channel + 70) for channel in c[:3]) + (255,)
        d.rectangle((0, 0, w - 1, h - 1), outline=(8, 8, 20, 255))
        if w > 2 and h > 2: d.rectangle((1, 1, w - 2, h - 2), outline=glow)
        if w > 4 and h > 4: d.rectangle((2, 2, w - 3, h - 3), outline=c)
    return out


def save_gif(frames: list[Image.Image], path, delay: int = 100, loop: bool = True):
    """Save RGBA frames as a GIF with one shared palette and real transparency."""
    frames = [f.convert("RGBA") for f in frames]
    w, h = frames[0].size
    transparent = any(f.getchannel("A").getextrema()[0] < 128 for f in frames)
    sheet = Image.new("RGB", (w, h * len(frames)), (0, 0, 0))
    for i, f in enumerate(frames):
        mask = f.getchannel("A").point(lambda a: 255 if a >= 128 else 0) if transparent else None
        sheet.paste(f.convert("RGB"), (0, i * h), mask)
    quant = sheet.quantize(colors=255 if transparent else 256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    used = quant.getextrema()[1] + 1
    pal = (quant.getpalette() + [0] * 768)[:768]
    for i in range(used, 256): pal[i * 3:i * 3 + 3] = pal[0:3]  # pad entries never win a nearest-colour tie
    palette_image = Image.new("P", (1, 1)); palette_image.putpalette(pal)
    out = []
    for f in frames:
        p = f.convert("RGB").quantize(palette=palette_image, dither=Image.Dither.NONE)
        if transparent: p.paste(255, mask=f.getchannel("A").point(lambda a: 255 if a < 128 else 0))
        out.append(p)
    kwargs = dict(optimize=False, disposal=2)
    if transparent: kwargs["transparency"] = 255
    if len(out) > 1:
        kwargs.update(save_all=True, append_images=out[1:], duration=delay)
        if loop: kwargs["loop"] = 0
    out[0].save(path, "GIF", **kwargs)


def pil_to_pixmap(im: Image.Image, scale: int = 8) -> QPixmap:
    rgba_im = im.convert("RGBA")
    data = rgba_im.tobytes("raw", "RGBA")
    qimg = QImage(data, rgba_im.width, rgba_im.height, QImage.Format_RGBA8888).copy()
    return QPixmap.fromImage(qimg).scaled(rgba_im.width * scale, rgba_im.height * scale, Qt.IgnoreAspectRatio, Qt.FastTransformation)


def checkerboard(w: int, h: int, cell: int = 6) -> QPixmap:
    pixmap = QPixmap(w, h); painter = QPainter(pixmap)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            painter.fillRect(x, y, cell, cell, QColor("#3a3a3a") if (x // cell + y // cell) % 2 else QColor("#2b2b2b"))
    painter.end(); return pixmap


# ---------------------------------------------------------------- dialogs

def _sidebar(extra=()):
    from PySide6.QtCore import QUrl
    places = [
        Path("/"), Path.home(), Path.home() / "Desktop", Path.home() / "Downloads", Path.home() / "Pictures", FILES,
        Path("/run/media") / os.environ.get("USER", ""), Path("/media") / os.environ.get("USER", ""),
        Path("/mnt"), Path("/media"), Path("/run/media"), *extra,
    ]
    # Include mounted volumes one level down (the usual udisks/KDE layout).
    for root in (Path("/run/media") / os.environ.get("USER", ""), Path("/media") / os.environ.get("USER", ""), Path("/mnt")):
        try: places.extend(sorted(p for p in root.iterdir() if p.is_dir()))
        except OSError: pass
    seen, urls = set(), []
    for place in places:
        if place.is_dir() and place not in seen: seen.add(place); urls.append(QUrl.fromLocalFile(str(place)))
    return urls


def pick_file(parent, title, start, save=False, default_name="", suffix=""):
    """Qt's own file dialog: it follows our light palette instead of the KDE colour scheme."""
    file_filter = f"{IMAGE_FILTER};;All files (*)" if not save else f"{suffix.upper()} (*.{suffix})"
    dialog = QFileDialog(parent, title, str(start), file_filter)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setViewMode(QFileDialog.ViewMode.Detail)
    dialog.setSidebarUrls(_sidebar([getattr(parent, "format", FORMATS["stamp"]).templates]))
    if save:
        dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave); dialog.setDefaultSuffix(suffix); dialog.selectFile(default_name)
    else:
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
    dialog.resize(760, 480)
    return dialog.selectedFiles()[0] if dialog.exec() and dialog.selectedFiles() else ""


def pick_folder(parent, title, start):
    dialog = QFileDialog(parent, title, str(start))
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True); dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    dialog.setFileMode(QFileDialog.FileMode.Directory); dialog.setSidebarUrls(_sidebar()); dialog.resize(760, 480)
    return dialog.selectedFiles()[0] if dialog.exec() and dialog.selectedFiles() else ""


class ColorButton(QPushButton):
    changed = Signal()

    def __init__(self, value: str, title: str = "colour"):
        super().__init__(); self.title = title; self.setValue(value); self.clicked.connect(self._pick)

    def value(self) -> str: return self._value

    def setValue(self, value: str):
        self._value = QColor(value).name()
        ink = "#111" if QColor(self._value).lightness() > 128 else "#fff"
        self.setText(self._value); self.setStyleSheet(f"background:{self._value}; color:{ink};")

    def _pick(self):
        colour = QColorDialog.getColor(QColor(self._value), self, self.title, QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if colour.isValid(): self.setValue(colour.name()); self.changed.emit()


class EffectDialog(QDialog):
    """Shared shell: a form on the left, an animated live preview underneath."""

    def __init__(self, parent, title, canvas_w, canvas_h):
        super().__init__(parent); self.setWindowTitle(title); self.canvas_w, self.canvas_h = canvas_w, canvas_h
        self.frames: list[Image.Image] = []; self.index = 0
        layout = QVBoxLayout(self); self.form = QFormLayout(); layout.addLayout(self.form)
        self.preview = QLabel(); self.preview.setObjectName("preview"); self.preview.setMinimumHeight(100); self.preview.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.preview)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel); buttons.accepted.connect(self.accept); buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.timer = QTimer(self); self.timer.setInterval(100); self.timer.timeout.connect(self._tick); self.timer.start()

    def _tick(self):
        if not self.frames: return
        self.index = (self.index + 1) % len(self.frames); self._show()

    def _show(self):
        if not self.frames: return
        frame = self.frames[self.index % len(self.frames)]
        bg = Image.new("RGBA", (max(frame.width, self.canvas_w), max(frame.height, self.canvas_h)), self.parent().bg if self.parent() and self.parent().bg[3] else (128, 128, 128, 255))
        bg.alpha_composite(frame, ((bg.width - frame.width) // 2, (bg.height - frame.height) // 2))
        scale = max(1, min(4, 460 // bg.width, 120 // max(1, bg.height)))
        self.preview.setPixmap(pil_to_pixmap(bg, scale))

    def refresh(self):
        self.frames = self.build(); self.index = 0; self._show()


class TextDialog(EffectDialog):
    def __init__(self, parent, style: dict, canvas_w, canvas_h):
        super().__init__(parent, "text", canvas_w, canvas_h)
        self.text = QLineEdit(style.get("text", "")); self.text.setPlaceholderText("type the text")
        self.font = QComboBox(); self.font.addItems(list(FONTS)); self.font.setCurrentText(style.get("font", "pixel (built-in)"))
        self.size = QSpinBox(); self.size.setRange(6, 48); self.size.setValue(int(style.get("size", 11)))
        self.color = ColorButton(style.get("color", "#111111"), "text colour")
        self.color2 = ColorButton(style.get("color2", "#ffffff"), "second colour")
        self.outline = QCheckBox("outline"); self.outline.setChecked(bool(style.get("outline")))
        self.outline_color = ColorButton(style.get("outline_color", "#000000"), "outline colour")
        self.shadow = QCheckBox("drop shadow"); self.shadow.setChecked(bool(style.get("shadow")))
        self.shadow_color = ColorButton(style.get("shadow_color", "#000000"), "shadow colour")
        self.effect = QComboBox(); self.effect.addItems(COLOR_EFFECTS); self.effect.setCurrentText(style.get("effect", "none"))
        self.motion = QComboBox(); self.motion.addItems(MOTIONS); self.motion.setCurrentText(style.get("motion", "none"))
        self.hold = QSpinBox(); self.hold.setRange(1, 12); self.hold.setValue(int(style.get("hold", 2))); self.hold.setSuffix(" ticks / step")
        self.hold.setToolTip("how many preview ticks each animation step is held — higher is slower")
        self.form.addRow("text", self.text); self.form.addRow("font", self.font); self.form.addRow("size", self.size)
        self.form.addRow("colour", self.color); self.form.addRow("2nd colour", self.color2)
        row = QHBoxLayout(); row.addWidget(self.outline); row.addWidget(self.outline_color); self.form.addRow(row)
        row = QHBoxLayout(); row.addWidget(self.shadow); row.addWidget(self.shadow_color); self.form.addRow(row)
        self.form.addRow("effect", self.effect); self.form.addRow("motion", self.motion); self.form.addRow("speed", self.hold)
        self.form.addRow(QLabel("2nd colour is used by flash and sparkle"))
        for w in (self.text.textChanged, self.font.currentTextChanged, self.size.valueChanged, self.color.changed, self.color2.changed,
                  self.outline.toggled, self.outline_color.changed, self.shadow.toggled, self.shadow_color.changed,
                  self.effect.currentTextChanged, self.motion.currentTextChanged, self.hold.valueChanged):
            w.connect(self.refresh)
        self.text.setFocus(); self.refresh()

    def style(self) -> dict:
        return dict(text=self.text.text(), font=self.font.currentText(), size=self.size.value(), color=self.color.value(),
                    color2=self.color2.value(), outline=self.outline.isChecked(), outline_color=self.outline_color.value(),
                    shadow=self.shadow.isChecked(), shadow_color=self.shadow_color.value(), effect=self.effect.currentText(),
                    motion=self.motion.currentText(), hold=self.hold.value())

    def build(self): return render_text_frames(self.style(), self.canvas_w)


class PatternDialog(EffectDialog):
    def __init__(self, parent, style: dict, canvas_w, canvas_h):
        super().__init__(parent, "pattern background", canvas_w, canvas_h)
        self.pattern = QComboBox(); self.pattern.addItems(PATTERNS); self.pattern.setCurrentText(style.get("pattern", "glitter"))
        self.color = ColorButton(style.get("color", "#ff9ad5"), "colour 1"); self.color2 = ColorButton(style.get("color2", "#ffffff"), "colour 2")
        self.animated = QCheckBox("animate"); self.animated.setChecked(bool(style.get("animated", True)))
        self.hold = QSpinBox(); self.hold.setRange(1, 12); self.hold.setValue(int(style.get("hold", 2))); self.hold.setSuffix(" ticks / step")
        self.form.addRow("pattern", self.pattern); self.form.addRow("colour 1", self.color); self.form.addRow("colour 2", self.color2)
        self.form.addRow(self.animated); self.form.addRow("speed", self.hold)
        for w in (self.pattern.currentTextChanged, self.color.changed, self.color2.changed, self.animated.toggled, self.hold.valueChanged):
            w.connect(self.refresh)
        self.refresh()

    def style(self) -> dict:
        return dict(pattern=self.pattern.currentText(), color=self.color.value(), color2=self.color2.value(),
                    animated=self.animated.isChecked(), hold=self.hold.value())

    def build(self): return render_pattern_frames(self.style(), self.canvas_w, self.canvas_h)


# ---------------------------------------------------------------- document

@dataclass
class Layer:
    name: str
    kind: str
    frames: list[Image.Image] = field(default_factory=list)
    text: str = ""
    x: int = 0
    y: int = 0
    visible: bool = True
    style: dict | None = None
    source: list[Image.Image] | None = None  # unscaled frames, so repeated resizes don't degrade

    def clone(self) -> "Layer":
        # Frames are never mutated in place, so sharing the image objects is safe.
        return Layer(self.name, self.kind, list(self.frames), self.text, self.x, self.y, self.visible,
                     dict(self.style) if self.style else None, list(self.source) if self.source else None)


class PreviewLabel(QLabel):
    """Pixel canvas that supports drag-to-move and corner resize."""

    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.setAlignment(Qt.AlignCenter)
        self.setMouseTracking(True)
        self.mode = None
        self.start = None

    def _canvas_point(self, point):
        pixmap = self.pixmap()
        if pixmap is None or pixmap.isNull(): return None
        origin = QPoint((self.width() - pixmap.width()) // 2, (self.height() - pixmap.height()) // 2)
        x = (point.x() - origin.x()) / max(1, self.owner.preview_scale)
        y = (point.y() - origin.y()) / max(1, self.owner.preview_scale)
        margin = 6 / max(1, self.owner.preview_scale)
        if x < -margin or y < -margin or x > self.owner.W + margin or y > self.owner.H + margin: return None
        return x, y

    def mousePressEvent(self, event):
        if event.button() != Qt.LeftButton: return
        point = self._canvas_point(event.position().toPoint())
        row = self.owner.layer_list.currentRow()
        if point is None or not (0 <= row < len(self.owner.layers)): return
        layer = self.owner.layers[row]
        width, height = layer.frames[0].size if layer.frames else (self.owner.W, self.owner.H)
        x, y = point
        grab = max(1.5, 10 / max(1, self.owner.preview_scale))
        corner = abs(x - (layer.x + width)) < grab and abs(y - (layer.y + height)) < grab
        inside = layer.x <= x <= layer.x + width and layer.y <= y <= layer.y + height
        if corner: self.mode = "resize"
        elif inside: self.mode = "move"
        else: return
        self.start = (x, y, layer.x, layer.y, width, height)
        self.owner._record()
        self.setCursor(Qt.SizeFDiagCursor if self.mode == "resize" else Qt.ClosedHandCursor)

    def mouseMoveEvent(self, event):
        if not self.mode or not self.start: return
        point = self._canvas_point(event.position().toPoint())
        if point is None: return
        sx, sy, x, y, width, height = self.start; dx, dy = point[0] - sx, point[1] - sy
        if self.mode == "move": self.owner._set_geometry(x + round(dx), y + round(dy), width, height)
        else: self.owner._set_geometry(x, y, max(1, width + round(dx)), max(1, height + round(dy)))

    def mouseReleaseEvent(self, event):
        if self.mode:
            self.mode = None; self.start = None; self.unsetCursor()


class StampForge(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(1040, 680)
        self.setMinimumSize(900, 600)
        self.fmt = "stamp"
        self.bg = (245, 245, 240, 255)
        self.border = "none"
        self.border_color = "#111111"
        self.layers: list[Layer] = []
        self.frame_index = 0
        self.preview_scale = 8
        self.undo_stack = []
        self.redo_stack = []
        self.config = self._load_config()
        self.last_dir = Path(self.config.get("last_dir", str(Path.home())))
        self.timer = QTimer(self)
        self.timer.setInterval(120)
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        self._build_menu()
        self._build_ui()
        self._apply_format_ui()
        self._render()

    # -- format helpers
    @property
    def format(self) -> Format: return FORMATS[self.fmt]

    @property
    def W(self) -> int: return self.format.w

    @property
    def H(self) -> int: return self.format.h

    # -- config
    def _load_config(self) -> dict:
        try: return json.loads(CONFIG.read_text())
        except Exception: return {}

    def _save_config(self):
        try:
            CONFIG.parent.mkdir(parents=True, exist_ok=True)
            self.config["last_dir"] = str(self.last_dir)
            CONFIG.write_text(json.dumps(self.config, indent=2))
        except Exception: pass

    # -- UI
    def _build_menu(self):
        menu = self.menuBar().addMenu("file")
        new_menu = menu.addMenu("new")
        for key, fmt in FORMATS.items():
            action = QAction(fmt.label, self); action.triggered.connect(lambda _=False, k=key: self.new_document(k)); new_menu.addAction(action)
        for label, fn, keys in [("open image as layer…", self.import_image, "Ctrl+I"), ("add text…", self.add_text, "Ctrl+T"),
                                ("add pattern…", self.add_pattern, "Ctrl+P"), (None, None, None),
                                ("export GIF…", lambda: self.export("GIF"), "Ctrl+E"), ("export PNG…", lambda: self.export("PNG"), "Ctrl+Shift+E"),
                                (None, None, None), ("quit", self.close, "Ctrl+Q")]:
            if label is None: menu.addSeparator(); continue
            action = QAction(label, self); action.setShortcut(QKeySequence(keys)); action.triggered.connect(fn); menu.addAction(action)
        edit = self.menuBar().addMenu("edit")
        for label, fn, keys in [("undo", self.undo, ["Ctrl+Z"]), ("redo", self.redo, ["Ctrl+R", "Ctrl+Shift+Z"]),
                                ("edit layer…", self.edit_layer, []), ("delete layer", self.remove_layer, [])]:
            action = QAction(label, self); action.setShortcuts([QKeySequence(k) for k in keys]); action.triggered.connect(fn); edit.addAction(action)
        help_menu = self.menuBar().addMenu("help")
        about = QAction("about StampForge", self); about.triggered.connect(self.about); help_menu.addAction(about)

    def _build_ui(self):
        root = QWidget(); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(12, 10, 12, 10); outer.setSpacing(10)
        titlebar = QWidget(); titlebar.setObjectName("mac-titlebar"); titlebar.setFixedHeight(27)
        title_row = QHBoxLayout(titlebar); title_row.setContentsMargins(7, 2, 7, 2)
        close_box = QLabel("■"); close_box.setObjectName("mac-close"); title_row.addWidget(close_box)
        title_row.addStretch(); title = QLabel("STAMPFORGE // WEB ASSET WORKSHOP"); title.setObjectName("titlebar-label")
        title_row.addWidget(title); title_row.addStretch()
        self.size_label = QLabel(); title_row.addWidget(self.size_label)
        outer.addWidget(titlebar)

        masthead = QWidget(); masthead.setObjectName("masthead")
        top = QHBoxLayout(masthead); top.setContentsMargins(10, 8, 10, 8); top.setSpacing(8)
        making = QLabel("MAKE A"); making.setObjectName("eyebrow"); top.addWidget(making)
        self.format_box = QComboBox()
        for key, fmt in FORMATS.items(): self.format_box.addItem(fmt.label, key)
        self.format_box.currentIndexChanged.connect(lambda i: self.set_format(self.format_box.itemData(i)))
        self.format_box.setToolTip("switching keeps your layers; text and patterns re-render at the new size")
        self.format_box.setMinimumWidth(190); top.addWidget(self.format_box)
        descriptor = QLabel("tiny graphics for personal sites, webrings & shrines"); descriptor.setObjectName("muted")
        top.addWidget(descriptor); top.addStretch()
        gif = QPushButton("EXPORT GIF"); gif.setObjectName("accent"); gif.clicked.connect(lambda: self.export("GIF")); top.addWidget(gif)
        png = QPushButton("EXPORT PNG"); png.clicked.connect(lambda: self.export("PNG")); top.addWidget(png)
        outer.addWidget(masthead)

        body = QWidget(); outer.addWidget(body, 1)
        body_layout = QHBoxLayout(body); body_layout.setContentsMargins(4, 0, 4, 0); body_layout.setSpacing(12)
        left = QVBoxLayout(); left.setSpacing(8); body_layout.addLayout(left, 1)
        preview_label = QLabel("LIVE PREVIEW  /  DRAG TO PLACE"); preview_label.setObjectName("eyebrow"); left.addWidget(preview_label)
        self.preview = PreviewLabel(self); self.preview.setMinimumSize(380, 260); self.preview.setObjectName("preview")
        self.preview.setFocusPolicy(Qt.ClickFocus); self.preview.setToolTip("drag the selected layer to move it • drag its corner square to resize")
        left.addWidget(self.preview, 1)
        controls = QHBoxLayout(); controls.setSpacing(5)
        for text, fn, role in [("IMPORT IMAGE", self.import_image, "tool"), ("ADD TEXT", self.add_text, "accent"), ("ADD PATTERN", self.add_pattern, "tool"), ("BACKGROUND", self.pick_bg, "tool")]:
            b = QPushButton(text); b.setObjectName(role); b.clicked.connect(fn); controls.addWidget(b)
        controls.addStretch(); left.addLayout(controls)
        self.frame_label = QLabel(); left.addWidget(self.frame_label)

        tabs = QTabWidget(); tabs.setMinimumWidth(350); tabs.setMaximumWidth(390); body_layout.addWidget(tabs)

        layers_tab = QWidget(); layers_layout = QVBoxLayout(layers_tab); layers_layout.setSpacing(6)
        layer_hint = QLabel("Stack order: bottom layers draw first. Double-click to edit."); layer_hint.setObjectName("muted"); layer_hint.setWordWrap(True); layers_layout.addWidget(layer_hint)
        self.layer_list = QListWidget(); self.layer_list.currentRowChanged.connect(self._layer_selected)
        self.layer_list.itemDoubleClicked.connect(lambda _item: self.edit_layer())
        for widget in (self.layer_list, self.preview):
            for keys, fn in (("Return", self.edit_layer), ("Enter", self.edit_layer), ("Delete", self.remove_layer)):
                shortcut = QShortcut(QKeySequence(keys), widget, context=Qt.WidgetWithChildrenShortcut); shortcut.activated.connect(fn)
        self.layer_list.setToolTip("bottom of the list is drawn on top • double-click text or pattern layers to edit")
        layers_layout.addWidget(self.layer_list, 1)
        row = QHBoxLayout()
        for text, fn in [("↑", lambda: self.move_layer(-1)), ("↓", lambda: self.move_layer(1)), ("edit", self.edit_layer), ("remove", self.remove_layer)]:
            b = QPushButton(text); b.clicked.connect(fn); row.addWidget(b)
        layers_layout.addLayout(row)
        row = QHBoxLayout()
        for text, fn in [("fit", self.fit_layer), ("center", self.center_layer), ("duplicate", self.duplicate_layer)]:
            b = QPushButton(text); b.clicked.connect(fn); row.addWidget(b)
        layers_layout.addLayout(row)
        self.vis = QCheckBox("visible"); self.vis.setChecked(True); self.vis.stateChanged.connect(self.toggle_layer); layers_layout.addWidget(self.vis)
        geo = QGroupBox("selected layer"); form = QFormLayout(geo)
        self.w_spin = QSpinBox(); self.w_spin.valueChanged.connect(self.resize_layer)
        self.h_spin = QSpinBox(); self.h_spin.valueChanged.connect(self.resize_layer)
        self.x_spin = QSpinBox(); self.x_spin.valueChanged.connect(self.change_position)
        self.y_spin = QSpinBox(); self.y_spin.valueChanged.connect(self.change_position)
        size_row = QHBoxLayout(); size_row.addWidget(self.w_spin); size_row.addWidget(QLabel("×")); size_row.addWidget(self.h_spin)
        pos_row = QHBoxLayout(); pos_row.addWidget(self.x_spin); pos_row.addWidget(QLabel(",")); pos_row.addWidget(self.y_spin)
        form.addRow("size", size_row); form.addRow("x, y", pos_row)
        layers_layout.addWidget(geo)
        tabs.addTab(layers_tab, "layers")

        templates_tab = QWidget(); tl = QVBoxLayout(templates_tab)
        template_heading = QLabel("STARTER ART / DOUBLE-CLICK TO ADD"); template_heading.setObjectName("eyebrow"); tl.addWidget(template_heading)
        self.template_hint = QLabel(); self.template_hint.setWordWrap(True); tl.addWidget(self.template_hint)
        self.template_list = QListWidget(); self._style_asset_list(self.template_list); self.template_list.itemDoubleClicked.connect(self.use_template); tl.addWidget(self.template_list)
        imp = QPushButton("import template…"); imp.clicked.connect(self.import_template); tl.addWidget(imp)
        crop = QPushButton("crop to selected template"); crop.clicked.connect(self.crop_to_template); tl.addWidget(crop)
        refresh = QPushButton("refresh folder"); refresh.clicked.connect(self.refresh_templates); tl.addWidget(refresh)
        tabs.addTab(templates_tab, "templates")

        files_tab = QWidget(); fl = QVBoxLayout(files_tab)
        fl.addWidget(QLabel("image folders — double-click a thumbnail to add it"))
        self.folder_list = QListWidget(); self.folder_list.setMaximumHeight(110); self.folder_list.currentItemChanged.connect(self._file_folder_changed); fl.addWidget(self.folder_list)
        row = QHBoxLayout()
        add_folder = QPushButton("add folder…"); add_folder.clicked.connect(self.add_folder); row.addWidget(add_folder)
        drop_folder = QPushButton("forget folder"); drop_folder.clicked.connect(self.forget_folder); row.addWidget(drop_folder)
        fl.addLayout(row)
        self.file_list = QListWidget(); self._style_asset_list(self.file_list); self.file_list.itemDoubleClicked.connect(self.use_file); fl.addWidget(self.file_list, 1)
        row = QHBoxLayout()
        add_file = QPushButton("import file…"); add_file.clicked.connect(self.import_file); row.addWidget(add_file)
        refresh_files = QPushButton("refresh"); refresh_files.clicked.connect(self.refresh_files); row.addWidget(refresh_files)
        fl.addLayout(row)
        tabs.addTab(files_tab, "files")

        canvas_tab = QWidget(); cform = QVBoxLayout(canvas_tab); cform.setSpacing(8)
        preset_group = QGroupBox("QUICK STYLE PRESETS"); preset_layout = QVBoxLayout(preset_group)
        preset_intro = QLabel("Pick a ready-made web look, then customize the layers below."); preset_intro.setObjectName("muted"); preset_intro.setWordWrap(True); preset_layout.addWidget(preset_intro)
        preset_row = QHBoxLayout()
        self.preset_box = QComboBox(); preset_row.addWidget(self.preset_box, 1)
        self.preset_apply = QPushButton("USE STYLE"); self.preset_apply.setObjectName("accent"); self.preset_apply.clicked.connect(self.apply_preset); preset_row.addWidget(self.preset_apply)
        preset_layout.addLayout(preset_row)
        self.preset_hint = QLabel(); self.preset_hint.setObjectName("muted"); preset_layout.addWidget(self.preset_hint)
        cform.addWidget(preset_group)
        canvas_group = QGroupBox("CANVAS FINISH"); canvas_form = QFormLayout(canvas_group)
        bg_row = QHBoxLayout()
        bg_btn = QPushButton("CHOOSE COLOUR…"); bg_btn.clicked.connect(self.pick_bg); bg_row.addWidget(bg_btn)
        clear_btn = QPushButton("TRANSPARENT"); clear_btn.clicked.connect(self.clear_bg); bg_row.addWidget(clear_btn)
        canvas_form.addRow("background", bg_row)
        self.border_box = QComboBox(); self.border_box.addItems(BORDERS); self.border_box.currentTextChanged.connect(self.set_border)
        self.border_btn = ColorButton(self.border_color, "border colour"); self.border_btn.changed.connect(self.set_border)
        canvas_form.addRow("border", self.border_box); canvas_form.addRow("border colour", self.border_btn)
        self.delay_spin = QSpinBox(); self.delay_spin.setRange(20, 2000); self.delay_spin.setSingleStep(10); self.delay_spin.setValue(120); self.delay_spin.setSuffix(" ms")
        self.delay_spin.valueChanged.connect(lambda v: self.timer.setInterval(v)); self.delay_spin.setToolTip("time per animation tick, used by the preview and GIF export")
        canvas_form.addRow("frame delay", self.delay_spin)
        self.loop = QCheckBox("loop forever"); self.loop.setChecked(True); canvas_form.addRow(self.loop)
        cform.addWidget(canvas_group)
        self.show_box = QCheckBox("outline selected layer in preview"); self.show_box.setChecked(True); self.show_box.toggled.connect(lambda _: self._render()); cform.addWidget(self.show_box)
        self.canvas_note = QLabel(); self.canvas_note.setWordWrap(True); self.canvas_note.setObjectName("note"); cform.addWidget(self.canvas_note)
        cform.addStretch()
        tabs.addTab(canvas_tab, "styles")

        self.refresh_file_folders()

    def _apply_format_ui(self):
        fmt = self.format
        self.setWindowTitle(f"StampForge — {fmt.label.replace('  ', ' ')}")
        self.size_label.setText(f"{fmt.w} × {fmt.h}")
        self.format_box.blockSignals(True); self.format_box.setCurrentIndex(list(FORMATS).index(self.fmt)); self.format_box.blockSignals(False)
        spins = (self.w_spin, self.h_spin, self.x_spin, self.y_spin)
        for s in spins: s.blockSignals(True)
        self.w_spin.setRange(1, fmt.w * 4); self.h_spin.setRange(1, fmt.h * 4)
        self.x_spin.setRange(-fmt.w * 4, fmt.w * 4); self.y_spin.setRange(-fmt.h * 4, fmt.h * 4)
        for s in spins: s.blockSignals(False)
        self.border_box.blockSignals(True); self.border_box.setCurrentText(self.border); self.border_box.blockSignals(False)
        self.border_btn.setValue(self.border_color)
        presets = STYLE_PRESETS.get(self.fmt, [])
        self.preset_box.blockSignals(True); self.preset_box.clear()
        for name, *_ in presets: self.preset_box.addItem(name)
        self.preset_box.blockSignals(False)
        if presets:
            self.preset_hint.setText(f"{len(presets)} {self.format.noun} looks • backgrounds + borders included")
        self.canvas_note.setText(f"exports are always {fmt.w} × {fmt.h} px.\nembed: <img src=\"{fmt.noun}.gif\" width=\"{fmt.w}\" height=\"{fmt.h}\" alt=\"\">")
        self.template_hint.setText(f"{fmt.noun} templates live in {fmt.templates.relative_to(ROOT)}/ — double-click one to add it as a layer")
        if getattr(self, "_listed_templates", None) != fmt.templates:
            self._listed_templates = fmt.templates; self.refresh_templates()
        self._layer_selected(self.layer_list.currentRow())

    def apply_preset(self):
        presets = STYLE_PRESETS.get(self.fmt, [])
        index = self.preset_box.currentIndex()
        if not (0 <= index < len(presets)): return
        name, pattern, color, color2, border, border_color = presets[index]
        self._record()
        self.bg = (*rgba(color)[:3], 255)
        self.border, self.border_color = border, border_color
        # Preset backgrounds are regular editable layers: apply one without
        # destroying artwork, while replacing only the previous preset layer.
        self.layers = [layer for layer in self.layers if not (layer.kind == "pattern" and layer.name.startswith("background:"))]
        self.layer_list.clear()
        background = Layer(f"background: {name}", "pattern", style=dict(
            pattern=pattern, color=color, color2=color2, animated=pattern != "solid", hold=2))
        self._regenerate(background)
        background.name = f"background: {name}"
        self.layers.insert(0, background)
        for layer in self.layers: self.layer_list.addItem(layer.name)
        self._apply_format_ui(); self.layer_list.setCurrentRow(0); self._render()
        self.statusBar().showMessage(f"applied {name} — customize it in the layers tab", 4000)

    # -- documents and formats
    def new_document(self, key: str = "stamp"):
        self._record()
        self.layers.clear(); self.layer_list.clear(); self.bg = (245, 245, 240, 255); self.border = "none"
        self.fmt = key; self.frame_index = 0; self._apply_format_ui(); self._render()

    new_stamp = new_document

    def set_format(self, key: str):
        if key == self.fmt or key not in FORMATS: return
        self._record()
        self.fmt = key
        for layer in self.layers:
            if layer.kind in ("text", "pattern") and layer.style: self._regenerate(layer, keep_position=layer.kind == "text")
            layer.x = max(-layer.frames[0].width + 1, min(layer.x, self.W - 1)) if layer.frames else 0
            layer.y = max(-layer.frames[0].height + 1, min(layer.y, self.H - 1)) if layer.frames else 0
        self._apply_format_ui(); self._render()

    def _regenerate(self, layer: Layer, keep_position=True):
        if layer.kind == "text":
            frames = render_text_frames(layer.style, self.W)
            layer.text = layer.style.get("text", ""); layer.name = self._text_name(layer.style)
            if layer.style.get("motion", "").startswith("scroll"): layer.x = 0
            elif not keep_position: layer.x = (self.W - frames[0].width) // 2
            if not keep_position or layer.style.get("motion", "").startswith("scroll"): layer.y = (self.H - frames[0].height) // 2
        else:
            frames = render_pattern_frames(layer.style, self.W, self.H); layer.x = layer.y = 0
            layer.name = f"pattern: {layer.style.get('pattern')}"
        layer.frames = frames; layer.source = list(frames)

    @staticmethod
    def _text_name(style):
        extras = [e for e in (style.get("effect"), style.get("motion")) if e and e != "none"]
        return "text: " + (style.get("text") or "") + (f"  [{', '.join(extras)}]" if extras else "")

    # -- adding layers
    def _push_layer(self, layer: Layer, index: int | None = None):
        if index is None: self.layers.append(layer); index = len(self.layers) - 1
        else: self.layers.insert(index, layer)
        self.layer_list.insertItem(index, layer.name); self.layer_list.setCurrentRow(index); self._render()

    def import_image(self):
        path = pick_file(self, "choose an image", self.last_dir)
        if path: self.last_dir = Path(path).parent; self._save_config(); self._add_image(path)

    def _add_image(self, path: str):
        try:
            src = Image.open(path)
            frames = []
            for i in range(getattr(src, "n_frames", 1)):
                src.seek(i); frame = src.convert("RGBA")
                frame.thumbnail((self.W, self.H), Image.Resampling.LANCZOS)
                frames.append(frame)
            self._record()
            fw, fh = frames[0].size
            layer = Layer(Path(path).name, "image", frames, x=(self.W - fw) // 2, y=(self.H - fh) // 2, source=list(frames))
            self._push_layer(layer)
        except Exception as exc:
            QMessageBox.warning(self, "could not import", str(exc))

    def add_text(self):
        style = dict(text="", color="#111111" if self.bg[3] and sum(self.bg[:3]) > 380 else "#ffffff", **DEFAULT_TEXT[self.fmt])
        dialog = TextDialog(self, style, self.W, self.H)
        if dialog.exec() and dialog.style()["text"].strip():
            self._record()
            layer = Layer("text", "text", style=dialog.style()); self._regenerate(layer, keep_position=False)
            self._push_layer(layer)

    def add_pattern(self):
        dialog = PatternDialog(self, {}, self.W, self.H)
        if dialog.exec():
            self._record()
            layer = Layer("pattern", "pattern", style=dialog.style()); self._regenerate(layer)
            self._push_layer(layer, 0)

    def edit_layer(self):
        row = self.layer_list.currentRow()
        if not (0 <= row < len(self.layers)): return
        layer = self.layers[row]
        if layer.kind not in ("text", "pattern") or not layer.style:
            self.statusBar().showMessage("only text and pattern layers can be edited — use the size/position controls for images", 4000); return
        dialog = (TextDialog if layer.kind == "text" else PatternDialog)(self, layer.style, self.W, self.H)
        if dialog.exec():
            self._record(); layer.style = dialog.style(); self._regenerate(layer)
            self.layer_list.item(row).setText(layer.name); self._layer_selected(row); self._render()

    def pick_bg(self):
        color = QColorDialog.getColor(QColor(*self.bg[:3]), self, "background", QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if color.isValid(): self._record(); self.bg = (color.red(), color.green(), color.blue(), 255); self._render()

    def clear_bg(self):
        self._record(); self.bg = (0, 0, 0, 0); self._render()

    def set_border(self, *_):
        self._record(); self.border = self.border_box.currentText(); self.border_color = self.border_btn.value(); self._render()

    # -- layer editing
    def _layer_selected(self, row):
        spins = (self.w_spin, self.h_spin, self.x_spin, self.y_spin)
        if 0 <= row < len(self.layers):
            layer = self.layers[row]; self.vis.blockSignals(True); self.vis.setChecked(layer.visible); self.vis.blockSignals(False)
            width, height = layer.frames[0].size if layer.frames else (self.W, self.H)
            for s in spins: s.blockSignals(True)
            self.w_spin.setValue(width); self.h_spin.setValue(height); self.x_spin.setValue(layer.x); self.y_spin.setValue(layer.y)
            for s in spins: s.blockSignals(False)
        self._render()

    def toggle_layer(self, state):
        row = self.layer_list.currentRow()
        if 0 <= row < len(self.layers): self._record(); self.layers[row].visible = bool(state); self._render()

    def change_position(self):
        row = self.layer_list.currentRow()
        if 0 <= row < len(self.layers):
            self._record(); layer = self.layers[row]
            self._set_geometry(self.x_spin.value(), self.y_spin.value(), *layer.frames[0].size)

    def resize_layer(self):
        row = self.layer_list.currentRow()
        if not (0 <= row < len(self.layers)): return
        width, height = self.w_spin.value(), self.h_spin.value()
        layer = self.layers[row]
        if layer.frames and layer.frames[0].size == (width, height): return
        self._record()
        self._set_geometry(layer.x, layer.y, width, height)

    def _set_geometry(self, x, y, width, height):
        row = self.layer_list.currentRow()
        if not (0 <= row < len(self.layers)): return
        layer = self.layers[row]
        if layer.frames and layer.frames[0].size != (width, height):
            base = layer.source or layer.frames
            layer.frames = [frame if frame.size == (width, height) else frame.resize((width, height), Image.Resampling.NEAREST) for frame in base]
        layer.x, layer.y = int(x), int(y)
        spins = (self.w_spin, self.h_spin, self.x_spin, self.y_spin)
        for s in spins: s.blockSignals(True)
        self.x_spin.setValue(layer.x); self.y_spin.setValue(layer.y); self.w_spin.setValue(width); self.h_spin.setValue(height)
        for s in spins: s.blockSignals(False)
        self._render()

    def fit_layer(self):
        row = self.layer_list.currentRow()
        if not (0 <= row < len(self.layers)) or not self.layers[row].frames: return
        fw, fh = (self.layers[row].source or self.layers[row].frames)[0].size
        scale = min(self.W / fw, self.H / fh); nw, nh = max(1, round(fw * scale)), max(1, round(fh * scale))
        self._record(); self._set_geometry((self.W - nw) // 2, (self.H - nh) // 2, nw, nh)

    def center_layer(self):
        row = self.layer_list.currentRow()
        if not (0 <= row < len(self.layers)) or not self.layers[row].frames: return
        fw, fh = self.layers[row].frames[0].size
        self._record(); self._set_geometry((self.W - fw) // 2, (self.H - fh) // 2, fw, fh)

    def duplicate_layer(self):
        row = self.layer_list.currentRow()
        if 0 <= row < len(self.layers):
            self._record(); copy = self.layers[row].clone(); copy.name += " copy"; self._push_layer(copy, row + 1)

    def move_layer(self, delta):
        row = self.layer_list.currentRow(); new = row + delta
        if 0 <= row < len(self.layers) and 0 <= new < len(self.layers):
            self._record()
            self.layers[row], self.layers[new] = self.layers[new], self.layers[row]; item = self.layer_list.takeItem(row); self.layer_list.insertItem(new, item); self.layer_list.setCurrentRow(new); self._render()

    def remove_layer(self):
        row = self.layer_list.currentRow()
        if 0 <= row < len(self.layers): self._record(); self.layers.pop(row); self.layer_list.takeItem(row); self._render()

    # -- templates
    def refresh_templates(self):
        self.template_list.clear()
        folder = self.format.templates; folder.mkdir(parents=True, exist_ok=True)
        for p in sorted(folder.iterdir()):
            if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS: self._add_asset_item(self.template_list, p)

    def import_template(self):
        path = pick_file(self, f"choose a {self.format.noun} template", self.last_dir)
        if path:
            self.last_dir = Path(path).parent; self._save_config()
            shutil.copy2(path, self.format.templates / Path(path).name); self.refresh_templates()

    def use_template(self, item): self._add_image(item.data(Qt.UserRole))

    def crop_to_template(self):
        item = self.template_list.currentItem()
        if not item:
            QMessageBox.information(self, "choose a template", "Select a template thumbnail first.")
            return
        path = item.data(Qt.UserRole); w, h = self.W, self.H
        try:
            template = Image.open(path).convert("RGBA").resize((w, h), Image.Resampling.LANCZOS)
            alpha = template.getchannel("A")
            # Remove paper-coloured margins connected to the outside edge. This
            # handles the common stamp-template pattern: a red/black frame,
            # white paper in the middle, and extra white gutters at left/right.
            pix = template.load(); base_alpha = alpha.load(); mask = Image.new("L", (w, h), 255); mask_pix = mask.load()
            corners = [pix[0, 0][:3], pix[w-1, 0][:3], pix[0, h-1][:3], pix[w-1, h-1][:3]]
            bg = max(set(corners), key=corners.count)

            def is_outer_paper(x, y):
                r, g, b, _ = pix[x, y]
                return base_alpha[x, y] > 0 and max(abs(r-bg[0]), abs(g-bg[1]), abs(b-bg[2])) < 32
            queue = deque(); seen = set()
            for x in range(w): queue.extend([(x, 0), (x, h-1)])
            for y in range(h): queue.extend([(0, y), (w-1, y)])
            while queue:
                x, y = queue.popleft()
                if (x, y) in seen or not (0 <= x < w and 0 <= y < h) or not is_outer_paper(x, y): continue
                seen.add((x, y)); mask_pix[x, y] = 0
                queue.extend(((x+1, y), (x-1, y), (x, y+1), (x, y-1)))
            # A dark/coloured frame can touch all four edges. In that case the
            # flood fill finds the thin frame itself, not removable paper. Keep
            # the template alpha unless the connected edge region is substantial
            # enough to be a real gutter/margin.
            edge_area = len(seen) / max(1, w * h)
            paper_like = min(bg) >= 200 and max(bg) - min(bg) <= 32
            # White paper is a removable gutter even when it is only a few
            # pixels wide. Dark/coloured edge regions are usually the actual
            # stamp frame and must remain visible.
            if len(seen) < 4 or (edge_area < 0.16 and not paper_like): mask = alpha
            self._record()
            frames = []
            for index in range(self.frame_count()):
                image = self._composite(index, finish=False)
                image.putalpha(Image.composite(image.getchannel("A"), Image.new("L", (w, h), 0), mask))
                frames.append(image)
            self.layers = [Layer("cropped: " + Path(path).name, "mask", frames, source=list(frames))]
            # The crop mask defines the final silhouette. Keep the canvas
            # transparent so later previews and exports retain it.
            self.bg = (0, 0, 0, 0)
            self.layer_list.clear(); self.layer_list.addItem(self.layers[0].name); self.layer_list.setCurrentRow(0); self._render()
        except Exception as exc:
            QMessageBox.warning(self, "crop failed", str(exc))

    # -- file browser
    def import_file(self):
        path = pick_file(self, "choose file", self.last_dir)
        if path:
            self.last_dir = Path(path).parent; self._save_config()
            shutil.copy2(path, FILES / Path(path).name); self.refresh_files()

    def refresh_files(self):
        item = self.folder_list.currentItem()
        self._load_file_folder(Path(item.data(Qt.UserRole)) if item else FILES)

    def _all_folders(self) -> dict:
        folders = {label: path for label, path in ASSET_FOLDERS.items() if path.is_dir()}
        for extra in self.config.get("folders", []):
            p = Path(extra)
            if p.is_dir(): folders[p.name] = p
        return folders

    def refresh_file_folders(self):
        self.folder_list.clear()
        for label, path in self._all_folders().items():
            item = QListWidgetItem(label); item.setData(Qt.UserRole, str(path)); item.setToolTip(str(path)); self.folder_list.addItem(item)
        if self.folder_list.count(): self.folder_list.setCurrentRow(0)

    def add_folder(self):
        folder = pick_folder(self, "add an image folder", self.last_dir)
        if folder:
            self.config.setdefault("folders", [])
            if folder not in self.config["folders"]: self.config["folders"].append(folder)
            self.last_dir = Path(folder); self._save_config(); self.refresh_file_folders()
            self.folder_list.setCurrentRow(self.folder_list.count() - 1)

    def forget_folder(self):
        item = self.folder_list.currentItem()
        if not item: return
        path = item.data(Qt.UserRole)
        if path in self.config.get("folders", []):
            self.config["folders"].remove(path); self._save_config(); self.refresh_file_folders()
        else:
            self.statusBar().showMessage("built-in folders can't be removed", 3000)

    def _file_folder_changed(self, current, _previous):
        if current: self._load_file_folder(Path(current.data(Qt.UserRole)))

    def _load_file_folder(self, folder):
        self.file_list.clear()
        try: paths = [p for p in sorted(folder.iterdir()) if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS]
        except OSError: paths = []
        shown = paths[:800]
        for p in shown: self._add_asset_item(self.file_list, p)
        suffix = f" (showing first {len(shown)} of {len(paths)})" if len(paths) > len(shown) else ""
        self.file_list.setToolTip(f"{folder}{suffix}")

    def use_file(self, item): self._add_image(item.data(Qt.UserRole))

    def _style_asset_list(self, widget):
        widget.setViewMode(QListWidget.IconMode)
        widget.setIconSize(QSize(94, 50))
        widget.setGridSize(QSize(116, 66))
        widget.setResizeMode(QListWidget.Adjust)
        widget.setMovement(QListWidget.Static)
        widget.setSpacing(4)
        widget.setUniformItemSizes(True)

    def _add_asset_item(self, widget, path):
        pixmap = QPixmap(str(path))
        if pixmap.isNull(): return
        size = f"{pixmap.width()}×{pixmap.height()}"
        pixmap = pixmap.scaled(94, 50, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        item = QListWidgetItem(QIcon(pixmap), "")
        item.setToolTip(f"{path.name}  ({size})")
        item.setData(Qt.UserRole, str(path))
        widget.addItem(item)

    # -- compositing
    def frame_count(self) -> int:
        counts = [len(l.frames) for l in self.layers if l.visible and l.frames] or [1]
        total = 1
        for c in counts: total = math.lcm(total, c)
        return total if total <= 360 else max(counts)

    def _composite(self, frame=0, finish=True):
        canvas = Image.new("RGBA", (self.W, self.H), self.bg)
        for layer in self.layers:
            if not layer.visible or not layer.frames: continue
            src = layer.frames[frame % len(layer.frames)]
            canvas.alpha_composite(src, (layer.x, layer.y)) if (layer.x >= 0 and layer.y >= 0) else canvas.alpha_composite(src.crop((max(0, -layer.x), max(0, -layer.y), src.width, src.height)), (max(0, layer.x), max(0, layer.y)))
        return apply_border(canvas, self.border, self.border_color) if finish else canvas

    # -- undo
    def _state(self):
        return (self.fmt, self.bg, self.border, self.border_color, [l.clone() for l in self.layers])

    def _record(self):
        self.undo_stack.append(self._state())
        self.redo_stack.clear()
        if len(self.undo_stack) > 60: self.undo_stack.pop(0)

    def _restore(self, state):
        self.fmt, self.bg, self.border, self.border_color, layers = state
        self.layers = [l.clone() for l in layers]
        self.layer_list.clear()
        for layer in self.layers: self.layer_list.addItem(layer.name)
        if self.layers: self.layer_list.setCurrentRow(0)
        self._apply_format_ui(); self._render()

    def undo(self):
        if not self.undo_stack: return
        self.redo_stack.append(self._state()); self._restore(self.undo_stack.pop())

    def redo(self):
        if not self.redo_stack: return
        self.undo_stack.append(self._state()); self._restore(self.redo_stack.pop())

    # -- preview
    def _render(self):
        if not hasattr(self, "frame_label"): return
        max_w, max_h = max(200, self.preview.width() - 20), max(120, self.preview.height() - 20)
        scale = max(1, min(max_w // self.W, max_h // self.H)); self.preview_scale = scale
        count = self.frame_count()
        image = self._composite(self.frame_index % count)
        pixmap = checkerboard(self.W * scale, self.H * scale, max(4, scale * 2))
        painter = QPainter(pixmap); painter.drawPixmap(0, 0, pil_to_pixmap(image, scale))
        row = self.layer_list.currentRow()
        if self.show_box.isChecked() and 0 <= row < len(self.layers) and self.layers[row].frames:
            layer = self.layers[row]; lw, lh = layer.frames[0].size
            rect = (layer.x * scale, layer.y * scale, lw * scale - 1, lh * scale - 1)
            painter.setPen(QPen(QColor("#ffffff"))); painter.drawRect(*rect)  # white under black dashes reads on any colour
            pen = QPen(QColor("#000000")); pen.setStyle(Qt.DashLine); painter.setPen(pen); painter.drawRect(*rect)
            hx, hy = (layer.x + lw) * scale - 5, (layer.y + lh) * scale - 5
            painter.fillRect(hx - 1, hy - 1, 8, 8, QColor("#ffffff")); painter.fillRect(hx, hy, 6, 6, QColor("#000000"))
        painter.end()
        self.preview.setPixmap(pixmap)
        seconds = count * self.delay_spin.value() / 1000
        self.frame_label.setText(f"{self.W} × {self.H} px  •  frame {self.frame_index % count + 1}/{count} ({seconds:.1f}s loop)  •  {scale}×")

    def _tick(self):
        count = self.frame_count()
        if count > 1:
            self.frame_index = (self.frame_index + 1) % count
            self._render()

    def resizeEvent(self, event): super().resizeEvent(event); self._render()

    # -- export
    def export(self, kind):
        ext = "gif" if kind == "GIF" else "png"
        path = pick_file(self, f"export {kind}", self.last_dir, save=True, default_name=f"{self.format.noun}.{ext}", suffix=ext)
        if not path: return
        self.last_dir = Path(path).parent; self._save_config()
        count = self.frame_count()
        try:
            if kind == "GIF": save_gif([self._composite(i) for i in range(count)], path, self.delay_spin.value(), self.loop.isChecked())
            else: self._composite(self.frame_index % count if count > 1 else 0).save(path, "PNG")
            note = "  (PNG holds one frame — use GIF for animation)" if kind == "PNG" and count > 1 else ""
            self.statusBar().showMessage(f"saved {path}{note}", 6000)
        except Exception as exc: QMessageBox.warning(self, "export failed", str(exc))

    def about(self):
        QMessageBox.information(self, "StampForge", "StampForge\nA tiny editor for 94×50 web stamps, 88×31 buttons and 150×20 blinkies.\n\nRetro tools for tiny personal websites.")


# ---------------------------------------------------------------- theme

STYLESHEET = """
  /* A compact System 7 / early Mac OS palette: graphite, platinum and paper. */
  QWidget { background:#bdbdbd; color:#111; font-family:'Geneva','Charcoal','DejaVu Sans'; font-size:12px; }
  QMainWindow, QDialog, QFileDialog, QColorDialog, QMessageBox { background:#bdbdbd; }
  QLabel, QCheckBox, QRadioButton { background:transparent; color:#111; }
  QMenuBar { background:#f2f2f2; color:#111; border-bottom:1px solid #111; padding:1px; }
  QMenuBar::item { padding:3px 9px; background:transparent; }
  QMenuBar::item:selected, QMenu::item:selected { background:#111; color:#fff; }
  QMenu { background:#f2f2f2; color:#111; border:1px solid #111; }
  QMenu::item { padding:4px 28px 4px 14px; }
  QMenu::separator { height:1px; background:#111; margin:3px 6px; }
  QPushButton, QToolButton { background:#d7d7d7; color:#111; border:1px solid #111; border-top-color:#fff; border-left-color:#fff; padding:4px 9px; min-height:20px; }
  QToolButton { padding:3px; min-height:18px; }
  QPushButton:hover, QToolButton:hover { background:#e8e8e8; }
  QPushButton:pressed, QToolButton:pressed, QToolButton:checked { background:#111; color:#fff; border-color:#111; }
  QPushButton:disabled, QToolButton:disabled { color:#808080; }
  QListWidget, QListView, QTreeView, QTableView, QLineEdit, QSpinBox, QTextEdit, QPlainTextEdit {
      background:#f7f7f2; color:#111; border:1px solid #111; padding:3px;
      selection-background-color:#111; selection-color:#fff; alternate-background-color:#ecece5; }
  QAbstractItemView { background:#f7f7f2; color:#111; selection-background-color:#111; selection-color:#fff; outline:0; }
  QAbstractItemView::item { color:#111; padding:2px; }
  QAbstractItemView::item:selected { background:#111; color:#fff; }
  QAbstractItemView::item:hover:!selected { background:#e1e1d8; }
  QAbstractScrollArea > QWidget#qt_scrollarea_viewport { background:#f7f7f2; }
  QHeaderView { background:#d7d7d7; }
  QHeaderView::section { background:#d7d7d7; color:#111; border:0; border-right:1px solid #888; border-bottom:1px solid #111; padding:3px 6px; }
  QComboBox { background:#f7f7f2; color:#111; border:1px solid #111; padding:3px 6px; min-height:18px; }
  QComboBox QAbstractItemView { background:#f7f7f2; color:#111; border:1px solid #111; selection-background-color:#111; selection-color:#fff; }
  QScrollBar:vertical { background:#d7d7d7; width:14px; border-left:1px solid #111; }
  QScrollBar:horizontal { background:#d7d7d7; height:14px; border-top:1px solid #111; }
  QScrollBar::handle { background:#f2f2f2; border:1px solid #111; min-height:20px; min-width:20px; }
  QScrollBar::add-line, QScrollBar::sub-line { width:0; height:0; }
  QScrollBar::add-page, QScrollBar::sub-page { background:transparent; }
  QToolTip { background:#ffffe1; color:#111; border:1px solid #111; padding:3px; }
  QTabWidget::pane { border:1px solid #111; background:#d0d0d0; }
  QTabWidget > QWidget > QWidget { background:#d0d0d0; }
  QTabBar::tab { background:#c4c4c4; color:#111; border:1px solid #111; border-bottom:0; padding:6px 10px; }
  QTabBar::tab:selected { background:#f2f2f2; }
  QGroupBox { border:1px solid #111; margin-top:10px; padding-top:8px; }
  QGroupBox::title { subcontrol-origin:margin; left:8px; padding:0 3px; background:#bdbdbd; }
  QStatusBar { background:#d7d7d7; color:#111; border-top:1px solid #111; }
  QSplitter::handle { background:#9a9a9a; }
  #mac-titlebar { background:#d7d7d7; border:1px solid #111; border-top-color:#fff; border-left-color:#fff; }
  #mac-titlebar QLabel { background:transparent; font-weight:bold; }
  #mac-titlebar #mac-close { border:1px solid #111; padding:0 2px; font-size:8px; }
  #preview { background:#2b2b2b; border:2px solid #111; }
  /* Retro-web workshop layer: cream paper, electric pink, blue link chrome. */
  #masthead { background:#fff4fb; border:1px solid #111; border-top:3px solid #111; }
  #titlebar-label { font-weight:bold; letter-spacing:1px; }
  #eyebrow { color:#9b2365; font-weight:bold; letter-spacing:1px; font-size:10px; }
  #muted, QLabel#muted { color:#5b5360; font-size:11px; }
  #note { background:#fffbd8; border:1px solid #9a8c55; padding:6px; }
  QPushButton#accent { background:#ff66b7; color:#111; font-weight:bold; border:2px solid #111; border-top-color:#fff; border-left-color:#fff; }
  QPushButton#accent:hover { background:#ff94cf; }
  QPushButton#tool { background:#d7ecff; }
  QGroupBox { background:#d9d9d9; border:1px solid #111; margin-top:13px; padding:10px 7px 7px; }
  QGroupBox::title { color:#111; font-weight:bold; letter-spacing:1px; subcontrol-origin:margin; left:8px; padding:1px 5px; background:#d9d9d9; }
  QTabBar::tab { font-weight:bold; letter-spacing:.5px; padding:7px 12px; }
  QTabBar::tab:selected { color:#9b2365; border-top:3px solid #ff66b7; }
  QListWidget { padding:5px; }
  QStatusBar { font-size:11px; }
  QSpinBox, QComboBox { min-height:22px; }
  QCheckBox::indicator:checked { background:#ff66b7; border:1px solid #111; }
"""


def light_palette() -> QPalette:
    """A fixed light palette so a dark desktop colour scheme can't leak into dialogs."""
    p = QPalette()
    colours = {
        QPalette.Window: "#bdbdbd", QPalette.WindowText: "#111111", QPalette.Base: "#f7f7f2",
        QPalette.AlternateBase: "#ecece5", QPalette.Text: "#111111", QPalette.Button: "#d7d7d7",
        QPalette.ButtonText: "#111111", QPalette.BrightText: "#ffffff", QPalette.Highlight: "#111111",
        QPalette.HighlightedText: "#ffffff", QPalette.ToolTipBase: "#ffffe1", QPalette.ToolTipText: "#111111",
        QPalette.PlaceholderText: "#6a6a6a", QPalette.Link: "#0000cc", QPalette.Light: "#ffffff",
        QPalette.Midlight: "#e8e8e8", QPalette.Mid: "#9a9a9a", QPalette.Dark: "#6e6e6e", QPalette.Shadow: "#111111",
    }
    for group in (QPalette.Active, QPalette.Inactive, QPalette.Disabled):
        for role, colour in colours.items(): p.setColor(group, role, QColor(colour))
    for role in (QPalette.Text, QPalette.WindowText, QPalette.ButtonText):
        p.setColor(QPalette.Disabled, role, QColor("#808080"))
    return p


def main():
    ensure_builtin_templates()
    app = QApplication(sys.argv); app.setStyle("Fusion")
    app.setPalette(light_palette())
    app.setStyleSheet(STYLESHEET)
    win = StampForge(); win.show(); sys.exit(app.exec())


if __name__ == "__main__": main()
