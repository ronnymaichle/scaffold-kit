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

    def test_scaffold_progress_creates_every_doc_a_reference_becomes(self):
        progress = (KIT / "templates" / "SCAFFOLD-PROGRESS.md").read_text(encoding="utf-8")
        for path in sorted((KIT / "references").glob("*.md")):
            if path.name == "upgrade.md":
                continue
            match = re.search(r"Becomes(.*?)(?:\.\s|\.$)", path.read_text(encoding="utf-8"), re.S)
            self.assertIsNotNone(match, path.name)
            for doc in re.findall(r"`(docs/[\w/.-]+\.md)`", match.group(1)):
                with self.subTest(reference=path.name, doc=doc):
                    self.assertTrue(f"`{doc}`" in progress, f"{doc} is in no scaffold checkpoint, so a new project never gets it")

    def test_scaffold_progress_creates_the_doc_templates(self):
        progress = (KIT / "templates" / "SCAFFOLD-PROGRESS.md").read_text(encoding="utf-8")
        for name in ("LAUNCH-CHECKLIST.md", "ROADMAP.md", "AGENT-METRICS.md"):
            with self.subTest(template=name):
                self.assertTrue((KIT / "templates" / name).is_file())
                self.assertIn(f"`docs/{name}`", progress)

    def test_roadmap_rows_link_to_their_prs(self):
        roadmap = (KIT / "templates" / "ROADMAP.md").read_text(encoding="utf-8")
        self.assertIn("| ID | Feature: what a user can do afterwards | Depends on | Status |", roadmap)
        self.assertRegex(roadmap, r"\n\| R1 \| \{\{FEATURES:[^{}]*\}\} \|")
        self.assertIn("done (#14)", roadmap)
        pr_template = (KIT / "templates" / "github" / "pull_request_template.md").read_text(encoding="utf-8")
        self.assertIn("\nRoadmap: ", pr_template)

    def test_root_template_stays_short_and_has_the_workflows(self):
        text = (KIT / "templates" / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertLess(len(text.splitlines()), 200, "leave room for project-specific lines (limit ~300)")
        for heading in ("## Feature workflow", "## Hotfix workflow", "## Release workflow"):
            self.assertIn(heading, text)
        steps = re.findall(r"^(\d+)\. ", text.split("## Feature workflow")[1].split("## Hotfix")[0], re.M)
        self.assertEqual(steps, [str(n) for n in range(1, 12)])

    def test_links_to_project_docs_are_consistent(self):
        known = {
            "docs/ARCHITECTURE.md", "docs/DATABASE.md", "docs/security/THREAT-MODEL.md", "docs/security/SAFEGUARDS.md",
            "docs/security/findings.md", "docs/PRIVACY.md", "docs/DEPLOYMENT.md", "docs/SCALING.md",
            "docs/OPERATIONS.md", "docs/DESIGN.md", "docs/SEO.md", "docs/ANALYTICS.md",
            "docs/LOGGING.md", "docs/TESTING.md", "docs/SOURCES.md", "docs/CODEMAP.md", "docs/LAUNCH-CHECKLIST.md",
            "docs/SCAFFOLD-PROGRESS.md", "docs/UPGRADE-PLAN.md", "docs/AGENT-TEAM.md", "docs/ROADMAP.md",
            "docs/AGENT-METRICS.md",
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

    def test_plan_preview_template_pins_its_scripts(self):
        text = (KIT / "templates" / "plan-preview.html").read_text(encoding="utf-8")
        for section in ("architecture", "data", "actions", "look", "screens"):
            self.assertIn(f'<section id="{section}">', text)
        urls = re.findall(r"https://cdn\.jsdelivr\.net/npm/[^\"'\s>]+", text)
        self.assertTrue(urls, "the diagrams need a pinned Mermaid build")
        for url in urls:
            with self.subTest(url=url):
                self.assertRegex(url, r"/npm/(@[\w.-]+/)?[\w.-]+@\d+\.\d+\.\d+/", "pin an exact version")
        for placeholder in re.findall(r"\{\{[^{}]*\}\}", text):
            with self.subTest(placeholder=placeholder):
                self.assertRegex(placeholder, r"^\{\{(\.\.\.|[A-Z_]+(: [^{}]+)?)\}\}$")

    def test_plan_preview_template_fits_three_proposals_and_wide_diagrams(self):
        text = (KIT / "templates" / "plan-preview.html").read_text(encoding="utf-8")
        for theme in ("a", "b", "c"):
            self.assertIn(f'<option value="themes/{theme}.css">', text)
        self.assertIn("useMaxWidth: false", text, "wide diagrams scroll instead of shrinking")
        self.assertIn("main > * { min-width: 0; }", text, "and they scroll in their box, not the page")


if __name__ == "__main__":
    unittest.main()
