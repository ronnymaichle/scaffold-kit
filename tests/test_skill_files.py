"""The skill sources in the kit stay valid and in sync with the kit."""
import re
import unittest

from helpers import KIT

SKILLS = {
    "scaffold-project": KIT / "skill" / "scaffold-project" / "SKILL.md",
    "scaffold-kit-maintainer": KIT / ".claude" / "skills" / "scaffold-kit-maintainer" / "SKILL.md",
}


def frontmatter(text):
    """The key: value pairs between the opening and closing --- lines."""
    if not text.startswith("---\n"):
        raise AssertionError("SKILL.md must start with a --- frontmatter block")
    block = text[4:text.index("\n---", 4)]
    fields = {}
    for line in block.splitlines():
        key, sep, value = line.partition(":")
        if sep:
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            fields[key.strip()] = value
    return fields


def reference_names_in_tables(text):
    """Reference file names in the first column of markdown tables."""
    names = set()
    for line in text.splitlines():
        cells = line.split("|")
        if line.startswith("| `") and len(cells) > 2:
            names.update(re.findall(r"`([\w-]+\.md)`", cells[1]))
    return names


class SkillFileTests(unittest.TestCase):
    def test_frontmatter_is_valid(self):
        for name, path in SKILLS.items():
            with self.subTest(skill=name):
                fields = frontmatter(path.read_text(encoding="utf-8"))
                self.assertEqual(fields.get("name"), name)
                description = fields.get("description", "")
                self.assertTrue(description)
                self.assertLessEqual(len(description), 1024)
                self.assertNotRegex(description, "[<>]")

    def test_scaffold_skill_fetches_the_current_major_version(self):
        major = (KIT / "VERSION").read_text(encoding="utf-8").strip().split(".")[0]
        text = SKILLS["scaffold-project"].read_text(encoding="utf-8")
        self.assertIn(f"'v{major}.*'", text)
        self.assertIn(f"^v{major}\\.", text)

    def test_scaffold_skill_stays_short(self):
        text = SKILLS["scaffold-project"].read_text(encoding="utf-8")
        self.assertLess(len(text), 16000, "keep detail in the kit so the skill survives compaction")

    def test_mapping_tables_list_every_reference(self):
        references = {p.name for p in (KIT / "references").glob("*.md")} - {"upgrade.md"}
        for path in (SKILLS["scaffold-project"], KIT / "README.md"):
            with self.subTest(file=str(path.relative_to(KIT))):
                listed = reference_names_in_tables(path.read_text(encoding="utf-8")) - {"upgrade.md"}
                self.assertEqual(listed, references)


if __name__ == "__main__":
    unittest.main()
