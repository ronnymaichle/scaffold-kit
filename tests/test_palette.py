import unittest

from helpers import TempProject, run_main

import colors
import design_tokens
import palette

BRANDS = [
    "#2563eb", "#3b82f6", "#facc15", "#16a34a", "#dc2626", "#7c3aed", "#111111", "#ffffff",
    "#f97316", "#0d9488", "#ec4899", "#808080", "#00ffff", "#a3e635", "#1e3a8a", "#fde68a",
]


def _light_hex(css, role):
    value = design_tokens.parse_theme_text(css)["base"][role]
    return colors.to_hex(colors.parse_color(value)[:3])


class ThemeTests(unittest.TestCase):
    def test_every_brand_produces_a_passing_theme(self):
        for brand in BRANDS:
            with self.subTest(brand=brand):
                css, _notes = palette.build_theme(brand, highlight="#f59e0b")
                parsed = design_tokens.parse_theme_text(css)
                dark = dict(parsed["base"])
                dark.update(parsed["dark"])
                results = design_tokens.evaluate_contrast({"light": parsed["base"], "dark": dark})
                bad = [r for r in results if r["status"] in ("fail", "missing")]
                self.assertEqual(bad, [])
                for role in ("success", "warning", "info", "destructive"):
                    self.assertIn(f"--{role}-subtle", css)
                    self.assertIn(f"--{role}-text", css)
                self.assertIn("@theme inline", css)

    def test_readable_brand_color_is_kept_exactly(self):
        css, notes = palette.build_theme("#2563eb")
        parsed = design_tokens.parse_theme_text(css)
        primary = colors.parse_color(parsed["base"]["primary"])[:3]
        self.assertEqual(colors.to_hex(primary), "#2563eb")
        self.assertEqual(notes, [])

    def test_unreadable_brand_gets_a_note(self):
        _css, notes = palette.build_theme("#facc15")
        self.assertTrue(notes)

    def test_note_names_the_derived_shade(self):
        css, notes = palette.build_theme("#facc15")
        derived = _light_hex(css, "primary")
        self.assertNotEqual(derived, "#facc15")
        self.assertTrue(any("#facc15" in n and derived in n for n in notes), notes)

    def test_unreadable_highlight_gets_a_note_naming_the_derived_shade(self):
        css, notes = palette.build_theme("#2563eb", highlight="#b8603a")
        derived = _light_hex(css, "highlight")
        self.assertNotEqual(derived, "#b8603a")
        self.assertTrue(any(n.startswith("highlight") and "#b8603a" in n and derived in n for n in notes), notes)

    def test_readable_highlight_is_kept_without_a_note(self):
        css, notes = palette.build_theme("#2563eb", highlight="#9a3412")
        self.assertEqual(_light_hex(css, "highlight"), "#9a3412")
        self.assertEqual(notes, [])

    def test_scale_has_eleven_descending_steps(self):
        scale = palette.build_scale(260.0, 0.2)
        self.assertEqual([s for s, _ in scale], [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950])
        lightness = [lch[0] for _, lch in scale]
        self.assertEqual(lightness, sorted(lightness, reverse=True))

    def test_no_tailwind_flag(self):
        css, _ = palette.build_theme("#2563eb", tailwind=False)
        self.assertNotIn("@theme", css)


class PreviewTests(unittest.TestCase):
    def test_preview_shows_each_proposal_in_both_themes(self):
        with TempProject() as p:
            run_main(palette.main, ["theme", "--primary", "#2563eb", "--out", str(p.root / "calm-blue.css")])
            run_main(palette.main, ["theme", "--primary", "#0d9488", "--out", str(p.root / "<teal>.css")])
            html = palette.build_preview([p.root / "calm-blue.css", p.root / "<teal>.css"])
        self.assertIn("Proposal 1: calm-blue (all pairs pass)", html)
        self.assertIn("Proposal 2: &lt;teal&gt;", html)
        self.assertEqual(html.count('<div class="label">light theme</div>'), 2)
        self.assertEqual(html.count('<div class="label">dark theme</div>'), 2)
        self.assertIn(".p1.dark{", html)

    def test_cli_rejects_missing_files(self):
        code, out = run_main(palette.main, ["preview", "/nope/theme.css"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
