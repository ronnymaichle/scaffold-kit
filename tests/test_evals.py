"""The skill's eval cases stay complete, so the dry runs of its planning step stay repeatable."""
import re
import unittest

from helpers import KIT

EVALS = KIT / "evals"


def cases():
    return sorted(p for p in EVALS.glob("*.md") if p.name != "README.md")


def section(text, heading):
    """The body under an exact level-2 heading, up to the next one."""
    parts = re.split(rf"^{re.escape(heading)}$", text, flags=re.M)
    return parts[1].split("\n## ")[0] if len(parts) > 1 else ""


class EvalCaseTests(unittest.TestCase):
    def test_every_case_has_answers_and_a_checklist(self):
        found = cases()
        self.assertGreaterEqual(len(found), 4, "lean, standard, strict and upgrade cases")
        for path in found:
            text = path.read_text(encoding="utf-8")
            with self.subTest(case=path.name):
                self.assertTrue(text.startswith("# "))
                self.assertTrue(section(text, "## Answers").strip())
                must = section(text, "## The plan must")
                must_not = section(text, "## The plan must not")
                self.assertGreaterEqual(len(re.findall(r"^- ", must, re.M)), 8)
                self.assertGreaterEqual(len(re.findall(r"^- ", must_not, re.M)), 3)

    def test_readme_lists_every_case_and_has_the_prompt(self):
        readme = (EVALS / "README.md").read_text(encoding="utf-8")
        for path in cases():
            with self.subTest(case=path.name):
                self.assertIn(f"`{path.name}`", readme)
        for heading in ("## How to run a case", "## Prompt"):
            self.assertIn(heading, readme)

    def test_fixtures_named_by_a_case_exist(self):
        for path in cases():
            for fixture in re.findall(r"`(evals/fixtures/[\w./-]+)`", path.read_text(encoding="utf-8")):
                with self.subTest(case=path.name, fixture=fixture):
                    self.assertTrue((KIT / fixture).exists())


if __name__ == "__main__":
    unittest.main()
