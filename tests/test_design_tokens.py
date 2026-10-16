import json
import unittest

from helpers import TempProject, run_main

import design_tokens


def literals(name, text):
    return [lit for _line, lit in design_tokens._find_literals(name, text)]


class LiteralTests(unittest.TestCase):
    def test_markup_literals(self):
        text = (
            '<div class="bg-[#ff0000] text-white hover:bg-red-500/50 bg-primary text-muted-foreground">\n'
            '<a href="#add">x</a> <svg><path fill="#fff"/><path fill="currentColor"/>'
            '<use href="#abc"/><rect fill="url(#bad)"/></svg>\n'
            '<p style="color: red; border: 1px solid var(--border)">x</p>\n'
            "<!-- #123456 in a comment -->\n"
        )
        found = literals("A.svelte", text)
        for expected in ("#ff0000", "text-white", "bg-red-500", "#fff", "red"):
            self.assertIn(expected, found)
        for not_expected in ("#add", "#abc", "#bad", "#123456", "bg-primary"):
            self.assertNotIn(not_expected, found)

    def test_style_blocks_and_css_files(self):
        svelte = "<style>\n  .x { color: oklch(0.5 0.1 200); background: var(--card); }\n</style>"
        self.assertEqual(literals("A.svelte", svelte), ["oklch(...)"])
        css = "#add { color: var(--foreground); }\n.btn { @apply bg-blue-600; border-color: black; }\n"
        found = literals("a.css", css)
        self.assertIn("bg-blue-600", found)
        self.assertIn("black", found)
        self.assertNotIn("#add", found)

    def test_jsx_inline_styles_and_ignore_comment(self):
        tsx = (
            "export const A = () => <div style={{ color: 'red', backgroundColor: '#000000' }} />;\n"
            "const B = '#00ff00'; // design-check-ignore: brand color for the OG image\n"
        )
        found = literals("A.tsx", tsx)
        self.assertIn("red", found)
        self.assertIn("#000000", found)
        self.assertNotIn("#00ff00", found)

    def test_cli_skips_theme_files(self):
        files = {
            "src/app.css": ":root { --background: oklch(1 0 0); --primary: #2563eb; }",
            "src/lib/Button.svelte": '<button class="bg-primary text-primary-foreground">ok</button>',
        }
        with TempProject(files) as p:
            code, out = run_main(design_tokens.main, ["--root", str(p.root), "literals"])
            self.assertEqual(code, 0, out)
            p.write("src/lib/Bad.svelte", '<p class="text-gray-500">x</p>')
            code, out = run_main(design_tokens.main, ["--root", str(p.root), "literals"])
            self.assertEqual(code, 1)
            self.assertIn("src/lib/Bad.svelte:1", out)


THEME = """
@import "tailwindcss";
@custom-variant dark (&:is(.dark *));
:root {
  --background: oklch(0.985 0 0);
  --foreground: oklch(0.145 0 0);
  --primary: #2563eb;
  --primary-foreground: oklch(0.99 0 0);
  --muted-foreground: oklch(0.45 0 0);
  --ring: var(--primary);
  --input: oklch(0.6 0 0);
  --border: oklch(0.922 0 0);
}
.dark {
  --background: oklch(0.16 0 0);
  --foreground: oklch(0.97 0 0);
  --primary: oklch(0.7 0.15 262);
  --primary-foreground: oklch(0.145 0 0);
  --muted-foreground: oklch(0.7 0 0);
  --input: oklch(1 0 0 / 15%);
}
@theme inline {
  --color-background: var(--background);
}
"""


class ContrastTests(unittest.TestCase):
    def test_parse_scopes_and_resolve(self):
        parsed = design_tokens.parse_theme_text(THEME)
        self.assertEqual(parsed["base"]["primary"], "#2563eb")
        self.assertEqual(parsed["dark"]["input"], "oklch(1 0 0 / 15%)")
        env = dict(parsed["base"])
        self.assertEqual(design_tokens.resolve_value("var(--ring)", env), "#2563eb")
        self.assertEqual(design_tokens.resolve_value("var(--nope, var(--border))", env), "oklch(0.922 0 0)")
        self.assertIsNone(design_tokens.resolve_value("var(--nope)", env))

    def test_media_query_dark_scope(self):
        css = ":root{--background:#fff;--foreground:#111}@media (prefers-color-scheme: dark){:root{--background:#000}}"
        parsed = design_tokens.parse_theme_text(css)
        self.assertEqual(parsed["dark"]["background"], "#000")

    def test_cli_reports_failing_pairs(self):
        with TempProject({"src/app.css": THEME}) as p:
            code, out = run_main(design_tokens.main, ["--root", str(p.root), "contrast"])
        self.assertEqual(code, 1)
        self.assertIn("dark: input on background", out)
        self.assertNotIn("light: input on background", out)
        self.assertNotIn("foreground on background is", out)

    def test_json_output(self):
        with TempProject({"src/app.css": THEME}) as p:
            code, out = run_main(design_tokens.main, ["--root", str(p.root), "contrast", "--json"])
        data = json.loads(out)
        statuses = {(r["theme"], r["fg"], r["bg"]): r["status"] for r in data["results"]}
        self.assertEqual(statuses[("light", "foreground", "background")], "pass")
        self.assertEqual(statuses[("dark", "input", "background")], "fail")
        self.assertEqual(code, 1)

    def test_configured_pairs_extend_and_override_defaults(self):
        config = json.dumps({"design": {"contrastPairs": [
            {"fg": "sidebar-foreground", "bg": "sidebar", "required": True},
            {"fg": "input", "bg": "background", "min": 1.0},
        ]}})
        with TempProject({"src/app.css": THEME, "quality.config.json": config}) as p:
            code, out = run_main(design_tokens.main, ["--root", str(p.root), "contrast", "--json"])
        data = json.loads(out)
        statuses = {(r["theme"], r["fg"], r["bg"]): r["status"] for r in data["results"]}
        self.assertEqual(statuses[("light", "foreground", "background")], "pass")
        self.assertEqual(statuses[("light", "sidebar-foreground", "sidebar")], "missing")
        self.assertEqual(statuses[("dark", "input", "background")], "pass")
        self.assertEqual(code, 1)

    def test_missing_theme_file(self):
        with TempProject({"src/x.ts": ""}) as p:
            code, out = run_main(design_tokens.main, ["--root", str(p.root), "contrast"])
        self.assertEqual(code, 1)
        self.assertIn("no theme file found", out)


if __name__ == "__main__":
    unittest.main()
