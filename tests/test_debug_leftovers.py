import unittest

from helpers import HAS_GIT, TempProject, run_main

import debug_leftovers

MARKER = "DEBUG" + "-TEMP"


class LeftoverTests(unittest.TestCase):
    def find(self, name, text):
        return debug_leftovers._find_leftovers(name, text)

    def test_marker_in_a_comment_is_found(self):
        found = self.find("a.ts", f"const x = 1;\nconsole.log(x); // {MARKER}\n")
        self.assertEqual(found, [(2, f"{MARKER} line")])

    def test_debugger_statement_but_not_in_comments_or_strings(self):
        text = "debugger;\n// open the debugger\nconst s = 'debugger';\nobj.debugger = 1;\n"
        self.assertEqual(self.find("a.js", text), [(1, "debugger statement")])

    def test_svelte_only_scans_scripts(self):
        text = "<script>\n  debugger;\n</script>\n<p>Use the debugger in devtools</p>\n"
        self.assertEqual(self.find("A.svelte", text), [(2, "debugger statement")])

    def test_python_breakpoints(self):
        text = "x = 1\nbreakpoint()\n# breakpoint()\ns = 'pdb.set_trace()'\nimport pdb; pdb.set_trace()\n"
        found = self.find("a.py", text)
        self.assertIn((2, "breakpoint() call"), found)
        self.assertIn((5, "pdb.set_trace() call"), found)
        self.assertEqual(len(found), 2)

    def test_markdown_is_ignored(self):
        self.assertEqual(self.find("CLAUDE.md", f"Mark temporary lines with {MARKER}.\n"), [])

    def test_cli_reports_and_exits_1(self):
        with TempProject({"src/a.ts": f"let a = 1; // {MARKER}\n", "README.md": MARKER}) as p:
            code, out = run_main(debug_leftovers.main, ["--root", str(p.root)])
        self.assertEqual(code, 1)
        self.assertIn("src/a.ts:1", out)
        self.assertNotIn("README.md", out)

    @unittest.skipUnless(HAS_GIT, "git not installed")
    def test_staged_reads_the_index(self):
        with TempProject({"src/a.ts": "let a = 1;\n"}, git=True) as p:
            p.run_git("add", "-A")
            code, _ = run_main(debug_leftovers.main, ["--root", str(p.root), "--staged"])
            self.assertEqual(code, 0)
            p.write("src/a.ts", "debugger;\n")  # working tree only, not staged
            code, _ = run_main(debug_leftovers.main, ["--root", str(p.root), "--staged"])
            self.assertEqual(code, 0)
            p.run_git("add", "-A")
            code, out = run_main(debug_leftovers.main, ["--root", str(p.root), "--staged"])
            self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
