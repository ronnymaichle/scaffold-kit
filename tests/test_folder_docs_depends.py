"""Depends on lines written from imports, and the deps command."""
import unittest

from helpers import TempProject, run_main

import folder_docs

TODO = "TODO" + "(describe)"
NO_CODEMAP = '{"folderDocs": {"codemapFile": null}}'


def init(p):
    return run_main(folder_docs.main, ["--root", str(p.root), "init"])


def check(p):
    return run_main(folder_docs.main, ["--root", str(p.root), "check"])


def deps(p, *paths):
    return run_main(folder_docs.main, ["--root", str(p.root), "deps", *paths])


def describe(p):
    """Replace every TODO marker in every folder doc, as a person would."""
    for path in p.root.rglob("CLAUDE.md"):
        text = path.read_text(encoding="utf-8").replace(TODO + ":", "Described.").replace(TODO, "Described.")
        path.write_text(text, encoding="utf-8")


def depends_lines(text):
    return [line for line in text.splitlines() if line.startswith("Depends on:")]


SERVICE = """
    import { z } from 'zod';
    import { findMarkers } from '$lib/server/repositories/markers';
    import { markerSchema } from '../../schemas/marker';
    import { round } from './helpers.js';
    import type { MarkerDTO } from './types';
    // import { gone } from './commented';
    const text = "import { fake } from './in-string'";
    export async function listMarkers(db) { return findMarkers(db).map(round); }
"""


def service_files():
    return {
        "src/lib/server/services/markers.ts": SERVICE,
        "src/lib/server/services/helpers.ts": "export const round = (n) => n;\n",
        "src/lib/server/services/types.ts": "export type MarkerDTO = { id: string };\n",
        "src/lib/server/services/markers.test.ts": "import { listMarkers } from './markers';\nimport { findMarkers } from '../repositories/markers';\n",
        "src/lib/server/repositories/markers.ts": "export function findMarkers(db) { return []; }\n",
        "src/lib/schemas/marker.ts": "export const markerSchema = {};\n",
        "quality.config.json": NO_CODEMAP,
    }


EXPECTED = (
    "Depends on: `src/lib/schemas/marker.ts`, `src/lib/server/repositories/markers.ts`, "
    "`src/lib/server/services/helpers.ts`, `src/lib/server/services/types.ts`"
)


class DependsLineTests(unittest.TestCase):
    def test_init_writes_the_line_from_imports(self):
        with TempProject(service_files()) as p:
            init(p)
            doc = p.read("src/lib/server/services/CLAUDE.md")
            self.assertIn(EXPECTED, doc)
            self.assertNotIn("zod", doc)
            self.assertNotIn("commented", doc)
            self.assertNotIn("in-string", doc)
            self.assertEqual(len(depends_lines(doc)), 1, doc)  # test files get no line
            describe(p)
            code, out = check(p)
            self.assertEqual(code, 0, out)

    def test_check_fails_when_imports_change_and_init_refreshes_the_line(self):
        with TempProject(service_files()) as p:
            init(p)
            describe(p)
            p.write("src/lib/server/services/markers.ts", SERVICE.replace("import type { MarkerDTO } from './types';", ""))
            code, out = check(p)
            self.assertEqual(code, 1)
            self.assertIn("markers.ts: Depends on should be", out)
            init(p)
            doc = p.read("src/lib/server/services/CLAUDE.md")
            self.assertEqual(
                depends_lines(doc),
                [EXPECTED.replace(", `src/lib/server/services/types.ts`", "")],
            )
            code, out = check(p)
            self.assertEqual(code, 0, out)

    def test_a_line_without_imports_is_removed(self):
        with TempProject(service_files()) as p:
            init(p)
            describe(p)
            p.write("src/lib/server/services/markers.ts", "export async function listMarkers() { return []; }\n")
            code, out = check(p)
            self.assertIn("markers.ts: imports no project files, so it needs no Depends on line", out)
            init(p)
            self.assertEqual(depends_lines(p.read("src/lib/server/services/CLAUDE.md")), [])
            code, out = check(p)
            self.assertEqual(code, 0, out)

    def test_a_handwritten_line_is_replaced_and_the_rest_kept(self):
        files = service_files()
        files["src/lib/server/services/CLAUDE.md"] = (
            "# src/lib/server/services\n\nPurpose: Business logic.\n\n## Files\n\n"
            "### markers.ts\nMarker queries.\n- `listMarkers(db)` -> `MarkerDTO[]`: published markers\n"
            "Depends on: repositories/markers, schemas/marker\n\n"
            "### helpers.ts\nNumber helpers.\n- `round` rounds\n\n"
            "### types.ts\nShared types.\n- Also exports: `MarkerDTO`\n\n"
            "### *.test.ts\nUnit tests.\n"
        )
        with TempProject(files) as p:
            init(p)
            describe(p)
            code, out = check(p)
            self.assertEqual(code, 0, out)
            doc = p.read("src/lib/server/services/CLAUDE.md")
            self.assertEqual(depends_lines(doc), [EXPECTED])
            self.assertIn("Marker queries.\n- `listMarkers(db)` -> `MarkerDTO[]`: published markers\nDepends on:", doc)

    def test_new_symbols_go_before_the_line(self):
        with TempProject(service_files()) as p:
            init(p)
            describe(p)
            p.write("src/lib/server/services/markers.ts", SERVICE + "export function countMarkers() { return 0; }\n")
            init(p)
            doc = p.read("src/lib/server/services/CLAUDE.md")
            entry = doc.split("### markers.ts")[1].split("###")[0]
            self.assertLess(entry.index("`countMarkers`"), entry.index("Depends on:"))

    def test_the_line_is_not_a_description(self):
        files = {
            "lib/a.ts": "import { b } from './b';\nexport const a = b;\n",
            "lib/b.ts": "export const b = 1;\n",
            "lib/CLAUDE.md": (
                "# lib\n\nPurpose: Things.\n\n## Files\n\n### a.ts\n- `a` the value\nDepends on: `lib/b.ts`\n\n"
                "### b.ts\nThe base value.\n- `b` the value\n"
            ),
            "quality.config.json": NO_CODEMAP,
        }
        with TempProject(files) as p:
            code, out = check(p)
        self.assertIn("entry 'a.ts' has no description", out)
        self.assertNotIn("Depends on should be", out)

    def test_the_check_can_be_turned_off(self):
        files = service_files()
        files["quality.config.json"] = '{"folderDocs": {"codemapFile": null, "dependsCheck": false}}'
        with TempProject(files) as p:
            init(p)
            self.assertEqual(depends_lines(p.read("src/lib/server/services/CLAUDE.md")), [])
            describe(p)
            code, out = check(p)
            self.assertEqual(code, 0, out)


class ImportResolutionTests(unittest.TestCase):
    def line_for(self, files, doc):
        files = dict(files)
        files.setdefault("quality.config.json", NO_CODEMAP)
        with TempProject(files) as p:
            init(p)
            return depends_lines(p.read(doc))

    def test_tsconfig_paths_extends_and_configured_aliases(self):
        files = {
            "tsconfig.json": (
                '{\n  // generated base first\n  "extends": "./.svelte-kit/tsconfig.json",\n'
                '  "compilerOptions": { "strict": true, },\n}\n'
            ),
            ".svelte-kit/tsconfig.json": '{"compilerOptions": {"paths": {"~/*": ["../src/*"]}}}',
            "src/app/page.ts": (
                "import { util } from '~/lib/util';\nimport { theme } from '$lib/theme';\n"
                "import { x } from '#shared/x';\nexport const page = [util, theme, x];\n"
            ),
            "src/lib/util.ts": "export const util = 1;\n",
            "src/lib/theme/index.ts": "export const theme = 1;\n",
            "shared/x.ts": "export const x = 1;\n",
            "quality.config.json": '{"folderDocs": {"codemapFile": null, "aliases": {"$lib": "src/lib", "#shared": "shared"}}}',
        }
        self.assertEqual(
            self.line_for(files, "src/app/CLAUDE.md"),
            ["Depends on: `shared/x.ts`, `src/lib/theme/index.ts`, `src/lib/util.ts`"],
        )

    def test_package_json_subpath_imports(self):
        files = {
            "package.json": (
                '{"imports": {"#lib": "./src/lib/index.js", "#lib/*": "./src/lib/*",'
                ' "#cfg": {"types": "./config/index.d.ts", "default": "./config/index.js"}}}'
            ),
            "src/hooks.server.ts": (
                "import { ERRORS } from '#lib/server/errors.js';\nimport { all } from '#lib';\n"
                "import { cfg } from '#cfg';\nexport const handle = [ERRORS, all, cfg];\n"
            ),
            "src/lib/index.ts": "export const all = 1;\n",
            "src/lib/server/errors.ts": "export const ERRORS = {};\n",
            "config/index.ts": "export const cfg = 1;\n",
            "config/index.d.ts": "export declare const cfg: number;\n",
        }
        self.assertEqual(
            self.line_for(files, "src/CLAUDE.md"),
            ["Depends on: `config/index.ts`, `src/lib/index.ts`, `src/lib/server/errors.ts`"],
        )

    def test_child_tsconfig_paths_replace_the_parents(self):
        files = {
            "tsconfig.json": '{"extends": "./base.json", "compilerOptions": {"paths": {"@/*": ["./src/*"]}}}',
            "base.json": '{"compilerOptions": {"paths": {"~/*": ["./src/*"]}}}',
            "src/app/page.ts": "import { a } from '@/lib/a';\nimport { b } from '~/lib/b';\nexport const page = [a, b];\n",
            "src/lib/a.ts": "export const a = 1;\n",
            "src/lib/b.ts": "export const b = 1;\n",
        }
        self.assertEqual(self.line_for(files, "src/app/CLAUDE.md"), ["Depends on: `src/lib/a.ts`"])

    def test_require_dynamic_import_and_reexports(self):
        files = {
            "lib/index.ts": (
                "export * from './a';\nexport { b } from './b';\n"
                "const c = require('./c');\nconst d = () => import('./d');\nimport './e.css';\n"
            ),
            "lib/a.ts": "export const a = 1;\n",
            "lib/b.ts": "export const b = 1;\n",
            "lib/c.cjs": "module.exports = {};\n",
            "lib/d.ts": "export default 1;\n",
            "lib/e.css": "body {}\n",
        }
        self.assertEqual(
            self.line_for(files, "lib/CLAUDE.md"),
            ["Depends on: `lib/a.ts`, `lib/b.ts`, `lib/c.cjs`, `lib/d.ts`, `lib/e.css`"],
        )

    def test_svelte_and_vue_script_blocks(self):
        files = {
            "src/lib/components/MarkerCard.svelte": (
                "<script module>\n  import { shared } from './shared';\n</script>\n"
                "<script lang=\"ts\">\n  import Badge from './Badge.svelte';\n"
                "  import { formatDistance } from '$lib/format';\n  let { marker } = $props();\n</script>\n"
            ),
            "src/lib/components/Badge.svelte": "<script>\n  let { label } = $props();\n</script>\n",
            "src/lib/components/shared.ts": "export const shared = 1;\n",
            "src/lib/format.ts": "export const formatDistance = 1;\n",
            "src/components/Card.vue": "<script setup lang=\"ts\">\nimport Btn from './Btn.vue'\n</script>\n",
            "src/components/Btn.vue": "<template><button /></template>\n",
        }
        files["quality.config.json"] = NO_CODEMAP
        with TempProject(files) as p:
            init(p)
            svelte_doc = p.read("src/lib/components/CLAUDE.md")
            vue_doc = p.read("src/components/CLAUDE.md")
        self.assertIn(
            "Depends on: `src/lib/components/Badge.svelte`, `src/lib/components/shared.ts`, `src/lib/format.ts`",
            svelte_doc,
        )
        self.assertIn("Depends on: `src/components/Btn.vue`", vue_doc)

    def test_python_relative_absolute_and_src_layout(self):
        files = {
            "app/__init__.py": "",
            "app/main.py": (
                "import os\nfrom app.routers import markers\nfrom .config import settings\n"
                "from . import db\n\ndef run():\n    return markers, settings, db, os\n"
            ),
            "app/config.py": "settings = {}\n",
            "app/db.py": "engine = None\n",
            "app/routers/__init__.py": "",
            "app/routers/markers.py": "router = None\n",
            "src/pkg/__init__.py": "",
            "src/pkg/a.py": "import pkg.b\n\nvalue = pkg.b.value\n",
            "src/pkg/b.py": "value = 1\n",
        }
        files["quality.config.json"] = NO_CODEMAP
        with TempProject(files) as p:
            init(p)
            app_doc = p.read("app/CLAUDE.md")
            pkg_doc = p.read("src/pkg/CLAUDE.md")
        self.assertIn("Depends on: `app/config.py`, `app/db.py`, `app/routers/markers.py`", app_doc)
        self.assertIn("Depends on: `src/pkg/b.py`", pkg_doc)

    def test_python_script_imports_its_neighbours(self):
        files = {
            "scripts/run.py": "import sys\nimport helper  # found through sys.path[0], the script's folder\n\nhelper.go(sys.argv)\n",
            "scripts/helper.py": "def go(argv):\n    return argv\n",
        }
        self.assertEqual(self.line_for(files, "scripts/CLAUDE.md"), ["Depends on: `scripts/helper.py`"])

    def test_go_imports_resolve_through_go_mod(self):
        files = {
            "go.mod": "module example.com/app\n\ngo 1.23\n",
            "cmd/api/main.go": (
                "package main\n\nimport (\n\t\"fmt\"\n\tmk \"example.com/app/internal/markers\"\n)\n\n"
                "func main() { fmt.Println(mk.New()) }\n"
            ),
            "internal/markers/store.go": "package markers\n\nfunc New() int { return 1 }\n",
        }
        self.assertEqual(self.line_for(files, "cmd/api/CLAUDE.md"), ["Depends on: `internal/markers/`"])


class DepsCommandTests(unittest.TestCase):
    def test_lists_imports_and_importers_including_tests(self):
        with TempProject(service_files()) as p:
            code, out = deps(p, "src/lib/server/repositories/markers.ts", "src/lib/server/services/markers.ts")
        self.assertEqual(code, 0, out)
        repo, service = out.split("\n\n", 1)
        self.assertEqual(
            repo.splitlines(),
            [
                "src/lib/server/repositories/markers.ts",
                "  imports: none",
                "  imported by:",
                "    src/lib/server/services/markers.test.ts",
                "    src/lib/server/services/markers.ts",
            ],
        )
        self.assertIn("  imports:\n    src/lib/schemas/marker.ts\n", service)
        self.assertIn("  imported by:\n    src/lib/server/services/markers.test.ts", service)

    def test_go_files_are_imported_through_their_package(self):
        files = {
            "go.mod": "module example.com/app\n",
            "cmd/api/main.go": "package main\n\nimport \"example.com/app/internal/markers\"\n\nfunc main() { markers.New() }\n",
            "internal/markers/store.go": "package markers\n\nfunc New() {}\n",
        }
        with TempProject(files) as p:
            code, out = deps(p, "internal/markers/store.go")
        self.assertEqual(code, 0, out)
        self.assertIn("  imported by:\n    cmd/api/main.go", out)

    def test_unknown_file(self):
        with TempProject(service_files()) as p:
            code, out = deps(p, "src/missing.ts")
        self.assertEqual(code, 1)
        self.assertIn("src/missing.ts: not a source file of this project", out)


if __name__ == "__main__":
    unittest.main()
