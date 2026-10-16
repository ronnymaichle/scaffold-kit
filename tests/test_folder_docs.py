import unittest

from helpers import HAS_GIT, TempProject, run_main

import folder_docs

TODO = "TODO" + "(describe)"

SERVICE = """
    import { db } from './db';
    // export function commentedOut() {}
    const note = "export function inString() {}";
    export async function getMarkersInBbox(bbox, limit = 500) { return []; }
    export const createMarker = async (input) => input;
    export type MarkerDTO = { id: string };
    export interface MarkerInput { title: string }
    function privateHelper() {}
"""

POPUP = """
    <script lang="ts">
      import type { MarkerDTO } from '$lib/server/markers';
      type Props = { marker: MarkerDTO; onClose?: () => void };
      let { marker, onClose = () => { console.log('x'); }, ...rest }: Props = $props();
    </script>
    <div>{marker.title}</div>
"""

ROUTE = """
    <script>
      let { data } = $props();
    </script>
    <h1>{data.title}</h1>
"""


def project_files():
    return {
        "package.json": "{}",
        "src/lib/server/markers.ts": SERVICE,
        "src/lib/server/db.ts": "export const db = {};\n",
        "src/lib/components/MarkerPopup.svelte": POPUP,
        "src/routes/+page.svelte": ROUTE,
        "src/lib/assets/logo.png": "binary-ish",
    }


def describe_all(p, rels):
    for rel in rels:
        text = p.read(rel).replace(TODO + ":", "Described.").replace(TODO, "Described.")
        (p.root / rel).write_text(text, encoding="utf-8")


DOCS = [
    "src/CLAUDE.md",
    "src/lib/CLAUDE.md",
    "src/lib/server/CLAUDE.md",
    "src/lib/components/CLAUDE.md",
    "src/routes/CLAUDE.md",
]


class FolderDocsFlowTests(unittest.TestCase):
    def check(self, p):
        return run_main(folder_docs.main, ["--root", str(p.root), "check"])

    def test_full_flow_init_describe_codemap(self):
        with TempProject(project_files()) as p:
            code, out = self.check(p)
            self.assertEqual(code, 1)
            self.assertIn("src/lib/server/: missing CLAUDE.md", out)
            self.assertNotIn("src/lib/assets", out)  # images only: no doc needed

            code, out = run_main(folder_docs.main, ["--root", str(p.root), "init"])
            self.assertEqual(code, 0)
            for rel in DOCS:
                self.assertTrue((p.root / rel).is_file(), rel)
            server_doc = p.read("src/lib/server/CLAUDE.md")
            for name in ("getMarkersInBbox", "createMarker", "MarkerDTO", "MarkerInput"):
                self.assertIn(f"`{name}`", server_doc)
            self.assertNotIn("privateHelper", server_doc)
            self.assertNotIn("commentedOut", server_doc)
            self.assertNotIn("inString", server_doc)
            popup_doc = p.read("src/lib/components/CLAUDE.md")
            self.assertIn("Props: `marker`, `onClose`", popup_doc)
            self.assertNotIn("`rest`", popup_doc)

            code, out = self.check(p)
            self.assertEqual(code, 1)
            self.assertIn("placeholder", out)

            describe_all(p, DOCS)
            code, out = self.check(p)
            self.assertEqual(code, 1)
            self.assertIn("CODEMAP.md is out of date", out)

            run_main(folder_docs.main, ["--root", str(p.root), "codemap"])
            codemap = p.read("docs/CODEMAP.md")
            self.assertIn("[`src/lib/server/`](../src/lib/server/CLAUDE.md)", codemap)
            code, out = self.check(p)
            self.assertEqual(code, 0, out)

    def test_new_export_missing_then_init_appends(self):
        with TempProject(project_files()) as p:
            run_main(folder_docs.main, ["--root", str(p.root), "init"])
            describe_all(p, DOCS)
            run_main(folder_docs.main, ["--root", str(p.root), "codemap"])
            p.write("src/lib/server/markers.ts", SERVICE + "\nexport function deleteMarker(id) {}\n")
            code, out = self.check(p)
            self.assertEqual(code, 1)
            self.assertIn("exports `deleteMarker`, which is not listed", out)
            run_main(folder_docs.main, ["--root", str(p.root), "init"])
            doc = p.read("src/lib/server/CLAUDE.md")
            self.assertIn("`deleteMarker`", doc)
            self.assertEqual(doc.count("### markers.ts"), 1)
            describe_all(p, ["src/lib/server/CLAUDE.md"])
            code, out = self.check(p)
            self.assertEqual(code, 0, out)

    def test_stale_entries_are_reported(self):
        with TempProject(project_files()) as p:
            run_main(folder_docs.main, ["--root", str(p.root), "init"])
            describe_all(p, DOCS)
            run_main(folder_docs.main, ["--root", str(p.root), "codemap"])
            p.write("src/lib/server/markers.ts", "export async function getMarkersInBbox() {}\n")
            p.remove("src/lib/server/db.ts")
            code, out = self.check(p)
            self.assertIn("lists `createMarker`, which it does not export", out)
            self.assertIn("lists db.ts, which does not exist", out)

    def test_new_subfolder_must_be_listed(self):
        with TempProject(project_files()) as p:
            run_main(folder_docs.main, ["--root", str(p.root), "init"])
            describe_all(p, DOCS)
            p.write("src/lib/server/uploads/presign.ts", "export function presign() {}\n")
            code, out = self.check(p)
            self.assertIn("subfolder uploads/ is not listed", out)
            self.assertIn("src/lib/server/uploads/: missing CLAUDE.md", out)
            run_main(folder_docs.main, ["--root", str(p.root), "init"])
            self.assertIn("`uploads/`", p.read("src/lib/server/CLAUDE.md"))


class FolderDocsFormatTests(unittest.TestCase):
    def test_glob_entries_cover_many_files(self):
        files = {
            "db/migrations/0001_init.sql": "create table a();\n",
            "db/migrations/0002_more.sql": "create table b();\n",
            "db/CLAUDE.md": "# db\n\nPurpose: Database files.\n\n## Subfolders\n- `migrations/`: generated SQL\n",
            "db/migrations/CLAUDE.md": "# db/migrations\n\nPurpose: Generated migrations.\n\n## Files\n\n### *.sql\nApplied in order by `migrate`; never edited after being applied.\n",
        }
        with TempProject(files) as p:
            run_main(folder_docs.main, ["--root", str(p.root), "codemap"])
            code, out = run_main(folder_docs.main, ["--root", str(p.root), "check"])
            self.assertEqual(code, 0, out)

    def test_wildcard_reexports_skip_the_stale_check(self):
        files = {
            "lib/index.ts": "export * from './a';\nexport { b as renamed, type C } from './b';\n",
            "lib/CLAUDE.md": "# lib\n\nPurpose: Public API.\n\n## Files\n\n### index.ts\nRe-exports the module API.\n- `renamed` re-export of b\n- `C` type\n- `fromA` comes through export *\n",
        }
        with TempProject(files) as p:
            run_main(folder_docs.main, ["--root", str(p.root), "codemap"])
            code, out = run_main(folder_docs.main, ["--root", str(p.root), "check"])
            self.assertEqual(code, 0, out)

    def test_props_after_arrow_and_generic_defaults(self):
        component = (
            "<script lang=\"ts\">\n"
            "  let { onClose = () => {}, title, items = new Map<string, number>(), limit = a >= 2 ? 1 : 0, last }"
            ": Props = $props();\n"
            "</script>\n"
        )
        with TempProject({"ui/Panel.svelte": component}) as p:
            run_main(folder_docs.main, ["--root", str(p.root), "init"])
            doc = p.read("ui/CLAUDE.md")
        self.assertIn("- Props: `items`, `last`, `limit`, `onClose`, `title`", doc)
        self.assertNotIn("`number`", doc)

    def test_commonjs_exports(self):
        files = {
            "tools/a.cjs": "module.exports = { build, check: run, async lint() {} };\nexports.VERSION = 1;\n",
            "tools/b.cjs": "module.exports = function main() {};\n",
            "tools/CLAUDE.md": (
                "# tools\n\nPurpose: Build helpers.\n\n## Files\n\n### a.cjs\nBuild tasks.\n"
                "- `build` builds\n- `check` checks\n- `lint` lints\n- `VERSION` kit version\n- `gone` removed\n\n"
                "### b.cjs\nEntry point.\n- `main()` runs everything\n"
            ),
            "quality.config.json": '{"folderDocs": {"codemapFile": null}}',
        }
        with TempProject(files) as p:
            code, out = run_main(folder_docs.main, ["--root", str(p.root), "check"])
        self.assertEqual(code, 1)
        self.assertIn("a.cjs lists `gone`, which it does not export", out)
        self.assertNotIn("b.cjs", out)
        self.assertEqual(out.count("tools/CLAUDE.md"), 1, out)

    def test_entry_without_description_fails(self):
        files = {
            "lib/a.ts": "export const a = 1;\n",
            "lib/CLAUDE.md": "# lib\n\nPurpose: Things.\n\n## Files\n\n### a.ts\n- `a` the value\n",
        }
        with TempProject(files) as p:
            code, out = run_main(folder_docs.main, ["--root", str(p.root), "check"])
            self.assertIn("entry 'a.ts' has no description", out)

    def test_python_and_go_exports(self):
        files = {
            "pkg/api.py": "__all__ = ['create']\n\ndef create():\n    pass\n\ndef helper():\n    pass\n",
            "pkg/models.py": "MAX = 5\n_PRIVATE = 1\n\nclass Marker:\n    pass\n\nif __name__ == '__main__':\n    run = 1\n",
            "svc/store.go": (
                "package svc\n\ntype Store struct{}\n\nfunc (s *Store) Get(id string) error { return nil }\n"
                "func New() *Store { return &Store{} }\nfunc helper() {}\n\nconst (\n\tLimit = 10\n\tinner = 1\n)\n"
            ),
        }
        with TempProject(files) as p:
            run_main(folder_docs.main, ["--root", str(p.root), "init"])
            py_doc, go_doc = p.read("pkg/CLAUDE.md"), p.read("svc/CLAUDE.md")
        self.assertIn("`create`", py_doc)
        self.assertNotIn("`helper`", py_doc)
        self.assertIn("`MAX`", py_doc)
        self.assertIn("`Marker`", py_doc)
        self.assertNotIn("_PRIVATE", py_doc)
        self.assertNotIn("`run`", py_doc)
        for name in ("Store", "Store.Get", "New", "Limit"):
            self.assertIn(f"`{name}`", go_doc)
        self.assertNotIn("helper", go_doc)
        self.assertNotIn("`inner`", go_doc)

    def test_include_limits_enforcement(self):
        files = project_files()
        files["quality.config.json"] = '{"folderDocs": {"include": ["src/lib/server"], "codemapFile": null}}'
        with TempProject(files) as p:
            code, out = run_main(folder_docs.main, ["--root", str(p.root), "check"])
            self.assertIn("src/lib/server/: missing CLAUDE.md", out)
            self.assertNotIn("src/routes", out)
            self.assertNotIn("src/: missing", out)

    def test_root_files_and_hidden_folders_are_ignored(self):
        files = {"vite.config.ts": "export default {};\n", ".github/workflows/ci.yml": "on: push\n"}
        with TempProject(files) as p:
            code, out = run_main(folder_docs.main, ["--root", str(p.root), "check"])
            self.assertEqual(code, 1)  # only the empty code map differs
            self.assertNotIn("missing CLAUDE.md", out)


@unittest.skipUnless(HAS_GIT, "git not installed")
class FolderDocsStagedTests(unittest.TestCase):
    def test_added_file_needs_its_folder_doc_staged(self):
        with TempProject(project_files(), git=True) as p:
            run_main(folder_docs.main, ["--root", str(p.root), "init"])
            describe_all(p, DOCS)
            run_main(folder_docs.main, ["--root", str(p.root), "codemap"])
            p.run_git("add", "-A")
            p.run_git("commit", "-q", "-m", "chore: init")

            p.write("src/lib/server/comments.ts", "export function addComment() {}\n")
            p.run_git("add", "src/lib/server/comments.ts")
            code, out = run_main(folder_docs.main, ["--root", str(p.root), "staged"])
            self.assertEqual(code, 1)
            self.assertIn("comments.ts was added; update and stage src/lib/server/CLAUDE.md", out)

            run_main(folder_docs.main, ["--root", str(p.root), "init"])
            describe_all(p, ["src/lib/server/CLAUDE.md"])
            p.run_git("add", "src/lib/server/CLAUDE.md")
            code, out = run_main(folder_docs.main, ["--root", str(p.root), "staged"])
            self.assertEqual(code, 0, out)

    def test_modified_file_only_warns(self):
        with TempProject(project_files(), git=True) as p:
            run_main(folder_docs.main, ["--root", str(p.root), "init"])
            describe_all(p, DOCS)
            run_main(folder_docs.main, ["--root", str(p.root), "codemap"])
            p.run_git("add", "-A")
            p.run_git("commit", "-q", "-m", "chore: init")
            p.write("src/lib/server/db.ts", "export const db = { ready: true };\n")
            p.run_git("add", "src/lib/server/db.ts")
            code, out = run_main(folder_docs.main, ["--root", str(p.root), "staged"])
            self.assertEqual(code, 0, out)
            self.assertIn("warning: src/lib/server/db.ts changed", out)


if __name__ == "__main__":
    unittest.main()
