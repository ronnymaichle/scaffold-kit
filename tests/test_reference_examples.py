"""Examples in the reference files must pass the checks they illustrate."""
import re
import unittest

from helpers import KIT, TempProject, run_main

import folder_docs


def first_markdown_block(path):
    text = path.read_text(encoding="utf-8")
    m = re.search(r"```markdown\n(.*?)```", text, re.S)
    if not m:
        raise AssertionError(f"no markdown example in {path}")
    return m.group(1)


def parent_doc(folder, child):
    return f"# {folder}\n\nPurpose: Parent folder.\n\n## Subfolders\n\n- `{child}/`: child folder\n"


class FolderDocsExampleTests(unittest.TestCase):
    def test_documented_example_passes_the_check(self):
        example = first_markdown_block(KIT / "references" / "folder-docs.md")
        files = {
            "src/lib/server/services/CLAUDE.md": example,
            "src/lib/server/services/markers.ts": (
                "export async function getMarkersInBbox(db, bbox, limit) { return []; }\n"
                "export async function createMarker(db, user, input) { return input; }\n"
                "export type MarkerInput = { title: string };\n"
                "export const MAX_MARKERS_PER_USER = 100;\n"
            ),
            "src/lib/server/services/markers.test.ts": "import { test } from 'vitest';\n",
            "src/lib/server/services/uploads/presign.ts": "export function presign() {}\n",
            "src/lib/server/services/uploads/CLAUDE.md": (
                "# src/lib/server/services/uploads\n\nPurpose: Presigned uploads.\n\n## Files\n\n"
                "### presign.ts\nPresigned upload URLs.\n- `presign()` -> `string`: a short-lived upload URL\n"
            ),
            "src/CLAUDE.md": parent_doc("src", "lib"),
            "src/lib/CLAUDE.md": parent_doc("src/lib", "server"),
            "src/lib/server/CLAUDE.md": parent_doc("src/lib/server", "services"),
            "quality.config.json": '{"folderDocs": {"codemapFile": null}}',
        }
        with TempProject(files) as p:
            code, out = run_main(folder_docs.main, ["--root", str(p.root), "check"])
        self.assertEqual(code, 0, out)

    def test_template_folder_doc_parses(self):
        template = (KIT / "templates" / "folder-CLAUDE.md").read_text(encoding="utf-8")
        doc = folder_docs._parse_doc(template)
        self.assertIsNotNone(doc.purpose)
        self.assertIn("files", doc.sections)


if __name__ == "__main__":
    unittest.main()
