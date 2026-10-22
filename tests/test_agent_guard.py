"""agent_guard.py: the PreToolUse hook that enforces the repository rules for agents."""
import json
import os
import re
import subprocess
import sys
import unittest
from unittest import mock

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

# The browser rules apply to the lead and to every subagent alike.
BROWSER_ALLOWED = [
    "./node_modules/.bin/playwright-cli open http://localhost:5173",
    "./node_modules/.bin/playwright-cli goto http://127.0.0.1:5173/markers",
    "playwright-cli -s=r7 tab-new http://app.localhost:3000",
    "pnpm exec playwright-cli goto 'http://[::1]:8000/'",
    "playwright-cli goto localhost:5173/sign-in",
    "playwright-cli goto /settings",
    "playwright-cli open",
    "playwright-cli open --headed --mobile http://localhost:5173",
    "playwright-cli open --browser chrome http://localhost:5173",
    "playwright-cli click e15 && playwright-cli fill e7 'Spanish title' --submit",
    "playwright-cli snapshot && playwright-cli console error",
    "playwright-cli set-color-scheme dark && playwright-cli screenshot --filename=.playwright-cli/markers-dark.png",
    "playwright-cli requests && playwright-cli response-body 3",
    "playwright-cli state-save .playwright-cli/user.json",
    "PLAYWRIGHT_CLI_SESSION=r7 playwright-cli snapshot",
    "playwright-cli --help goto",
    "playwright-cli --version",
    "bun run playwright-cli close",
    "npx playwright test tests/e2e/markers.spec.ts",
    "grep -rn playwright-cli docs",
    "echo 'playwright-cli open https://example.com'",
]

BROWSER_DENIED = [
    ("playwright-cli open https://example.com", "local app"),
    ("playwright-cli goto https://staging.example.com/sign-in", "local app"),
    ("playwright-cli goto http://192.168.1.20:5173", "local app"),
    ("playwright-cli goto example.com", "local app"),
    ("playwright-cli goto http://localhost@evil.test/", "local app"),
    ("playwright-cli goto http://127.0.0.1.nip.io", "local app"),
    ("playwright-cli goto file:///etc/passwd", "local app"),
    ("playwright-cli goto 'javascript:alert(1)'", "local app"),
    ("playwright-cli tab-new http://localhost.evil.test", "local app"),
    ("pnpm exec playwright-cli goto https://evil.test", "local app"),
    ("npx playwright cli goto https://example.com", "local app"),
    ("bash -c 'playwright-cli goto https://example.com'", "local app"),
    ("npx playwright-cli open http://localhost:5173", "own copy"),
    ("bunx @playwright/cli open http://localhost:5173", "own copy"),
    ("pnpm dlx @playwright/cli@latest open", "own copy"),
    ("npm exec playwright-cli open", "own copy"),
    ("playwright-cli attach --extension=chrome", "page commands"),
    ("playwright-cli attach --cdp=http://localhost:9222", "page commands"),
    ("playwright-cli show --port 9323 --host 0.0.0.0", "page commands"),
    ("playwright-cli run-code 'async page => page.goto(\"https://evil.test\")'", "page commands"),
    ("playwright-cli install --skills", "page commands"),
    ("playwright-cli install-browser chrome", "page commands"),
    ("playwright-cli tray", "page commands"),
    ("playwright-cli some-future-command", "page commands"),
    ("playwright-cli open --persistent http://localhost:5173", "profile"),
    ("playwright-cli open --profile=/tmp/chrome-profile http://localhost:5173", "profile"),
    ("playwright-cli --config /tmp/other.json open http://localhost:5173", "profile"),
    ("PLAYWRIGHT_MCP_CDP_ENDPOINT=http://localhost:9222 playwright-cli open", "profile"),
    ("env PLAYWRIGHT_MCP_ALLOWED_ORIGINS='*' playwright-cli open", "profile"),
]

# macOS escape routes: the Keychain and the developer's own browser.
MAC_DENIED = [
    ("security find-generic-password -s 'Claude Code-credentials' -w", "Keychain"),
    ("/usr/bin/security find-internet-password -s github.com -g", "Keychain"),
    ("security dump-keychain -d login.keychain", "Keychain"),
    ("security unlock-keychain ~/Library/Keychains/login.keychain-db", "Keychain"),
    ("security set-generic-password-partition-list -S apple-tool: -s x", "Keychain"),
    ("open https://example.com", "your own browser"),
    ("open -a 'Google Chrome' http://localhost:5173", "your own browser"),
    ("xdg-open https://example.com", "your own browser"),
    ("open 'slack://open'", "your own browser"),
]

MAC_ALLOWED = [
    "open /tmp/plan-preview/index.html",
    "open -a Safari docs/mockups/home.html",
    "open file:///tmp/plan-preview/index.html",
    "security find-certificate -a -c localhost",
]

# Asked when the lead runs them, denied for subagents.
SYSTEM_WIDE = [
    ("osascript -e 'tell application \"Google Chrome\" to get URL of active tab of front window'", "osascript"),
    ("npm install -g @playwright/cli@latest", "outside the project"),
    ("npm -g i ctx7", "outside the project"),
    ("pnpm add --global firebase-tools", "outside the project"),
    ("bun add -g some-tool", "outside the project"),
    ("yarn global add some-tool", "outside the project"),
    ("brew install gitleaks", "outside the project"),
    ("pipx install semgrep", "outside the project"),
    ("python3 -m pip install --user requests", "outside the project"),
    ("uv tool install ruff", "outside the project"),
]

PROJECT_INSTALLS = [
    "pnpm add -D @playwright/cli@0.1.22",
    "npm install",
    "bun install --frozen-lockfile",
    "pip install -r requirements.txt",
    "brew list",
    "brew info gh",
]

# Paths in the Read deny rules of the settings template, reached through the shell.
CREDENTIAL_READS = [
    "cat ~/.ssh/id_ed25519",
    "cat $HOME/.ssh/id_ed25519",
    "cat ${HOME}/.config/context7/credentials.json",
    "base64 < ~/.aws/credentials",
    "cp ~/.claude/.credentials.json /tmp/x",
    "cat ~/.docker/config.json",
    "tar czf /tmp/k.tgz ~/.kube",
    "cat ~/.context7/credentials.json",
    "grep token ~/.netrc",
    "openssl rsa -in certs/server.key -text",
    "python3 -c \"print(open('~/.ssh/id_rsa'.replace('~', '/Users/me')).read())\"",
    "echo $(cat ~/.git-credentials)",
    "cat ~/.claude/script-approvals/3f2a.json",
]

CREDENTIAL_SAFE = [
    "cat src/app.ts",
    "cat .env",
    "ls ~/.claude/projects",
    "cat ~/.ssh_notes.txt",
    "git log -- src/keys.ts",
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

    def test_browser_rules_apply_to_every_agent(self):
        for agent in (None, "test-runner", "designer"):
            self.check([(c,) for c in BROWSER_ALLOWED], "allow", agent=agent)
            self.check(BROWSER_DENIED, "deny", agent=agent)

    def test_every_browser_command_in_the_testing_rules_is_allowed(self):
        # docs/TESTING.md shows the agents how to check a change in the browser; the guard must let those commands through.
        text = (KIT / "references" / "testing.md").read_text(encoding="utf-8")
        section = text.split("## Browser checks by agents")[1].split("\n## ")[0]
        commands = re.findall(r"`(playwright-cli [^`]+)`", section)
        self.assertTrue(commands)
        for command in commands:
            with self.subTest(command=command):
                self.assertEqual(agent_guard.decide(command, agent="test-runner")[0], "allow")

    def test_keychain_and_own_browser_stay_out_of_reach(self):
        for agent in (None, "implementer"):
            self.check(MAC_DENIED, "deny", agent=agent)
            self.check([(c,) for c in MAC_ALLOWED], "allow", agent=agent)

    def test_system_wide_changes_ask_the_user(self):
        self.check(SYSTEM_WIDE, "ask")
        self.check(SYSTEM_WIDE, "deny", agent="implementer")
        self.check([(c,) for c in PROJECT_INSTALLS], "allow")


class ProjectFileTests(unittest.TestCase):
    def project(self, settings=True):
        files = {"tests/fixtures/photo.jpg": "x"}
        if settings:
            files[".claude/settings.json"] = (KIT / "templates" / "claude" / "settings.json").read_text(encoding="utf-8")
        p = TempProject(files)
        p.__enter__()
        self.addCleanup(p.__exit__, None, None, None)
        return p

    def test_browser_files_stay_inside_the_project(self):
        p = self.project()
        for command in (
            f"playwright-cli upload {p.root}/tests/fixtures/photo.jpg",
            "playwright-cli state-load .playwright-cli/user.json",
        ):
            with self.subTest(command=command):
                self.assertEqual(agent_guard.decide(command, root=p.root)[0], "allow")
        for command in (
            "playwright-cli upload /etc/hosts",
            f"playwright-cli upload {p.root}/../passport.pdf",
            "playwright-cli state-load /tmp/real-session.json",
            "playwright-cli state-save ~/session.json",
        ):
            with self.subTest(command=command):
                decision, reason = agent_guard.decide(command, root=p.root)
                self.assertEqual(decision, "deny")
                self.assertIn("inside the project", reason)

    def test_shell_reads_of_deny_listed_paths_are_denied(self):
        p = self.project()
        home = os.path.expanduser("~")
        for agent in (None, "implementer"):
            around = os.path.relpath(os.path.join(home, ".aws", "config"), p.root)
            for command in CREDENTIAL_READS + [f"cat {home}/.ssh/id_rsa", f"cat {around}"]:
                with self.subTest(command=command, agent=agent):
                    decision, reason = agent_guard.decide(command, agent=agent, root=p.root)
                    self.assertEqual(decision, "deny")
                    self.assertIn("keys and logins", reason)
            for command in CREDENTIAL_SAFE:
                with self.subTest(command=command, agent=agent):
                    self.assertEqual(agent_guard.decide(command, agent=agent, root=p.root)[0], "allow")

    def test_the_deny_list_comes_from_the_project_settings(self):
        p = self.project(settings=False)
        self.assertEqual(agent_guard.decide("cat ~/.ssh/id_ed25519", root=p.root)[0], "allow")
        p.write(".claude/settings.json", json.dumps({"permissions": {"deny": ["Read(~/.secrets/**)", "Bash(rm -rf *)"]}}))
        self.assertEqual(agent_guard.decide("cat ~/.secrets/token", root=p.root)[0], "deny")
        self.assertEqual(agent_guard.decide("cat ~/.ssh/id_ed25519", root=p.root)[0], "allow")


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

    def test_the_hook_reads_the_deny_list_of_the_project(self):
        settings = (KIT / "templates" / "claude" / "settings.json").read_text(encoding="utf-8")
        with TempProject({".claude/settings.json": settings, "src/.keep": ""}) as p:
            payload = {"tool_name": "Bash", "cwd": str(p.root / "src"), "tool_input": {"command": "cat ~/.ssh/id_ed25519"}}
            out = json.loads(self.run_hook(payload, p.root).stdout)["hookSpecificOutput"]
            self.assertEqual(out["permissionDecision"], "deny")
            self.assertIn("keys and logins", out["permissionDecisionReason"])

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


SCRIPT_FILES = {
    "scripts/tool.py": "import common\n",
    "scripts/common.py": "X = 1\n",
    "scripts/notes.md": "notes\n",
    "scripts/run.sh": "echo hi\n",
    "app/index.js": "console.log(1)\n",
    "app/util.ts": "export const a = 1\n",
    "node_modules/x/bin.js": "x\n",
    ".venv/bin/tool.py": "x\n",
}

# Commands that run project code: the key is the folder and language whose files the approval covers.
SCRIPT_RUNS = [
    ("python3 scripts/tool.py --dry-run", "scripts/*.py"),
    ("python3 -I -B scripts/tool.py", "scripts/*.py"),
    ("python3.12 -W ignore scripts/tool.py", "scripts/*.py"),
    ("cd scripts && python3 tool.py", "scripts/*.py"),
    ("python3 -m scripts.tool", "scripts/*.py"),
    ("FOO=1 timeout 60 python3 scripts/tool.py | tail -5", "scripts/*.py"),
    ("echo $(python3 scripts/tool.py)", "scripts/*.py"),
    ("bash scripts/run.sh", "scripts/*.sh"),
    ("./scripts/run.sh", "scripts/*.sh"),
    ("sh -c 'scripts/run.sh'", "scripts/*.sh"),
    ("source scripts/run.sh", "scripts/*.sh"),
    ("node app/index.js", "app/*.{js,ts}"),
    ("bun run app/util.ts", "app/*.{js,ts}"),
]

# Commands that run no project file: inline code, stdin, dependencies, files outside the project, or nothing at all.
NO_SCRIPT_RUNS = [
    "python3 -c 'print(1)'",
    "python3 -Ic 'print(1)'",
    "python3 - <<'EOF'\nprint(1)\nEOF",
    "python3 --version",
    "python3 -m pytest",
    "node -e 'console.log(1)'",
    "node node_modules/x/bin.js",
    "python3 .venv/bin/tool.py",
    "cat scripts/tool.py",
    "pnpm test",
    "bun run dev",
    "git status",
]


class ScriptRunTests(unittest.TestCase):
    def project(self):
        p = TempProject(SCRIPT_FILES)
        p.__enter__()
        self.addCleanup(p.__exit__, None, None, None)
        return p

    def test_finds_the_project_code_a_command_runs(self):
        p = self.project()
        for command, key in SCRIPT_RUNS:
            with self.subTest(command=command):
                self.assertEqual(list(agent_guard.scripts_run(command, root=p.root)), [key])
        for command in NO_SCRIPT_RUNS:
            with self.subTest(command=command):
                self.assertEqual(agent_guard.scripts_run(command, root=p.root), {})

    def test_files_outside_the_project_are_not_checked(self):
        p = self.project()
        with TempProject({"elsewhere.py": "x\n"}) as other:
            self.assertEqual(agent_guard.scripts_run(f"python3 {other.root}/elsewhere.py", root=p.root), {})

    def test_the_fingerprint_covers_the_files_a_script_can_import(self):
        p = self.project()
        before = agent_guard.scripts_run("python3 scripts/tool.py", root=p.root)
        p.write("scripts/notes.md", "other notes\n")
        self.assertEqual(agent_guard.scripts_run("python3 scripts/tool.py", root=p.root), before)
        p.write("scripts/common.py", "X = 2\n")
        self.assertNotEqual(agent_guard.scripts_run("python3 scripts/tool.py", root=p.root), before)


class ScriptApprovalHookTests(unittest.TestCase):
    """The hook asks before project code it has not seen approved, and records the approval once the command runs."""

    def setUp(self):
        self.home = TempProject()
        self.home.__enter__()
        self.addCleanup(self.home.__exit__, None, None, None)
        self.p = TempProject(SCRIPT_FILES)
        self.p.__enter__()
        self.addCleanup(self.p.__exit__, None, None, None)

    def hook(self, command, event="PreToolUse", tool_use_id="toolu_1"):
        payload = {
            "hook_event_name": event, "tool_name": "Bash", "cwd": str(self.p.root),
            "tool_use_id": tool_use_id, "tool_input": {"command": command},
        }
        env = dict(os.environ, CLAUDE_PROJECT_DIR=str(self.p.root), HOME=str(self.home.root))
        result = subprocess.run(
            [sys.executable, "-B", str(QUALITY / "agent_guard.py")],
            input=json.dumps(payload), capture_output=True, text=True, env=env, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)["hookSpecificOutput"] if result.stdout else None

    def test_asks_until_the_code_runs_once_approved_and_again_after_a_change(self):
        out = self.hook("python3 scripts/tool.py")
        self.assertEqual(out["permissionDecision"], "ask")
        self.assertIn("scripts/*.py", out["permissionDecisionReason"])
        self.assertIsNone(self.hook("python3 scripts/tool.py", event="PostToolUse"))
        self.assertIsNone(self.hook("python3 scripts/tool.py", tool_use_id="toolu_2"))
        self.assertIsNone(self.hook("python3 -m scripts.tool", tool_use_id="toolu_3"))
        self.p.write("scripts/common.py", "X = 2\n")
        out = self.hook("python3 scripts/tool.py", tool_use_id="toolu_4")
        self.assertEqual(out["permissionDecision"], "ask")
        self.assertIn("changed", out["permissionDecisionReason"])

    def test_a_failed_run_still_counts_as_approved(self):
        self.hook("bash scripts/run.sh")
        self.hook("bash scripts/run.sh", event="PostToolUseFailure")
        self.assertIsNone(self.hook("bash scripts/run.sh", tool_use_id="toolu_2"))

    def test_a_refused_command_approves_nothing(self):
        self.hook("python3 scripts/tool.py")
        # No PostToolUse: the user said no, so the command never ran.
        self.assertEqual(self.hook("python3 scripts/tool.py", tool_use_id="toolu_2")["permissionDecision"], "ask")
        self.hook("python3 scripts/tool.py", event="PostToolUse", tool_use_id="toolu_9")
        self.assertEqual(self.hook("python3 scripts/tool.py", tool_use_id="toolu_3")["permissionDecision"], "ask")

    def test_deny_wins_and_records_nothing(self):
        out = self.hook("python3 scripts/tool.py && git push -f origin feat/x")
        self.assertEqual(out["permissionDecision"], "deny")
        self.hook("python3 scripts/tool.py && git push -f origin feat/x", event="PostToolUse")
        self.assertEqual(self.hook("python3 scripts/tool.py", tool_use_id="toolu_2")["permissionDecision"], "ask")

    def test_another_ask_keeps_both_reasons(self):
        out = self.hook("python3 scripts/tool.py && gh pr merge 3 --squash")
        self.assertEqual(out["permissionDecision"], "ask")
        self.assertIn("Merging", out["permissionDecisionReason"])
        self.assertIn("scripts/*.py", out["permissionDecisionReason"])

    def test_approvals_live_outside_the_repository(self):
        self.hook("python3 scripts/tool.py")
        self.hook("python3 scripts/tool.py", event="PostToolUse")
        ledgers = list((self.home.root / ".claude" / "script-approvals").glob("*.json"))
        self.assertEqual(len(ledgers), 1)
        ledger = json.loads(ledgers[0].read_text(encoding="utf-8"))
        self.assertEqual(list(ledger["approved"]), ["scripts/*.py"])
        self.assertEqual(ledger["pending"], {})
        self.assertFalse(any("approval" in f.name for f in self.p.root.rglob("*")))

    def test_commands_without_project_code_leave_no_trace(self):
        for command in ("git status", "python3 -c 'print(1)'", "pnpm test"):
            with self.subTest(command=command):
                self.assertIsNone(self.hook(command))
                self.assertIsNone(self.hook(command, event="PostToolUse"))
        self.assertFalse((self.home.root / ".claude").exists())


class CommandLineTests(unittest.TestCase):
    def test_check_one_command(self):
        code, out = run_main(agent_guard.main, ["--command", "git push --force origin feat/x"])
        self.assertEqual(code, 1)
        self.assertTrue(out.startswith("deny: "), out)
        code, out = run_main(agent_guard.main, ["--command", "git commit -m x", "--agent", "implementer"])
        self.assertEqual(code, 1)
        code, out = run_main(agent_guard.main, ["--command", "git status"])
        self.assertEqual((code, out.strip()), (0, "allow"))

    def test_the_command_line_shows_the_script_question(self):
        with TempProject(SCRIPT_FILES) as p, TempProject() as home, mock.patch.dict(os.environ, {"HOME": str(home.root)}):
            code, out = run_main(agent_guard.main, ["--command", "python3 scripts/tool.py", "--root", str(p.root)])
            self.assertEqual(code, 1)
            self.assertTrue(out.startswith("ask: "), out)
            self.assertFalse((home.root / ".claude").exists(), "checking a command records nothing")


if __name__ == "__main__":
    unittest.main()
