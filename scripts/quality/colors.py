"""Color parsing and conversion for the design checks and the palette generator.

Supports CSS hex, rgb()/rgba(), hsl()/hsla(), oklch(), oklab() and named
colors; converts between sRGB and OKLCH; computes WCAG 2 contrast.
Standard library only, Python 3.9+.
"""
from __future__ import annotations

import math
import re

__all__ = [
    "NAMED_COLORS",
    "parse_color",
    "srgb_to_oklch",
    "oklch_to_srgb",
    "in_gamut",
    "gamut_map",
    "to_hex",
    "format_oklch",
    "composite",
    "relative_luminance",
    "contrast_ratio",
]

_NAMED = """
aliceblue f0f8ff antiquewhite faebd7 aqua 00ffff aquamarine 7fffd4 azure f0ffff
beige f5f5dc bisque ffe4c4 black 000000 blanchedalmond ffebcd blue 0000ff
blueviolet 8a2be2 brown a52a2a burlywood deb887 cadetblue 5f9ea0 chartreuse 7fff00
chocolate d2691e coral ff7f50 cornflowerblue 6495ed cornsilk fff8dc crimson dc143c
cyan 00ffff darkblue 00008b darkcyan 008b8b darkgoldenrod b8860b darkgray a9a9a9
darkgreen 006400 darkgrey a9a9a9 darkkhaki bdb76b darkmagenta 8b008b
darkolivegreen 556b2f darkorange ff8c00 darkorchid 9932cc darkred 8b0000
darksalmon e9967a darkseagreen 8fbc8f darkslateblue 483d8b darkslategray 2f4f4f
darkslategrey 2f4f4f darkturquoise 00ced1 darkviolet 9400d3 deeppink ff1493
deepskyblue 00bfff dimgray 696969 dimgrey 696969 dodgerblue 1e90ff firebrick b22222
floralwhite fffaf0 forestgreen 228b22 fuchsia ff00ff gainsboro dcdcdc
ghostwhite f8f8ff gold ffd700 goldenrod daa520 gray 808080 green 008000
greenyellow adff2f grey 808080 honeydew f0fff0 hotpink ff69b4 indianred cd5c5c
indigo 4b0082 ivory fffff0 khaki f0e68c lavender e6e6fa lavenderblush fff0f5
lawngreen 7cfc00 lemonchiffon fffacd lightblue add8e6 lightcoral f08080
lightcyan e0ffff lightgoldenrodyellow fafad2 lightgray d3d3d3 lightgreen 90ee90
lightgrey d3d3d3 lightpink ffb6c1 lightsalmon ffa07a lightseagreen 20b2aa
lightskyblue 87cefa lightslategray 778899 lightslategrey 778899
lightsteelblue b0c4de lightyellow ffffe0 lime 00ff00 limegreen 32cd32 linen faf0e6
magenta ff00ff maroon 800000 mediumaquamarine 66cdaa mediumblue 0000cd
mediumorchid ba55d3 mediumpurple 9370db mediumseagreen 3cb371
mediumslateblue 7b68ee mediumspringgreen 00fa9a mediumturquoise 48d1cc
mediumvioletred c71585 midnightblue 191970 mintcream f5fffa mistyrose ffe4e1
moccasin ffe4b5 navajowhite ffdead navy 000080 oldlace fdf5e6 olive 808000
olivedrab 6b8e23 orange ffa500 orangered ff4500 orchid da70d6 palegoldenrod eee8aa
palegreen 98fb98 paleturquoise afeeee palevioletred db7093 papayawhip ffefd5
peachpuff ffdab9 peru cd853f pink ffc0cb plum dda0dd powderblue b0e0e6
purple 800080 rebeccapurple 663399 red ff0000 rosybrown bc8f8f royalblue 4169e1
saddlebrown 8b4513 salmon fa8072 sandybrown f4a460 seagreen 2e8b57 seashell fff5ee
sienna a0522d silver c0c0c0 skyblue 87ceeb slateblue 6a5acd slategray 708090
slategrey 708090 snow fffafa springgreen 00ff7f steelblue 4682b4 tan d2b48c
teal 008080 thistle d8bfd8 tomato ff6347 turquoise 40e0d0 violet ee82ee
wheat f5deb3 white ffffff whitesmoke f5f5f5 yellow ffff00 yellowgreen 9acd32
"""

_pairs = _NAMED.split()
NAMED_COLORS = {_pairs[i]: "#" + _pairs[i + 1] for i in range(0, len(_pairs), 2)}

_FUNC = re.compile(r"^\s*(rgba?|hsla?|oklch|oklab)\(\s*(.*?)\s*\)\s*$", re.I | re.S)


def _split_args(body):
    alpha = None
    if "/" in body:
        body, alpha = body.split("/", 1)
        alpha = alpha.strip()
    parts = [p for p in re.split(r"[\s,]+", body.strip()) if p]
    if alpha is None and len(parts) == 4:
        alpha = parts.pop()
    return parts, alpha


def _number(token, percent_of=1.0):
    token = token.strip().lower()
    if token == "none":
        return 0.0
    if token.endswith("%"):
        return float(token[:-1]) / 100.0 * percent_of
    for unit, factor in (("deg", 1.0), ("grad", 0.9), ("rad", 180.0 / math.pi), ("turn", 360.0)):
        if token.endswith(unit):
            return float(token[: -len(unit)]) * factor
    return float(token)


def _alpha(token):
    if token is None:
        return 1.0
    return max(0.0, min(1.0, _number(token, 1.0)))


def _hsl_to_rgb(h, s, light):
    def channel(n):
        k = (n + (h % 360) / 30.0) % 12
        a = s * min(light, 1 - light)
        return light - a * max(-1.0, min(k - 3, 9 - k, 1.0))

    return channel(0), channel(8), channel(4)


def _decode(c):
    return math.copysign(((abs(c) + 0.055) / 1.055) ** 2.4, c) if abs(c) > 0.04045 else c / 12.92


def _encode(c):
    return math.copysign(1.055 * abs(c) ** (1 / 2.4) - 0.055, c) if abs(c) > 0.0031308 else 12.92 * c


def _cbrt(x):
    return math.copysign(abs(x) ** (1.0 / 3.0), x)


def _oklab_to_srgb(L, a, b):
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    r = 4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s
    g = -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s
    bb = -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s
    return _encode(r), _encode(g), _encode(bb)


def oklch_to_srgb(L, C, H):
    """Convert OKLCH (L 0..1, C, H degrees) to gamma-encoded sRGB, not clamped."""
    rad = math.radians(H)
    return _oklab_to_srgb(L, C * math.cos(rad), C * math.sin(rad))


def srgb_to_oklch(r, g, b):
    """Convert gamma-encoded sRGB (0..1) to OKLCH as (L, C, H in degrees)."""
    r, g, b = _decode(r), _decode(g), _decode(b)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = _cbrt(l), _cbrt(m), _cbrt(s)
    L = 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_
    a = 1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_
    bb = 0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_
    C = math.hypot(a, bb)
    H = math.degrees(math.atan2(bb, a)) % 360 if C > 1e-7 else 0.0
    return L, C, H


def in_gamut(rgb, eps=1e-5):
    """True when every sRGB channel lies within 0..1 (with a small tolerance)."""
    return all(-eps <= c <= 1 + eps for c in rgb)


def gamut_map(L, C, H):
    """Reduce chroma (keeping lightness and hue) until the color fits in sRGB."""
    L = max(0.0, min(1.0, L))
    if in_gamut(oklch_to_srgb(L, C, H)):
        return L, C, H
    lo, hi = 0.0, C
    for _ in range(30):
        mid = (lo + hi) / 2
        if in_gamut(oklch_to_srgb(L, mid, H)):
            lo = mid
        else:
            hi = mid
    return L, lo, H


def _clamp_rgb(rgb):
    return tuple(max(0.0, min(1.0, c)) for c in rgb)


def to_hex(rgb):
    """Format sRGB (0..1, clamped) as #rrggbb."""
    return "#" + "".join(f"{round(c * 255):02x}" for c in _clamp_rgb(rgb))


def format_oklch(L, C, H, alpha=None):
    """Format a CSS oklch() value with fixed precision."""
    if C < 0.0005:
        C, H = 0.0, 0.0
    text = f"oklch({L:.4f} {C:.4f} {H:.3f}"
    if alpha is not None and alpha < 1:
        text += f" / {alpha:g}"
    return text + ")"


def parse_color(value):
    """Parse a CSS color into (r, g, b, alpha) with sRGB channels clamped to 0..1.

    Returns None for anything it cannot evaluate (var(), color-mix(), keywords
    such as currentColor).
    """
    if value is None:
        return None
    text = str(value).strip().lower()
    if text == "transparent":
        return (0.0, 0.0, 0.0, 0.0)
    if text in NAMED_COLORS:
        text = NAMED_COLORS[text]
    if text.startswith("#"):
        digits = text[1:]
        if not re.fullmatch(r"[0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8}", digits):
            return None
        if len(digits) in (3, 4):
            digits = "".join(ch * 2 for ch in digits)
        channels = [int(digits[i:i + 2], 16) / 255 for i in range(0, len(digits), 2)]
        if len(channels) == 3:
            channels.append(1.0)
        return tuple(channels)
    match = _FUNC.match(text)
    if not match:
        return None
    name, body = match.group(1), match.group(2)
    try:
        parts, alpha = _split_args(body)
        if len(parts) != 3:
            return None
        if name.startswith("rgb"):
            rgb = tuple(
                _number(p, 1.0) if p.endswith("%") else _number(p) / 255.0 for p in parts
            )
        elif name.startswith("hsl"):
            h = _number(parts[0])
            s = _number(parts[1], 1.0) if parts[1].endswith("%") else _number(parts[1]) / 100
            light = _number(parts[2], 1.0) if parts[2].endswith("%") else _number(parts[2]) / 100
            rgb = _hsl_to_rgb(h, s, light)
        elif name == "oklch":
            L = _number(parts[0], 1.0)
            if not parts[0].endswith("%") and L > 1.0:
                L /= 100.0
            C = _number(parts[1], 0.4)
            H = _number(parts[2])
            rgb = oklch_to_srgb(L, C, H)
        else:
            L = _number(parts[0], 1.0)
            if not parts[0].endswith("%") and L > 1.0:
                L /= 100.0
            rgb = _oklab_to_srgb(L, _number(parts[1], 0.4), _number(parts[2], 0.4))
        a = _alpha(alpha)
    except ValueError:
        return None
    r, g, b = _clamp_rgb(rgb)
    return (r, g, b, a)


def composite(fg, bg):
    """Blend an (r, g, b, a) color over an opaque (r, g, b) background."""
    a = fg[3] if len(fg) > 3 else 1.0
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3))


def relative_luminance(rgb):
    """WCAG 2 relative luminance of gamma-encoded sRGB."""
    r, g, b = (_decode(max(0.0, min(1.0, c))) for c in rgb[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast_ratio(a, b):
    """WCAG 2 contrast ratio (1..21) between two opaque sRGB colors."""
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)
