"""agent_guard.py: the PreToolUse hook that enforces the repository rules for agents."""
import json
import os
import re
import subprocess
import sys
import unittest

from helpers import HAS_GIT, KIT, QUALITY, TempProject, run_main

import agent_guard

HEREDOC_COMMIT = 'git commit -m "$(cat <<\'EOF\'\nfeat(markers): add comments\n\ngit push --force and --no-verify are never used\nEOF\n)"'

LEAD_ALLOWED = [
    "git status",
    "git switch main && git pull --ff-only && git switch -c feat/r7-marker-comments",
    'git add -A && git commit -m "feat(markers): add comments"',
    'git commit -m "docs: never use --no-verify or push -f"',
    "git commit -mn",
    "git commit -am 'fix(markers): trim titles'",
    HEREDOC_COMMIT,
    "git rebase main",
    "git push -u origin feat/r7-marker-comments",
    "git push --force-with-lease origin feat/r7-marker-comments",
    "git push -n origin main",
    "git push origin --delete feat/r7-marker-comments",
    "git tag -a v1.2.3 -m 'scaffold 1.2.3' && git push origin v1.2.3",
    "git switch -c hotfix/session-cookie v1.2.2",
    "git branch -D feat/r7-marker-comments",
    "git checkout -- src/lib/markers.ts",
    "git checkout -b feat/r8-photos origin/main",
    "git restore --staged .",
    "git stash && git stash pop",
    "git clean -n",
    "gh pr create --title 'feat(markers): add comments' --body-file pr.md",
    "gh pr view 14 && gh pr checks 14",
    "gh api repos/o/r/pulls/14",
    "bun run deploy:env staging",
    "bun run deploy:env production --dry-run",
    "make deploy-env ENV=production DRY_RUN=1",
    "make deploy-env ENV=staging",
    "python3 scripts/quality/folder_docs.py init",
    "echo 'git push --force'",
    "grep -rn 'reset --hard' docs",
    "git log --oneline 2>&1 | head -5",
]

LEAD_DENIED = [
    ("git commit --no-verify -m 'x'", "hook"),
    ("git commit -nm 'x'", "hook"),
    ("git commit -anm 'x'", "hook"),
    ("FOO=1 git commit -n -m x", "hook"),
    ("git -c core.hooksPath=/dev/null commit -m 'x'", "hook"),
    ("LEFTHOOK=0 git commit -m 'x'", "hook"),
    ("git config core.hooksPath .nohooks", "hook"),
    ("git merge --no-verify main", "hook"),
    ("git push --no-verify", "hook"),
    ("git push -f origin feat/x", "--force-with-lease"),
    ("git push --force origin feat/x", "--force-with-lease"),
    ("git push -uf origin feat/x", "--force-with-lease"),
    ("git push origin +feat/x", "--force-with-lease"),
    ("git push --force-with-lease origin main", "main"),
    ("git push --force-with-lease origin HEAD:main", "main"),
    ("git push origin --delete main", "main"),
    ("git push origin :main", "main"),
    ("git push --mirror origin", "one branch"),
    ("git push --all origin", "one branch"),
    ("cd app && git push -f origin feat/x", "--force-with-lease"),
    ("git -C app push --force origin feat/x", "--force-with-lease"),
    ("bash -c 'git push -f origin feat/x'", "--force-with-lease"),
    ('echo "$(git push -f origin feat/x)"', "--force-with-lease"),
    ("echo `git push -f origin feat/x`", "--force-with-lease"),
    ("git status\ngit push -f origin feat/x", "--force-with-lease"),
    ("git push \\\n  --force origin feat/x", "--force-with-lease"),
    ("/usr/bin/git push -f origin feat/x", "--force-with-lease"),
    ("timeout 30 git push -f origin feat/x", "--force-with-lease"),
    ("timeout -k 5 30s stdbuf -oL git push -f origin feat/x", "--force-with-lease"),
    ("git commit -m 'unclosed", "could not read"),
]

LEAD_ASKED = [
    ("git reset --hard", "uncommitted"),
    ("git reset --hard origin/main", "uncommitted"),
    ("git clean -fd", "uncommitted"),
    ("git clean -xdf", "uncommitted"),
    ("git checkout -- .", "uncommitted"),
    ("git checkout .", "uncommitted"),
    ("git checkout -f main", "uncommitted"),
    ("git restore .", "uncommitted"),
    ("git restore :/", "uncommitted"),
    ("git switch --discard-changes main", "uncommitted"),
    ("git stash clear", "uncommitted"),
    ("gh pr merge 14 --squash --delete-branch", "Merging a pull request"),
    ("gh repo create my-app --private --source . --push", "repository"),
    ("gh api -X PUT repos/o/r/branches/main/protection --input rules.json", "git host"),
    ("bun run deploy:env production", "production"),
    ("npm run deploy:env -- production", "production"),
    ("./scripts/deploy/promote.sh production", "production"),
    ("make deploy-env ENV=production", "production"),
    ("ENV=production make deploy-env", "production"),
]

SUBAGENT_ALLOWED = [
    "git status",
    "git diff --stat",
    "git log --oneline -5",
    "git rev-parse --short HEAD",
    "git show HEAD:src/a.ts",
    "git branch --show-current",
    "git branch -a",
    "git branch --contains abc123",
    "git tag --list",
    "git ls-files src",
    "git blame src/a.ts",
    "git grep -n createMarker",
    "git stash list",
    "git config --get user.name",
    "git remote -v",
    "gh pr view 14",
    "gh pr diff 14",
    "gh issue list",
    "bun run test src/a.test.ts",
    "python3 scripts/quality/folder_docs.py deps src/a.ts",
]

SUBAGENT_DENIED = [
    ("git commit -m 'x'", "Only the lead"),
    ("git add -A", "Only the lead"),
    ("git push", "Only the lead"),
    ("git switch main", "Only the lead"),
    ("git checkout feat/x", "Only the lead"),
    ("git stash", "Only the lead"),
    ("git restore src/a.ts", "Only the lead"),
    ("git branch -d feat/x", "Only the lead"),
    ("git branch feat/new", "Only the lead"),
    ("git tag v1.0.0", "Only the lead"),
    ("git pull", "Only the lead"),
    ("git reset HEAD~1", "Only the lead"),
    ("git status && git commit -m x", "Only the lead"),
    ("gh pr create --title x", "Only the lead"),
    ("gh pr merge 1", "Only the lead"),
    ("gh api repos/o/r/pulls", "Only the lead"),
    ("bun run deploy:env staging", "Only the lead"),
    ("make deploy-env ENV=staging", "Only the lead"),
]


class DecideTests(unittest.TestCase):
    def check(self, cases, wanted, agent=None):
        for command, *expected in cases:
            with self.subTest(command=command, agent=agent):
                decision, reason = agent_guard.decide(command, agent=agent)
                self.assertEqual(decision, wanted, reason)
                if expected:
                    self.assertIn(expected[0], reason)

    def test_lead_allowed(self):
        self.check([(c,) for c in LEAD_ALLOWED], "allow")

    def test_lead_denied_with_the_reason(self):
        self.check(LEAD_DENIED, "deny")

    def test_lead_asks_the_user(self):
        self.check(LEAD_ASKED, "ask")

    def test_subagents_only_read_git_state(self):
        self.check([(c,) for c in SUBAGENT_ALLOWED], "allow", agent="implementer")
        self.check(SUBAGENT_DENIED, "deny", agent="implementer")

    def test_deny_wins_over_ask_in_one_command(self):
        decision, _reason = agent_guard.decide("git reset --hard && git push -f origin feat/x")
        self.assertEqual(decision, "deny")

    def test_every_git_command_in_the_workflows_is_allowed(self):
        # The guard must never block the project's own Feature, Hotfix and Release workflows.
        text = (KIT / "templates" / "CLAUDE.md").read_text(encoding="utf-8")
        commands = re.findall(r"`((?:git|gh) [^`]+)`", text)
        self.assertTrue(commands)
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(agent_guard.decide(command)[0], "allow")


@unittest.skipUnless(HAS_GIT, "git is not installed")
class MainBranchTests(unittest.TestCase):
    def project(self):
        p = TempProject({"README.md": "x\n"}, git=True)
        p.__enter__()
        self.addCleanup(p.__exit__, None, None, None)
        p.run_git("add", "-A")
        p.run_git("commit", "-q", "-m", "init")
        p.run_git("remote", "add", "origin", "https://example.invalid/o/r.git")
        return p

    def test_first_push_of_main_is_allowed(self):
        p = self.project()
        self.assertEqual(agent_guard.decide("git push -u origin main", root=p.root)[0], "allow")

    def test_main_changes_only_through_a_pull_request_once_published(self):
        p = self.project()
        p.run_git("update-ref", "refs/remotes/origin/main", "HEAD")
        for command in ("git push origin main", "git push origin HEAD:main", "git push"):
            with self.subTest(command=command):
                decision, reason = agent_guard.decide(command, root=p.root)
                self.assertEqual(decision, "deny")
                self.assertIn("pull request", reason)
        p.run_git("switch", "-q", "-c", "feat/r1-sign-in")
        for command in ("git push", "git push -u origin feat/r1-sign-in", "git push --force-with-lease"):
            with self.subTest(command=command):
                self.assertEqual(agent_guard.decide(command, root=p.root)[0], "allow")


class HookTests(unittest.TestCase):
    def run_hook(self, payload, root):
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(root))
        raw = payload if isinstance(payload, str) else json.dumps(payload)
        return subprocess.run(
            [sys.executable, "-B", str(QUALITY / "agent_guard.py")],
            input=raw, capture_output=True, text=True, env=env, check=False,
        )

    def test_a_denied_command_is_explained_to_the_agent_and_logged(self):
        with TempProject() as p:
            token = "ghp_" + "a" * 36
            payload = {
                "tool_name": "Bash", "cwd": str(p.root), "agent_id": "a1", "agent_type": "implementer",
                "tool_input": {"command": f"git push https://me:{token}@github.com/o/r.git HEAD"},
            }
            result = self.run_hook(payload, p.root)
            self.assertEqual(result.returncode, 0, result.stderr)
            out = json.loads(result.stdout)["hookSpecificOutput"]
            self.assertEqual(out["hookEventName"], "PreToolUse")
            self.assertEqual(out["permissionDecision"], "deny")
            self.assertIn("Only the lead", out["permissionDecisionReason"])
            entry = json.loads(p.read("logs/agent-guard.log").splitlines()[-1])
            self.assertEqual((entry["decision"], entry["agent"]), ("deny", "implementer"))
            self.assertNotIn(token, entry["command"])
            self.assertRegex(entry["time"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_ask_goes_to_the_user(self):
        with TempProject() as p:
            payload = {"tool_name": "Bash", "cwd": str(p.root), "tool_input": {"command": "gh pr merge 3 --squash"}}
            out = json.loads(self.run_hook(payload, p.root).stdout)["hookSpecificOutput"]
            self.assertEqual(out["permissionDecision"], "ask")

    def test_allowed_and_unrelated_calls_print_nothing(self):
        with TempProject() as p:
            for payload in (
                {"tool_name": "Bash", "cwd": str(p.root), "tool_input": {"command": "git status"}},
                {"tool_name": "Read", "cwd": str(p.root), "tool_input": {"file_path": "README.md"}},
                "not json",
            ):
                with self.subTest(payload=payload):
                    result = self.run_hook(payload, p.root)
                    self.assertEqual((result.returncode, result.stdout), (0, ""))
            self.assertFalse((p.root / "logs").exists())


class CommandLineTests(unittest.TestCase):
    def test_check_one_command(self):
        code, out = run_main(agent_guard.main, ["--command", "git push --force origin feat/x"])
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("deny: "), out)
        code, out = run_main(agent_guard.main, ["--command", "git commit -m x", "--agent", "implementer"])
        self.assertEqual(code, 1)
        code, out = run_main(agent_guard.main, ["--command", "git status"])
        self.assertEqual((code, out.strip()), (0, "allow"))


if __name__ == "__main__":
    unittest.main()
