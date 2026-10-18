"""Consistency checks for the kit's own files."""
import json
import re
import unittest

from helpers import KIT

import common


class KitFileTests(unittest.TestCase):
    def test_version_file_matches_scripts(self):
        self.assertEqual((KIT / "VERSION").read_text(encoding="utf-8").strip(), common.KIT_VERSION)

    def test_references_name_the_docs_they_become(self):
        for path in sorted((KIT / "references").glob("*.md")):
            head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:4])
            with self.subTest(reference=path.name):
                self.assertTrue(head.startswith("# "))
                if path.name != "upgrade.md":
                    self.assertIn("Becomes", head)

    def test_root_template_stays_short_and_has_the_workflows(self):
        text = (KIT / "templates" / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertLess(len(text.splitlines()), 200, "leave room for project-specific lines (limit ~300)")
        for heading in ("## Feature workflow", "## Hotfix workflow", "## Release workflow"):
            self.assertIn(heading, text)
        steps = re.findall(r"^(\d+)\. ", text.split("## Feature workflow")[1].split("## Hotfix")[0], re.M)
        self.assertEqual(steps, [str(n) for n in range(1, 12)])

    def test_links_to_project_docs_are_consistent(self):
        known = {
            "docs/ARCHITECTURE.md", "docs/DATABASE.md", "docs/security/THREAT-MODEL.md",
            "docs/security/findings.md", "docs/PRIVACY.md", "docs/DEPLOYMENT.md", "docs/SCALING.md",
            "docs/OPERATIONS.md", "docs/DESIGN.md", "docs/SEO.md", "docs/ANALYTICS.md",
            "docs/LOGGING.md", "docs/TESTING.md", "docs/SOURCES.md", "docs/CODEMAP.md", "docs/LAUNCH-CHECKLIST.md",
            "docs/SCAFFOLD-PROGRESS.md", "docs/UPGRADE-PLAN.md", "docs/AGENT-TEAM.md",
        }
        files = list((KIT / "references").glob("*.md")) + list((KIT / "templates").rglob("*.md"))
        for path in files:
            for ref in re.findall(r"docs/[\w/.-]+\.md", path.read_text(encoding="utf-8")):
                if ref.startswith(("docs/decisions/", "docs/incidents/")):
                    continue  # patterns such as docs/decisions/NNNN-short-title.md
                with self.subTest(file=path.name, ref=ref):
                    self.assertIn(ref, known)

    def test_quality_config_template_is_valid(self):
        config = json.loads((KIT / "templates" / "quality.config.json").read_text(encoding="utf-8"))
        for section in config:
            self.assertIn(section, common._DEFAULTS)
            for key in config[section]:
                self.assertIn(key, common._DEFAULTS[section])

    def test_hook_template_runs_every_quality_script(self):
        text = (KIT / "templates" / "lefthook.yml").read_text(encoding="utf-8")
        for command in ("folder_docs.py staged", "debug_leftovers.py --staged", "design_tokens.py literals --staged", "sources.py check"):
            self.assertIn(command, text)


if __name__ == "__main__":
    unittest.main()
