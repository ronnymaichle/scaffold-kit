"""The agent templates stay valid, match the roster in references/agents.md, and avoid known traps."""
import json
import re
import unittest

from helpers import KIT
from test_skill_files import frontmatter

AGENTS = KIT / "templates" / "claude" / "agents"
SETTINGS = KIT / "templates" / "claude" / "settings.json"
STACK_SKILL = KIT / "templates" / "claude" / "skills" / "stack-conventions" / "SKILL.md"
REFERENCE = KIT / "references" / "agents.md"

EFFORTS = {"low", "medium", "high", "xhigh", "max"}
MODEL_ALIASES = {"opus", "sonnet", "haiku", "fable", "inherit"}
WRITE_TOOLS = {"Edit", "Write", "NotebookEdit"}
READ_ONLY = {"reviewer", "security-auditor", "designer", "architect"}
# Agents that write or judge code get the project's stack conventions preloaded.
PRELOADS_STACK = {"implementer", "reviewer", "debugger", "designer", "architect"}


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

    def test_parallel_implementers_leave_folder_docs_to_the_lead(self):
        # folder_docs.py init rewrites every folder doc, so a parallel implementer running it clobbers the others' work.
        text = (AGENTS / "implementer.md").read_text(encoding="utf-8")
        steps = [s for s in re.split(r"\n(?=\d+\. )", text) if "folder_docs.py init" in s or "`init`" in s]
        self.assertTrue(steps)
        for step in steps:
            with self.subTest(step=step[:40]):
                self.assertIn("runs alone", step)
        flow = REFERENCE.read_text(encoding="utf-8").split("## How work flows")[1].split("\n## ")[0]
        self.assertIn("the lead runs `folder_docs.py init`", flow)

    def test_roster_matches_templates(self):
        self.assertEqual(roster_in_reference(), {p.stem for p in self.agent_files()})

    def test_code_agents_preload_the_stack_skill(self):
        for name in PRELOADS_STACK:
            with self.subTest(agent=name):
                text = (AGENTS / f"{name}.md").read_text(encoding="utf-8")
                block = text[4:text.index("\n---", 4)]
                self.assertRegex(block, r"(?m)^skills:\n  - stack-conventions$")

    def test_stack_skill_template(self):
        text = STACK_SKILL.read_text(encoding="utf-8")
        fields = frontmatter(text)
        self.assertEqual(fields.get("name"), "stack-conventions")
        self.assertTrue(fields.get("description"))
        # Preloading skips skills that disable model invocation.
        self.assertNotIn("disable-model-invocation", fields)
        for heading in ("## Conventional and recommended", "## Traps", "## Sources"):
            self.assertIn(heading, text)
        self.assertIn("{{", text, "filled in at scaffold time from the official docs")

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
