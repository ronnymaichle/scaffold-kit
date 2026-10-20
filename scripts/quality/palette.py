#!/usr/bin/env python3
"""Palette and theme generator (scaffold-kit).

  scale HEX [--name NAME]
      Print an 11-step OKLCH scale (50-950) for one color as CSS variables.
  theme --primary HEX [--highlight HEX] [--out FILE] [--no-tailwind]
      Generate the full light and dark token theme (shadcn-compatible names plus
      success, warning, info, subtle and text roles). Every default contrast pair
      passes WCAG AA; the result is verified before it is written.
  preview FILE [FILE ...] [--out FILE]
      Write one HTML page that compares theme proposals: palette swatches, sample
      components in light and dark, and the contrast results. Write previews
      outside the project; they are for choosing, not for committing.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import colors  # noqa: E402
import common  # noqa: E402
import design_tokens  # noqa: E402

__all__ = ["main", "build_scale", "build_theme", "build_preview"]

_STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950]
_CHROMA_L = [0.971, 0.936, 0.885, 0.808, 0.707, 0.630, 0.560, 0.495, 0.432, 0.385, 0.282]
_CHROMA_F = [0.12, 0.25, 0.45, 0.70, 0.92, 1.00, 1.00, 0.92, 0.80, 0.68, 0.50]
_NEUTRAL_L = [0.985, 0.967, 0.922, 0.870, 0.708, 0.556, 0.439, 0.371, 0.269, 0.205, 0.145]
_SEMANTIC = {
    "destructive": (27.0, 0.21),
    "success": (150.0, 0.16),
    "warning": (70.0, 0.17),
    "info": (250.0, 0.16),
}
_MARGIN = 0.12  # safety margin over the WCAG minimum for derived colors
_TEXT, _UI = 4.5 + _MARGIN, 3.0 + _MARGIN
_BRAND_TEXT = 4.5 + 0.03  # the exact brand color only needs to survive rounding


def _hex_to_lch(value):
    parsed = colors.parse_color(value)
    if parsed is None:
        raise SystemExit(f"error: not a color: {value}")
    return colors.srgb_to_oklch(*parsed[:3])


def _chroma_factor(L):
    pts = list(zip(_CHROMA_L, _CHROMA_F))
    if L >= pts[0][0]:
        return pts[0][1]
    if L <= pts[-1][0]:
        return pts[-1][1]
    for (l1, f1), (l2, f2) in zip(pts, pts[1:]):
        if l2 <= L <= l1:
            t = (L - l2) / (l1 - l2)
            return f2 + t * (f1 - f2)
    return 1.0


def _family(hue, peak):
    def color_at(L):
        return colors.gamut_map(L, peak * _chroma_factor(L), hue)
    return color_at


def _neutral(hue, tint):
    def color_at(L):
        return colors.gamut_map(L, tint, hue)
    return color_at


def _rgb(lch):
    return tuple(max(0.0, min(1.0, c)) for c in colors.oklch_to_srgb(*colors.gamut_map(*lch)))


def _cr(a, b):
    return colors.contrast_ratio(_rgb(a), _rgb(b))


def _passes(color_at, L, against, target):
    c = color_at(L)
    return all(_cr(c, other) >= target for other in against)


def _max_L(color_at, against, target, lo=0.0, hi=1.0):
    """Lightest L in [lo, hi] that still passes (for colors darker than `against`)."""
    if not _passes(color_at, lo, against, target):
        return None
    if _passes(color_at, hi, against, target):
        return hi
    for _ in range(40):
        mid = (lo + hi) / 2
        if _passes(color_at, mid, against, target):
            lo = mid
        else:
            hi = mid
    return lo


def _min_L(color_at, against, target, lo=0.0, hi=1.0):
    """Darkest L in [lo, hi] that still passes (for colors lighter than `against`)."""
    if not _passes(color_at, hi, against, target):
        return None
    if _passes(color_at, lo, against, target):
        return lo
    for _ in range(40):
        mid = (lo + hi) / 2
        if _passes(color_at, mid, against, target):
            hi = mid
        else:
            lo = mid
    return hi


def build_scale(hue, peak, brand=None, lightness=None):
    """Return [(step, (L, C, H))] for steps 50-950; brand replaces the nearest step."""
    lightness = lightness or _CHROMA_L
    color_at = _family(hue, peak)
    scale = [(step, color_at(L)) for step, L in zip(_STEPS, lightness)]
    if brand is not None:
        nearest = min(range(len(scale)), key=lambda i: abs(scale[i][1][0] - brand[0]))
        scale[nearest] = (scale[nearest][0], brand)
    return scale


def _fmt(lch, alpha=None):
    return colors.format_oklch(*colors.gamut_map(*lch), alpha=alpha)


def _light_solid(color_at, hue, light_fg, dark_fg):
    """Solid fill for light mode: white text when it works, dark text for yellows."""
    if not 55 <= hue <= 115:
        L = _max_L(color_at, [light_fg], _TEXT, 0.15, 0.95)
        if L is not None and L >= 0.40:
            return color_at(min(L, 0.68)), light_fg
    L = _min_L(color_at, [dark_fg], _TEXT, 0.3, 0.98)
    return color_at(max(L or 0.8, 0.78)), dark_fg


def _dark_solid(color_at, light_fg, dark_fg, floor=0.70):
    L = _min_L(color_at, [dark_fg], _TEXT, 0.3, 0.98)
    if L is None:
        L = _max_L(color_at, [light_fg], _TEXT, 0.1, 0.9) or 0.5
        return color_at(L), light_fg
    return color_at(min(max(L, floor), 0.88)), dark_fg


def build_theme(primary, highlight=None, tailwind=True):
    """Return (css_text, notes) for a theme built around the given hex colors."""
    notes = []
    brand = _hex_to_lch(primary)
    hue = brand[2]
    tint = 0.0 if brand[1] < 0.02 else max(0.003, min(0.018, brand[1] * 0.12))
    neutral = _neutral(hue, tint)
    white_ish = colors.gamut_map(0.99, min(tint, 0.004), hue)
    black_ish = neutral(0.145)
    peak = min(max(brand[1], 0.02), 0.32)
    primary_family = _family(hue, peak)

    scales = {"primary": build_scale(hue, peak, brand)}
    scales["neutral"] = [(s, neutral(L)) for s, L in zip(_STEPS, _NEUTRAL_L)]
    for role, (h, c) in _SEMANTIC.items():
        scales[role] = build_scale(h, c)
    hl = None
    if highlight:
        hl = _hex_to_lch(highlight)
        scales["highlight"] = build_scale(hl[2], min(max(hl[1], 0.02), 0.32), hl)

    light, dark = {}, {}

    # light surfaces and text
    light["background"] = neutral(0.985)
    light["card"] = light["popover"] = (1.0, 0.0, 0.0)
    light["foreground"] = light["card-foreground"] = light["popover-foreground"] = black_ish
    light["secondary"] = light["muted"] = light["accent"] = neutral(0.967)
    light["secondary-foreground"] = light["accent-foreground"] = neutral(0.205)
    surfaces = [light["background"], light["card"], light["muted"]]
    light["muted-foreground"] = neutral(_max_L(neutral, surfaces, _TEXT, 0.0, 0.9))
    light["border"] = neutral(0.922)
    light["input"] = neutral(_max_L(neutral, surfaces[:2], _UI, 0.0, 0.95))

    # light primary: keep the exact brand color when it can carry text
    brand_rgb_ok = None
    for fg in (white_ish, black_ish):
        if _cr(brand, fg) >= _BRAND_TEXT:
            brand_rgb_ok = fg
            break
    if brand_rgb_ok is not None and _cr(brand, light["background"]) >= 1.5:
        light["primary"], light["primary-foreground"] = brand, brand_rgb_ok
    else:
        if brand_rgb_ok is not None:
            notes.append(("primary", primary, "primary is too close to the background to read as a button; derived a darker shade"))
        else:
            notes.append(("primary", primary, "primary cannot carry readable text as is; derived the nearest shade that can"))
        light["primary"], light["primary-foreground"] = _light_solid(primary_family, hue, white_ish, black_ish)
        if _cr(light["primary"], light["background"]) < 1.5:
            light["primary"], light["primary-foreground"] = neutral(0.205), white_ish
            notes.append(("primary", primary, "primary falls back to near-black; use the brand color as highlight instead"))
    ring_family = primary_family
    if _cr(light["primary"], light["background"]) >= _UI and _cr(light["primary"], light["card"]) >= _UI:
        light["ring"] = light["primary"]
    else:
        light["ring"] = ring_family(_max_L(ring_family, surfaces[:2], _UI, 0.1, 0.9) or 0.5)

    # dark surfaces and text
    dark["background"] = neutral(0.16)
    dark["card"] = neutral(0.205)
    dark["popover"] = neutral(0.25)
    dark["foreground"] = dark["card-foreground"] = dark["popover-foreground"] = neutral(0.97)
    dark["secondary"] = dark["muted"] = dark["accent"] = neutral(0.27)
    dark["secondary-foreground"] = dark["accent-foreground"] = neutral(0.97)
    dsurfaces = [dark["background"], dark["card"], dark["popover"], dark["muted"]]
    dark["muted-foreground"] = neutral(_min_L(neutral, dsurfaces, _TEXT, 0.3, 1.0))
    dark["border"] = neutral(0.32)
    dark["input"] = neutral(_min_L(neutral, dsurfaces[:2], _UI, 0.2, 1.0))
    dark_primary_family = _family(hue, peak * 0.9)
    dark["primary"], dark["primary-foreground"] = _dark_solid(
        dark_primary_family, white_ish, black_ish, floor=max(0.66, min(brand[0] + 0.06, 0.8))
    )
    if _cr(dark["primary"], dark["background"]) >= _UI and _cr(dark["primary"], dark["card"]) >= _UI:
        dark["ring"] = dark["primary"]
    else:
        dark["ring"] = dark_primary_family(_min_L(dark_primary_family, dsurfaces[:2], _UI, 0.3, 1.0) or 0.7)

    if hl is not None:
        hl_family = _family(hl[2], min(max(hl[1], 0.02), 0.32))
        fg = next((f for f in (white_ish, black_ish) if _cr(hl, f) >= _BRAND_TEXT), None)
        if fg is not None:
            light["highlight"], light["highlight-foreground"] = hl, fg
        else:
            notes.append(("highlight", highlight, "highlight cannot carry readable text as is; derived the nearest shade that can"))
            light["highlight"], light["highlight-foreground"] = _light_solid(hl_family, hl[2], white_ish, black_ish)
        dark["highlight"], dark["highlight-foreground"] = _dark_solid(
            _family(hl[2], min(max(hl[1], 0.02), 0.32) * 0.9), white_ish, black_ish
        )

    # semantic roles: solid fill + foreground, subtle background, readable text
    for role, (h, c) in _SEMANTIC.items():
        fam = _family(h, c)
        light[role], light[f"{role}-foreground"] = _light_solid(fam, h, white_ish, black_ish)
        light[f"{role}-subtle"] = fam(0.965)
        light[f"{role}-text"] = fam(
            _max_L(fam, [light["background"], light["card"], light[f"{role}-subtle"]], _TEXT, 0.1, 0.9) or 0.45
        )
        dark[role], dark[f"{role}-foreground"] = _dark_solid(_family(h, c * 0.95), white_ish, black_ish)
        dark[f"{role}-subtle"] = colors.gamut_map(0.26, c * 0.32, h)
        dark[f"{role}-text"] = fam(
            _min_L(fam, [dark["background"], dark["card"], dark["popover"], dark[f"{role}-subtle"]], _TEXT, 0.3, 1.0)
            or 0.8
        )

    exact = {brand: _norm_hex(primary)}
    if hl is not None:
        exact[hl] = _norm_hex(highlight)
    css = _render_css(primary, highlight, scales, light, dark, tailwind, exact)
    themes = design_tokens.parse_theme_text(css)
    merged_dark = dict(themes["base"])
    merged_dark.update(themes["dark"])
    results = design_tokens.evaluate_contrast({"light": themes["base"], "dark": merged_dark})
    failures = [r for r in results if r["status"] in ("fail", "missing")]
    if failures:
        detail = "; ".join(f"{r['theme']} {r['fg']} on {r['bg']}: {r['ratio']}" for r in failures)
        raise RuntimeError(f"generated theme failed contrast checks: {detail}")
    named = []
    for role, requested, message in notes:
        derived = colors.to_hex(colors.parse_color(themes["base"][role])[:3])
        named.append(f"{message} ({_norm_hex(requested)} becomes {derived} in light mode)")
    return css, named


_ROLE_ORDER = [
    "background", "foreground", "card", "card-foreground", "popover", "popover-foreground",
    "primary", "primary-foreground", "secondary", "secondary-foreground", "muted",
    "muted-foreground", "accent", "accent-foreground", "highlight", "highlight-foreground",
    "destructive", "destructive-foreground", "destructive-subtle", "destructive-text",
    "success", "success-foreground", "success-subtle", "success-text",
    "warning", "warning-foreground", "warning-subtle", "warning-text",
    "info", "info-foreground", "info-subtle", "info-text",
    "border", "input", "ring",
]


def _norm_hex(value):
    parsed = colors.parse_color(value)
    return colors.to_hex(parsed[:3]) if parsed else value


def _render_css(primary, highlight, scales, light, dark, tailwind, exact=None):
    exact = exact or {}

    def value(lch):
        return exact.get(lch) or _fmt(lch)

    inputs = f"--primary {primary}" + (f" --highlight {highlight}" if highlight else "")
    lines = [
        f"/* Theme generated by scripts/quality/palette.py (scaffold-kit {common.KIT_VERSION}).",
        f"   Inputs: {inputs}",
        "   Regenerate instead of editing by hand; verify with",
        "   python3 scripts/quality/design_tokens.py contrast",
        "   Components use the semantic tokens (bg-background, text-muted-foreground, ...),",
        "   never the --palette-* scales or color literals. */",
        "",
        ":root {",
        "  /* palette: generated scales, inputs for the tokens below */",
    ]
    for name, scale in scales.items():
        for step, lch in scale:
            hexv = colors.to_hex(_rgb(lch))
            lines.append(f"  --palette-{name}-{step}: {value(lch)}; /* {hexv} */")
    lines += ["", "  /* tokens: light theme */", "  --radius: 0.625rem;"]
    for role in _ROLE_ORDER:
        if role in light:
            lines.append(f"  --{role}: {value(light[role])};")
    lines.append(f"  --overlay: {_fmt(_SEMANTIC_OVERLAY_LIGHT, 0.5)};")
    lines += ["}", "", ".dark {", "  /* tokens: dark theme */"]
    for role in _ROLE_ORDER:
        if role in dark:
            lines.append(f"  --{role}: {value(dark[role])};")
    lines.append(f"  --overlay: {_fmt((0.0, 0.0, 0.0), 0.6)};")
    lines.append("}")
    if tailwind:
        lines += ["", "@theme inline {"]
        for role in _ROLE_ORDER + ["overlay"]:
            if role in light or role == "overlay":
                lines.append(f"  --color-{role}: var(--{role});")
        lines += [
            "  --radius-sm: calc(var(--radius) - 4px);",
            "  --radius-md: calc(var(--radius) - 2px);",
            "  --radius-lg: var(--radius);",
            "  --radius-xl: calc(var(--radius) + 4px);",
            "}",
        ]
    return "\n".join(lines) + "\n"


_SEMANTIC_OVERLAY_LIGHT = (0.145, 0.0, 0.0)


# ------------------------------------------------------------------- preview

_PREVIEW_CSS = """
body{margin:0;padding:24px;font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;background:#ececee;color:#18181b}
h1{font-size:20px;margin:0 0 4px}.lead{margin:0 0 24px;color:#52525b;max-width:70ch}
.proposal{margin:0 0 40px}.proposal>h2{font-size:17px;margin:0 0 12px}
.modes{display:grid;grid-template-columns:repeat(auto-fit,minmax(440px,1fr));gap:16px}
.ui{background:var(--background);color:var(--foreground);border:1px solid var(--border);border-radius:14px;padding:20px;display:grid;gap:18px}
.label{font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--muted-foreground)}
.scale{display:grid;grid-template-columns:72px repeat(11,1fr);gap:3px;align-items:center;font-size:11px;color:var(--muted-foreground)}
.sw{height:22px;border-radius:4px}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.btn{font:inherit;font-size:14px;font-weight:500;padding:8px 14px;border-radius:calc(var(--radius,.625rem) - 2px);border:1px solid transparent;cursor:pointer}
.btn-primary{background:var(--primary);color:var(--primary-foreground)}
.btn-secondary{background:var(--secondary);color:var(--secondary-foreground)}
.btn-outline{background:var(--background);color:var(--foreground);border-color:var(--input)}
.btn-ghost{background:transparent;color:var(--foreground)}.btn-ghost:hover{background:var(--accent);color:var(--accent-foreground)}
.btn-destructive{background:var(--destructive);color:var(--destructive-foreground)}
.btn-highlight{background:var(--highlight);color:var(--highlight-foreground)}
.focus{outline:2px solid var(--ring);outline-offset:2px}
.card{background:var(--card);color:var(--card-foreground);border:1px solid var(--border);border-radius:var(--radius,.625rem);padding:16px;display:grid;gap:6px}
.card h3{margin:0;font-size:16px}.muted{color:var(--muted-foreground)}
.badge{display:inline-block;font-size:12px;padding:2px 8px;border-radius:999px;background:var(--secondary);color:var(--secondary-foreground)}
.field{display:grid;gap:6px;font-size:14px}.field label{font-weight:500}
.input{font:inherit;padding:8px 10px;border-radius:calc(var(--radius,.625rem) - 2px);border:1px solid var(--input);background:var(--background);color:var(--foreground)}
.input.invalid{border-color:var(--destructive)}.error{color:var(--destructive-text);font-size:13px}
.alert{border-radius:calc(var(--radius,.625rem) - 2px);padding:10px 12px;display:grid;grid-template-columns:20px 1fr;gap:4px 8px;font-size:14px}
.alert .icon{font-weight:700}.alert b{display:block}
.toast{background:var(--popover);color:var(--popover-foreground);border:1px solid var(--border);border-radius:var(--radius,.625rem);padding:10px 12px;display:grid;grid-template-columns:20px 1fr;gap:2px 8px;font-size:14px;box-shadow:0 6px 18px rgba(0,0,0,.12)}
.overlay{position:relative;height:72px;border-radius:10px;overflow:hidden;background:var(--card)}
.overlay::after{content:"";position:absolute;inset:0;background:var(--overlay)}
table{border-collapse:collapse;font-size:13px;margin-top:8px}td,th{padding:3px 10px;text-align:left;border-bottom:1px solid #d4d4d8}
.pass{color:#166534}.fail{color:#b91c1c;font-weight:600}
"""

_ROLE_ALERTS = [("info", "i", "Heads up", "Videos are processed in the background."),
                ("success", "✓", "Saved", "Your marker is live."),
                ("warning", "!", "Almost full", "You have used 90% of your storage."),
                ("destructive", "✕", "Upload failed", "The file is larger than 50 MB.")]


def _panel(idx, mode, env, scales):
    parts = [f'<div class="ui p{idx} {mode}">', f'<div class="label">{mode} theme</div>']
    if scales:
        parts.append('<div class="scale">')
        for name in scales:
            parts.append(f"<span>{html.escape(name)}</span>")
            for step in _STEPS:
                parts.append(f'<span class="sw" title="{name}-{step}" style="background:var(--palette-{name}-{step})"></span>')
        parts.append("</div>")
    parts.append('<div class="card"><h3>Lisbon viewpoints <span class="badge">12 photos</span></h3>'
                 '<p style="margin:0">Body text uses the foreground token on the card surface.</p>'
                 '<p class="muted" style="margin:0">Muted text: updated 3 hours ago by Ana.</p></div>')
    parts.append('<div class="row"><button class="btn btn-primary">Save marker</button>'
                 '<button class="btn btn-secondary">Preview</button>'
                 '<button class="btn btn-outline">Cancel</button>'
                 '<button class="btn btn-ghost">More</button>'
                 '<button class="btn btn-destructive">Delete</button>'
                 + ('<button class="btn btn-highlight">New</button>' if "highlight" in env else "")
                 + '<button class="btn btn-outline focus">Focused</button></div>')
    parts.append('<div class="row" style="align-items:start">'
                 '<div class="field" style="flex:1"><label>Title</label><input class="input" value="Sunset at Miradouro">'
                 '<span class="muted" style="font-size:13px">Shown on the map and in search.</span></div>'
                 '<div class="field" style="flex:1"><label>Email</label><input class="input invalid" value="ana@">'
                 '<span class="error">Enter a valid email address.</span></div></div>')
    for role, icon, title, text in _ROLE_ALERTS:
        parts.append(f'<div class="alert" style="background:var(--{role}-subtle)">'
                     f'<span class="icon" style="color:var(--{role}-text)">{icon}</span>'
                     f'<span><b style="color:var(--{role}-text)">{title}</b>{text}</span></div>')
    parts.append('<div class="toast"><span class="icon" style="color:var(--success-text)">✓</span>'
                 '<span>Marker saved</span></div>')
    parts.append('<div class="toast"><span class="icon" style="color:var(--destructive-text)">✕</span>'
                 '<span>Could not save the comment.<br><span class="muted">Error ref: 7f3a9c</span></span></div>')
    parts.append('<div class="overlay" title="modal overlay"></div>')
    parts.append("</div>")
    return "".join(parts)


def build_preview(paths, title="Theme proposals"):
    """Return HTML comparing the given theme files in light and dark."""
    scoped, sections = [], []
    for idx, path in enumerate(paths):
        themes = design_tokens.parse_theme_files([path])
        results = design_tokens.evaluate_contrast(themes)
        scale_names = []
        for name in themes["light"]:
            m = re.match(r"palette-(.+)-50$", name)
            if m:
                scale_names.append(m.group(1))
        for mode in ("light", "dark"):
            env = themes[mode]
            decls = []
            for name in env:
                value = design_tokens.resolve_value(env[name], env)
                if value is not None and not value.startswith("calc("):
                    decls.append(f"--{name}:{value}")
            scoped.append(f".p{idx}.{mode}{{{';'.join(decls)}}}")
        rows = "".join(
            f'<tr><td>{r["theme"]}</td><td>{html.escape(r["fg"])} on {html.escape(r["bg"])}</td>'
            f'<td>{r["ratio"] if r["ratio"] is not None else "—"}</td><td>{r["min"]}</td>'
            f'<td class="{"pass" if r["status"] == "pass" else "fail"}">{r["status"]}</td></tr>'
            for r in results if r["status"] != "skip"
        )
        failing = sum(1 for r in results if r["status"] in ("fail", "missing"))
        summary = "all pairs pass" if not failing else f"{failing} failing pair(s)"
        sections.append(
            f'<section class="proposal"><h2>Proposal {idx + 1}: {html.escape(Path(path).stem)} ({summary})</h2>'
            f'<div class="modes">{_panel(idx, "light", themes["light"], scale_names)}'
            f'{_panel(idx, "dark", themes["dark"], scale_names)}</div>'
            f"<details><summary>Contrast checks</summary><table><tr><th>Theme</th><th>Pair</th>"
            f"<th>Ratio</th><th>Needs</th><th>Result</th></tr>{rows}</table></details></section>"
        )
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{html.escape(title)}</title><style>{_PREVIEW_CSS}{''.join(scoped)}</style></head><body>"
        f"<h1>{html.escape(title)}</h1><p class=\"lead\">Each proposal shows the same components in the "
        "light and dark theme. Text needs a contrast ratio of at least 4.5:1; input borders and focus "
        "rings need 3:1 (WCAG 2.2 AA).</p>" + "".join(sections) + "</body></html>\n"
    )


def main(argv=None):
    """Command-line entry point; returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    sc = sub.add_parser("scale", help="print an OKLCH scale for one color")
    sc.add_argument("color")
    sc.add_argument("--name", default="brand")
    th = sub.add_parser("theme", help="generate a full light and dark token theme")
    th.add_argument("--primary", required=True, help="brand color, e.g. #2563eb")
    th.add_argument("--highlight", help="optional second brand color for small accents")
    th.add_argument("--out", help="write the CSS to this file instead of printing it")
    th.add_argument("--no-tailwind", action="store_true", help="omit the Tailwind v4 @theme block")
    pv = sub.add_parser("preview", help="write an HTML page comparing theme files")
    pv.add_argument("files", nargs="+")
    pv.add_argument("--out", default="theme-preview.html")
    pv.add_argument("--title", default="Theme proposals")
    args = parser.parse_args(argv)

    if args.command == "scale":
        L, C, H = _hex_to_lch(args.color)
        for step, lch in build_scale(H, min(max(C, 0.02), 0.32), (L, C, H)):
            print(f"--{args.name}-{step}: {_fmt(lch)}; /* {colors.to_hex(_rgb(lch))} */")
        return 0
    if args.command == "theme":
        css, notes = build_theme(args.primary, args.highlight, tailwind=not args.no_tailwind)
        for note in notes:
            print(f"note: {note}", file=sys.stderr)
        if args.out:
            out = Path(args.out)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(css, encoding="utf-8")
            print(f"wrote {out} (all default contrast pairs pass)")
        else:
            sys.stdout.write(css)
        return 0
    missing = [f for f in args.files if not Path(f).is_file()]
    if missing:
        print(f"error: not found: {', '.join(missing)}")
        return 2
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_preview(args.files, args.title), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
