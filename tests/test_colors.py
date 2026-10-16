import unittest

import helpers  # noqa: F401  (sets the import path)
import colors


class ColorTests(unittest.TestCase):
    def rgb(self, value):
        return colors.parse_color(value)[:3]

    def test_known_contrast_ratios(self):
        self.assertAlmostEqual(colors.contrast_ratio(self.rgb("#fff"), self.rgb("#000")), 21.0, places=2)
        self.assertAlmostEqual(colors.contrast_ratio(self.rgb("#777"), self.rgb("#fff")), 4.48, places=2)
        self.assertAlmostEqual(colors.contrast_ratio(self.rgb("#dc2626"), self.rgb("white")), 4.83, places=2)

    def test_parse_formats(self):
        self.assertEqual(colors.parse_color("rgb(255 0 0 / 50%)"), (1.0, 0.0, 0.0, 0.5))
        self.assertEqual(colors.parse_color("rgba(0, 0, 255, .5)"), (0.0, 0.0, 1.0, 0.5))
        self.assertEqual(colors.parse_color("hsl(120 100% 25%)")[:3], (0.0, 0.5, 0.0))
        self.assertEqual(colors.parse_color("#abcd")[3], 0xdd / 255)
        self.assertEqual(colors.parse_color("transparent")[3], 0.0)
        self.assertIsNone(colors.parse_color("var(--x)"))
        self.assertIsNone(colors.parse_color("currentColor"))

    def test_oklch_round_trip(self):
        for hexv in ("#3b82f6", "#16a34a", "#f59e0b", "#111827", "#ffffff"):
            L, C, H = colors.srgb_to_oklch(*self.rgb(hexv))
            self.assertEqual(colors.to_hex(colors.oklch_to_srgb(L, C, H)), hexv)
            self.assertEqual(colors.to_hex(colors.parse_color(colors.format_oklch(L, C, H))[:3]), hexv)

    def test_gamut_map_keeps_lightness_and_fits(self):
        L, C, H = colors.gamut_map(0.7, 0.4, 30)
        self.assertEqual(L, 0.7)
        self.assertTrue(colors.in_gamut(colors.oklch_to_srgb(L, C, H)))
        self.assertLess(C, 0.4)

    def test_composite(self):
        over_black = colors.composite(colors.parse_color("oklch(1 0 0 / 10%)"), (0.0, 0.0, 0.0))
        self.assertAlmostEqual(over_black[0], 0.1, places=3)

    def test_named_colors(self):
        self.assertEqual(len(colors.NAMED_COLORS), 148)
        self.assertEqual(colors.NAMED_COLORS["rebeccapurple"], "#663399")


if __name__ == "__main__":
    unittest.main()
