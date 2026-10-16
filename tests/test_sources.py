import datetime
import json
import unittest

from helpers import KIT, TempProject, run_main

import common
import sources

SOURCES = (
    "# Trusted sources\n\n"
    "Last reviewed: 2026-10-01\n\n"
    "| Area | Sources |\n|---|---|\n"
    "| Vulnerabilities | [OSV](https://osv.dev/list), [KEV](https://www.cisa.gov/known-exploited-vulnerabilities-catalog) |\n"
    "| Registry | the package page on https://www.npmjs.com/package/x (not pre-approved) |\n"
    "| Platform | https://supabase.com/changelog and https://status.supabase.com/ |\n"
)
DOMAINS = ["osv.dev", "status.supabase.com", "supabase.com", "www.cisa.gov"]


def settings(*allow, **extra):
    return json.dumps({"permissions": {"allow": list(allow)}, **extra}, indent=2) + "\n"


def webfetch(*domains):
    return [f"WebFetch(domain:{d})" for d in domains]


class DomainTests(unittest.TestCase):
    def test_https_links_become_sorted_unique_domains(self):
        found, _http = sources.linked_domains(SOURCES + "Again: https://osv.dev/vulnerability/X\n")
        self.assertEqual(sources.preapproved(found, common.load_config(".")["sources"]["neverPreapprove"]), DOMAINS)

    def test_hosts_anyone_can_publish_on_are_never_preapproved(self):
        never = common.load_config(".")["sources"]["neverPreapprove"]
        found, _ = sources.linked_domains("https://github.com/advisories https://user.github.io/x https://osv.dev\n")
        self.assertEqual(sources.preapproved(found, never), ["osv.dev"])

    def test_http_links_are_reported_with_their_line(self):
        _found, http = sources.linked_domains("# S\n\nhttp://example.com/feed\n")
        self.assertEqual(http, [(3, "http://example.com/feed")])

    def test_review_date_warns_when_old(self):
        today = datetime.date(2027, 6, 1)
        self.assertIsNotNone(sources.review_warning(SOURCES, today, 180))
        self.assertIsNone(sources.review_warning(SOURCES, datetime.date(2026, 11, 1), 180))
        self.assertIsNotNone(sources.review_warning("# S\n", today, 180))


class CheckTests(unittest.TestCase):
    def run_check(self, files):
        with TempProject(files) as p:
            return run_main(sources.main, ["--root", str(p.root), "check"])

    def test_passes_when_rules_match_the_sources(self):
        code, out = self.run_check({
            "docs/SOURCES.md": SOURCES,
            ".claude/settings.json": settings("Bash(git status)", *webfetch(*DOMAINS)),
        })
        self.assertEqual(code, 0, out)

    def test_rule_for_an_unlisted_domain_fails(self):
        code, out = self.run_check({
            "docs/SOURCES.md": SOURCES,
            ".claude/settings.json": settings(*webfetch(*DOMAINS, "evil.example")),
        })
        self.assertEqual(code, 1)
        self.assertIn("evil.example", out)

    def test_missing_rule_fails_and_suggests_sync(self):
        code, out = self.run_check({
            "docs/SOURCES.md": SOURCES,
            ".claude/settings.json": settings(*webfetch(*DOMAINS[1:])),
        })
        self.assertEqual(code, 1)
        self.assertIn("osv.dev", out)
        self.assertIn("sync", out)

    def test_bare_and_wildcard_rules_fail(self):
        for rule in ("WebFetch", "WebFetch(domain:*)", "WebFetch(domain:*.supabase.com)"):
            with self.subTest(rule=rule):
                code, out = self.run_check({
                    "docs/SOURCES.md": SOURCES,
                    ".claude/settings.json": settings(rule, *webfetch(*DOMAINS)),
                })
                self.assertEqual(code, 1, out)

    def test_never_preapproved_host_fails_even_if_linked(self):
        code, out = self.run_check({
            "docs/SOURCES.md": SOURCES + "https://github.com/advisories\n",
            ".claude/settings.json": settings(*webfetch(*DOMAINS, "github.com")),
        })
        self.assertEqual(code, 1)
        self.assertIn("github.com", out)

    def test_http_link_fails(self):
        code, out = self.run_check({
            "docs/SOURCES.md": SOURCES + "http://insecure.example/feed\n",
            ".claude/settings.json": settings(*webfetch(*DOMAINS, "insecure.example")),
        })
        self.assertEqual(code, 1)
        self.assertIn("docs/SOURCES.md:10", out)

    def test_missing_files_fail(self):
        code, out = self.run_check({".claude/settings.json": settings()})
        self.assertEqual(code, 1)
        self.assertIn("docs/SOURCES.md", out)
        code, out = self.run_check({"docs/SOURCES.md": SOURCES})
        self.assertEqual(code, 1)
        self.assertIn("sync", out)

    def test_settings_file_can_be_turned_off(self):
        code, out = self.run_check({
            "docs/SOURCES.md": SOURCES,
            "quality.config.json": '{"sources": {"settingsFile": null}}',
        })
        self.assertEqual(code, 0, out)

    def test_invalid_settings_json_is_a_usage_error(self):
        code, _out = self.run_check({"docs/SOURCES.md": SOURCES, ".claude/settings.json": "{"})
        self.assertEqual(code, 2)


class SyncTests(unittest.TestCase):
    def test_sync_rewrites_only_webfetch_rules_and_is_idempotent(self):
        before = settings("Bash(git status)", "WebFetch(domain:old.example)", "WebFetch", env={"A": "1"})
        with TempProject({"docs/SOURCES.md": SOURCES, ".claude/settings.json": before}) as p:
            code, out = run_main(sources.main, ["--root", str(p.root), "sync"])
            self.assertEqual(code, 0, out)
            first = (p.root / ".claude" / "settings.json").read_text(encoding="utf-8")
            data = json.loads(first)
            self.assertEqual(data["env"], {"A": "1"})
            self.assertEqual(data["permissions"]["allow"], ["Bash(git status)"] + webfetch(*DOMAINS))
            run_main(sources.main, ["--root", str(p.root), "sync"])
            self.assertEqual((p.root / ".claude" / "settings.json").read_text(encoding="utf-8"), first)
            code, out = run_main(sources.main, ["--root", str(p.root), "check"])
            self.assertEqual(code, 0, out)

    def test_sync_creates_the_settings_file(self):
        with TempProject({"docs/SOURCES.md": SOURCES}) as p:
            code, out = run_main(sources.main, ["--root", str(p.root), "sync"])
            self.assertEqual(code, 0, out)
            data = json.loads((p.root / ".claude" / "settings.json").read_text(encoding="utf-8"))
            self.assertEqual(data["permissions"]["allow"], webfetch(*DOMAINS))

    def test_domains_prints_one_per_line(self):
        with TempProject({"docs/SOURCES.md": SOURCES}) as p:
            code, out = run_main(sources.main, ["--root", str(p.root), "domains"])
        self.assertEqual(code, 0)
        self.assertEqual(out.split(), DOMAINS)


class ReferenceTests(unittest.TestCase):
    def test_kit_reference_links_only_over_https(self):
        text = (KIT / "references" / "sources.md").read_text(encoding="utf-8")
        found, http = sources.linked_domains(text)
        self.assertEqual(http, [])
        never = common.load_config(".")["sources"]["neverPreapprove"]
        self.assertGreater(len(sources.preapproved(found, never)), 10)


if __name__ == "__main__":
    unittest.main()
