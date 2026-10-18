"""The agent templates stay valid, match the roster in references/agents.md, and avoid known traps."""
import json
import re
import unittest

from helpers import KIT
from test_skill_files import frontmatter

AGENTS = KIT / "templates" / "claude" / "agents"
SETTINGS = KIT / "templates" / "claude" / "settings.json"
REFERENCE = KIT / "references" / "agents.md"

EFFORTS = {"low", "medium", "high", "xhigh", "max"}
MODEL_ALIASES = {"opus", "sonnet", "haiku", "fable", "inherit"}
WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}
READ_ONLY = {"reviewer", "security-auditor"}


def roster_in_reference():
    """Agent names in the first column of the roster table (rows starting with a backticked name)."""
    text = REFERENCE.read_text(encoding="utf-8")
    roster = text.split("## Roster")[1].split("\n## ")[0]
    return set(re.findall(r"^\| `([a-z-]+)` \|", roster, re.M))


class AgentTemplateTests(unittest.TestCase):
    def agent_files(self):
        files = sorted(AGENTS.glob("*.md"))
        self.assertTrue(files, "templates/claude/agents/ has no agent files")
        return files

    def test_frontmatter_is_valid(self):
        for path in self.agent_files():
            with self.subTest(agent=path.name):
                fields = frontmatter(path.read_text(encoding="utf-8"))
                self.assertEqual(fields.get("name"), path.stem)
                self.assertTrue(fields.get("description"))
                model = fields.get("model", "")
                self.assertTrue(model in MODEL_ALIASES or model.startswith("claude-"), model)
                self.assertIn(fields.get("effort"), EFFORTS)
                self.assertRegex(fields.get("maxTurns", ""), r"^\d+$", "every agent needs a turn limit")
                self.assertTrue(fields.get("tools"), "list the tools so each role gets only what it needs")

    def test_read_only_roles_cannot_edit(self):
        for name in READ_ONLY:
            with self.subTest(agent=name):
                fields = frontmatter((AGENTS / f"{name}.md").read_text(encoding="utf-8"))
                tools = {t.strip() for t in fields["tools"].split(",")}
                self.assertFalse(tools & WRITE_TOOLS)

    def test_every_agent_reports_in_the_shared_format(self):
        for path in self.agent_files():
            with self.subTest(agent=path.name):
                text = path.read_text(encoding="utf-8")
                for word in ("Status:", "Evidence:"):
                    self.assertIn(word, text)

    def test_roster_matches_templates(self):
        self.assertEqual(roster_in_reference(), {p.stem for p in self.agent_files()})

    def test_lead_settings(self):
        settings = json.loads(SETTINGS.read_text(encoding="utf-8"))
        model = settings.get("model", "")
        self.assertTrue(model.startswith("claude-opus-"), "the lead runs on a pinned Opus model")
        per_model = settings.get("modelSettings", {})
        self.assertIn(model, per_model, "the effort entry must be keyed by the same model ID")
        self.assertIn(per_model[model].get("effortLevel"), EFFORTS - {"max"})
        # Opus 5.5 and later ignore a top-level effortLevel in user settings, so it
        # would only look like it works.
        self.assertNotIn("effortLevel", settings)
        # Agent teams are enabled per session, never for the whole project.
        self.assertNotIn("CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS", settings.get("env", {}))


if __name__ == "__main__":
    unittest.main()
