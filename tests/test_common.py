import json
import unittest

from helpers import KIT, TempProject

import common


class GlobTests(unittest.TestCase):
    def test_double_star_matches_zero_or_more_folders(self):
        self.assertTrue(common.glob_match("src/a.ts", "src/**/*.ts"))
        self.assertTrue(common.glob_match("src/a/b/c.ts", "src/**/*.ts"))
        self.assertFalse(common.glob_match("lib/a.ts", "src/**/*.ts"))

    def test_pattern_without_slash_matches_the_last_segment(self):
        self.assertTrue(common.glob_match("src/lib/markers.test.ts", "*.test.*"))
        self.assertFalse(common.glob_match("src/lib/markers.ts", "*.test.*"))

    def test_braces_and_folder_itself(self):
        self.assertTrue(common.glob_match("x.svelte", "*.{svelte,tsx}"))
        self.assertTrue(common.glob_match("src/lib/theme", "src/lib/theme/**"))
        self.assertTrue(common.glob_match("src/lib/theme/a.css", "src/lib/theme/**"))


class ExcludeTests(unittest.TestCase):
    def test_names_match_any_depth_and_slash_names_only_the_root(self):
        entries = ["node_modules", "/docs", "/build"]
        self.assertTrue(common.is_excluded("a/node_modules/b", entries))
        self.assertTrue(common.is_excluded("docs/guides", entries))
        self.assertFalse(common.is_excluded("src/docs", entries))
        self.assertFalse(common.is_excluded("src/lib/build", entries))

    def test_hidden_folders(self):
        self.assertTrue(common.is_excluded(".github/workflows", []))
        self.assertFalse(common.is_excluded(".github/workflows", [], hidden=False))


class ConfigTests(unittest.TestCase):
    def test_defaults_without_a_config_file(self):
        with TempProject() as p:
            cfg = common.load_config(p.root)
        self.assertEqual(cfg["folderDocs"]["docFile"], "CLAUDE.md")

    def test_exclude_lists_extend_and_other_keys_replace(self):
        with TempProject({"quality.config.json": json.dumps({
            "folderDocs": {"exclude": ["generated"], "codemapFile": None},
            "design": {"themeFiles": ["styles/theme.css"]},
        })}) as p:
            cfg = common.load_config(p.root)
        self.assertIn("generated", cfg["folderDocs"]["exclude"])
        self.assertIn("node_modules", cfg["folderDocs"]["exclude"])
        self.assertIsNone(cfg["folderDocs"]["codemapFile"])
        self.assertEqual(cfg["design"]["themeFiles"], ["styles/theme.css"])

    def test_invalid_json_exits(self):
        with TempProject({"quality.config.json": "{nope"}) as p:
            with self.assertRaises(SystemExit):
                common.load_config(p.root)


class JsStripTests(unittest.TestCase):
    def test_comments_and_strings_are_blanked_with_offsets_kept(self):
        src = 'const a = "// x"; // note\nconst b = `t ${ {k: 1}.k } u`; /* c */ export const z = 1'
        out = common.strip_js_comments_and_strings(src)
        self.assertEqual(len(out), len(src))
        self.assertNotIn("note", out)
        self.assertNotIn("// x", out)
        self.assertIn("{k: 1}.k", out)
        self.assertIn("export const z = 1", out)

    def test_keep_strings(self):
        out = common.strip_js_comments_and_strings("x = '#fff' // c", keep_strings=True)
        self.assertIn("#fff", out)
        self.assertNotIn("c", out.replace("const", ""))

    def test_script_blocks(self):
        blocks = common.extract_script_blocks('<script lang="ts">let a = 1;</script><p>x</p><script module>export const b = 2;</script>')
        self.assertEqual(len(blocks), 2)
        self.assertIn("module", blocks[1][0])


class VersionTests(unittest.TestCase):
    def test_kit_version_matches_version_file(self):
        self.assertEqual(common.KIT_VERSION, (KIT / "VERSION").read_text().strip())


if __name__ == "__main__":
    unittest.main()
