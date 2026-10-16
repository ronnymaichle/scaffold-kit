"""The scripts/quality folder must pass its own checks once copied into a project."""
import shutil
import unittest

from helpers import QUALITY, TempProject, run_main

import debug_leftovers
import design_tokens
import folder_docs


class VendoredFolderTests(unittest.TestCase):
    def test_copied_folder_passes_every_check(self):
        with TempProject({
            "scripts/CLAUDE.md": "# scripts\n\nPurpose: Project scripts.\n\n## Subfolders\n- `quality/`: vendored quality checks\n",
            "quality.config.json": '{"folderDocs": {"codemapFile": null}}',
        }) as p:
            target = p.root / "scripts" / "quality"
            shutil.copytree(QUALITY, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            code, out = run_main(folder_docs.main, ["--root", str(p.root), "check"])
            self.assertEqual(code, 0, out)
            code, out = run_main(debug_leftovers.main, ["--root", str(p.root)])
            self.assertEqual(code, 0, out)
            code, out = run_main(design_tokens.main, ["--root", str(p.root), "literals"])
            self.assertEqual(code, 0, out)


if __name__ == "__main__":
    unittest.main()
