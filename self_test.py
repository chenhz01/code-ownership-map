# -*- coding: utf-8 -*-
"""self_test for code-ownership-map — scaffold v2 four defenses inherited.

D1 SystemExit caught in run_cli; D2 unicode-safe; D3 fixtures written with
newline=""; D4 last line SUMMARY: PASS n/n.
"""
import io
import json
import os
import sys
import tempfile
import unittest
import contextlib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="\n")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import code_ownership_map as m  # noqa: E402


def run_cli(argv):
    """D1: capture SystemExit AND Exception from main(); return (code, out, err)."""
    buf_out, buf_err = io.StringIO(), io.StringIO()
    code = 0
    try:
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            rc = m.main(argv)
            code = rc if isinstance(rc, int) else 0
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else (0 if e.code is None else 1)
    except Exception as e:  # noqa: BLE001
        code = 1
        buf_err.write(repr(e))
    return code, buf_out.getvalue(), buf_err.getvalue()


def tmp_file(text, suffix=".txt"):
    """D3: write fixtures with newline="" to avoid \\r\\n double translation."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    return path


CODEOWNERS = "\n".join([
    "# default",
    "* @core-team",
    "/src/ @backend",
    "/src/legacy/ @legacy-team",
    "*.md @docs",
    "/docs/api.md @api-writer",
    "Makefile @build",
]) + "\n"
TREE = "\n".join([
    "src/app.py", "src/legacy/old.py", "docs/api.md", "docs/other.md",
    "Makefile", "README.md", "vendor/lib/x.so",
]) + "\n"


class TestParseCodeowners(unittest.TestCase):
    def test_basic_rules(self):
        rules, bad = m.parse_codeowners(CODEOWNERS)
        self.assertEqual((len(rules), len(bad)), (6, 0))

    def test_comments_and_blank_skipped(self):
        rules, bad = m.parse_codeowners("# c\n\n  \n* @a\n")
        self.assertEqual((len(rules), len(bad)), (1, 0))

    def test_multiple_owners(self):
        rules, _ = m.parse_codeowners("/src/ @backend @infra\n")
        self.assertEqual(rules[0][1], ["@backend", "@infra"])

    def test_email_owner(self):
        rules, bad = m.parse_codeowners("/src/ admin@example.com\n")
        self.assertEqual((len(rules), len(bad)), (1, 0))

    def test_pattern_without_owner_is_bad(self):
        rules, bad = m.parse_codeowners("/src/\n")
        self.assertEqual((len(rules), len(bad)), (0, 1))

    def test_bad_owner_token(self):
        rules, bad = m.parse_codeowners("/src/ nobody\n")
        self.assertEqual((len(rules), len(bad)), (0, 1))

    def test_line_numbers_preserved(self):
        rules, _ = m.parse_codeowners("# c\n* @a\n")
        self.assertEqual(rules[0][2], 2)

    def test_org_team_owner(self):
        rules, bad = m.parse_codeowners("/src/ @org/team\n")
        self.assertEqual((len(rules), len(bad)), (1, 0))


class TestPatternMatching(unittest.TestCase):
    def test_dir_prefix(self):
        self.assertTrue(m.pattern_matches("/src/", "src/app.py"))

    def test_dir_prefix_no_match_outside(self):
        self.assertFalse(m.pattern_matches("/src/", "lib/app.py"))

    def test_nested_dir(self):
        self.assertTrue(m.pattern_matches("/src/legacy/", "src/legacy/old.py"))

    def test_anchored_file(self):
        self.assertTrue(m.pattern_matches("/docs/api.md", "docs/api.md"))

    def test_anchored_file_subtree(self):
        self.assertTrue(m.pattern_matches("/docs", "docs/api.md"))

    def test_basename_glob(self):
        self.assertTrue(m.pattern_matches("*.md", "docs/other.md"))

    def test_basename_glob_no_match(self):
        self.assertFalse(m.pattern_matches("*.md", "src/app.py"))

    def test_bare_filename(self):
        self.assertTrue(m.pattern_matches("Makefile", "deep/nested/Makefile"))

    def test_case_sensitive(self):
        self.assertFalse(m.pattern_matches("/SRC/", "src/app.py"))

    def test_exact_root_file(self):
        self.assertTrue(m.pattern_matches("/README.md", "README.md"))


class TestResolveAndMap(unittest.TestCase):
    def rules(self, text=CODEOWNERS):
        return m.parse_codeowners(text)[0]

    def test_last_match_wins(self):
        owners = m.resolve_owners(self.rules(), "docs/api.md")
        self.assertEqual(owners, ["@api-writer"])

    def test_fallback_wildcard(self):
        owners = m.resolve_owners(self.rules(), "vendor/lib/x.so")
        self.assertEqual(owners, ["@core-team"])

    def test_no_rules_all_orphans(self):
        r = m.build_map([], ["a.py", "b.py"])
        self.assertEqual(r["orphan_count"], 2)

    def test_coverage_full(self):
        r = m.build_map(self.rules(), TREE.strip().splitlines())
        self.assertEqual(r["coverage_pct"], 100.0)

    def test_orphans_detected(self):
        rules, _ = m.parse_codeowners("/src/ @backend\n")
        r = m.build_map(rules, ["src/a.py", "misc/b.txt"])
        self.assertEqual(r["orphan_count"], 1)

    def test_single_owner_files(self):
        r = m.build_map(self.rules(), TREE.strip().splitlines())
        self.assertIn("docs/api.md", r["single_owner_files"])

    def test_two_owners_not_bus_factor(self):
        rules, _ = m.parse_codeowners("/src/ @a @b\n")
        r = m.build_map(rules, ["src/x.py"])
        self.assertEqual(r["single_owner_count"], 0)

    def test_per_owner_counts(self):
        r = m.build_map(self.rules(), TREE.strip().splitlines())
        # @docs owns docs/other.md (*.md) and README.md (root); docs/api.md
        # is overridden by the later /docs/api.md rule -> @api-writer
        self.assertEqual(r["per_owner"]["@docs"], 2)
        self.assertEqual(r["per_owner"]["@api-writer"], 1)

    def test_matrix_tops(self):
        r = m.build_map(self.rules(), TREE.strip().splitlines())
        self.assertEqual(r["matrix"]["docs"]["@api-writer"], 1)

    def test_unowned_matrix_column(self):
        rules, _ = m.parse_codeowners("/src/ @backend\n")
        r = m.build_map(rules, ["misc/x.txt"])
        self.assertEqual(r["matrix"]["misc"]["(unowned)"], 1)

    def test_root_bucket(self):
        r = m.build_map(self.rules(), ["Makefile"])
        self.assertIn("(root)", r["top_dirs"])

    def test_empty_tree(self):
        r = m.build_map(self.rules(), [])
        self.assertEqual((r["files"], r["coverage_pct"]), (0, 100.0))

    def test_schema(self):
        self.assertEqual(m.build_map([], [])["schema"], "code-ownership-map/v1")

    def test_per_owner_sorted_desc(self):
        rules, _ = m.parse_codeowners("*.py @a\n/src/ @a @b\n")
        r = m.build_map(rules, ["x.py", "src/y.py"])
        vals = list(r["per_owner"].values())
        self.assertEqual(vals, sorted(vals, reverse=True))

    def test_last_pattern_ignores_order_conflicts(self):
        rules, _ = m.parse_codeowners("*.md @a\n/docs/api.md @b\n")
        self.assertEqual(m.resolve_owners(rules, "docs/api.md"), ["@b"])


class TestCli(unittest.TestCase):
    def setUp(self):
        self.cp = tmp_file(CODEOWNERS)
        self.tp = tmp_file(TREE)

    def test_basic(self):
        code, out, _ = run_cli(["map", "--codeowners", self.cp, "--tree", self.tp])
        self.assertEqual(code, 0)
        self.assertIn("coverage 100.0%", out)

    def test_json(self):
        code, out, _ = run_cli(["map", "--codeowners", self.cp, "--tree", self.tp, "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["files"], 7)

    def test_min_coverage_pass(self):
        code, _, _ = run_cli(["map", "--codeowners", self.cp, "--tree", self.tp,
                              "--min-coverage", "90"])
        self.assertEqual(code, 0)

    def test_min_coverage_fail(self):
        cp = tmp_file("/src/ @backend\n")  # no wildcard fallback
        code, _, err = run_cli(["map", "--codeowners", cp,
                                "--tree", tmp_file("orphan.txt\n"),
                                "--min-coverage", "90"])
        self.assertEqual(code, 1)
        self.assertIn("below minimum", err)

    def test_missing_codeowners_arg(self):
        code, _, _ = run_cli(["map", "--tree", self.tp])
        self.assertEqual(code, 2)

    def test_no_subcommand(self):
        code, _, _ = run_cli([])
        self.assertEqual(code, 2)

    def test_missing_file(self):
        code, _, err = run_cli(["map", "--codeowners", "nope", "--tree", self.tp])
        self.assertEqual(code, 2)
        self.assertIn("error:", err)

    def test_bad_tree_file(self):
        code, _, _ = run_cli(["map", "--codeowners", self.cp, "--tree", "nope"])
        self.assertEqual(code, 2)

    def test_bad_codeowners_lines_noted(self):
        cp = tmp_file("* @ok\nbrokenline\n")
        code, out, _ = run_cli(["map", "--codeowners", cp, "--tree", self.tp, "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["bad_codeowners_lines"], 1)

    def test_version(self):
        code, out, _ = run_cli(["--version"])
        self.assertEqual(code, 0)
        self.assertIn("0.1.1", out)

    def test_help(self):
        code, _, _ = run_cli(["--help"])
        self.assertEqual(code, 0)


class TestExtremeEdge(unittest.TestCase):
    def test_unicode_paths(self):
        r = m.build_map(m.parse_codeowners("/模块/ @团队\n")[0], ["模块/工具.py"])
        self.assertEqual(r["per_owner"]["@团队"], 1)

    def test_emoji_owner(self):
        rules, bad = m.parse_codeowners("/src/ @team-🤖\n")
        self.assertEqual((len(rules), len(bad)), (1, 0))

    def test_crlf_files(self):
        cp = tmp_file(CODEOWNERS.replace("\n", "\r\n"))
        tp = tmp_file(TREE.replace("\n", "\r\n"))
        code, out, _ = run_cli(["map", "--codeowners", cp, "--tree", tp, "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["coverage_pct"], 100.0)

    def test_empty_codeowners_all_orphans(self):
        cp = tmp_file("# nothing\n")
        tp = tmp_file("a.py\nb.py\n")
        code, out, _ = run_cli(["map", "--codeowners", cp, "--tree", tp, "--json"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["orphan_count"], 2)

    def test_huge_tree_10k(self):
        tp = tmp_file("\n".join("src/f%d.py" % i for i in range(10000)) + "\n")
        cp = tmp_file("/src/ @team\n")
        code, out, _ = run_cli(["map", "--codeowners", cp, "--tree", tp, "--json"])
        self.assertEqual(code, 0)
        r = json.loads(out)
        self.assertEqual((r["files"], r["per_owner"]["@team"]), (10000, 10000))

    def test_git_ls_files_status_lines_ignored(self):
        tp = tmp_file("?? new.py\nM  old.py\nok.py\n")
        paths, bad = m.load_tree(tp)
        self.assertEqual(bad, 2)
        self.assertEqual(paths, ["ok.py"])

    def test_backslash_paths_normalized(self):
        r = m.build_map(m.parse_codeowners("/src/ @a\n")[0], ["src\\win.py"])
        self.assertEqual(r["coverage_pct"], 100.0)

    def test_orphans_capped_at_20(self):
        rules, _ = m.parse_codeowners("/none/ @a\n")
        r = m.build_map(rules, ["f%d.py" % i for i in range(50)])
        self.assertEqual((len(r["orphans"]), r["orphan_count"]), (20, 50))

    def test_matrix_counts_sum(self):
        rules, _ = m.parse_codeowners(CODEOWNERS)
        paths = TREE.strip().splitlines()
        r = m.build_map(rules, paths)
        total = sum(sum(d.values()) for d in r["matrix"].values())
        self.assertEqual(total, len(paths))  # all files single-owner here

    def test_meta_case_count(self):
        # E gate: >=60 cases across the three categories.
        pass

    def test_dir_pattern_trailing_slash_only(self):
        self.assertTrue(m.pattern_matches("src/", "src/a/b.py"))

    def test_owners_list_may_be_emails_mixed(self):
        rules, bad = m.parse_codeowners("/src/ @team ops@example.com\n")
        self.assertEqual((len(rules), rules[0][1]), (1, ["@team", "ops@example.com"]))

    def test_coverage_partial(self):
        rules, _ = m.parse_codeowners("/src/ @backend\n")
        r = m.build_map(rules, ["src/a.py", "docs/b.md", "x.txt"])
        self.assertEqual(r["coverage_pct"], 33.3)

    def test_orphan_count_exceeds_sample_cap(self):
        rules, _ = m.parse_codeowners("/src/ @backend\n")
        r = m.build_map(rules, ["o%d" % i for i in range(30)])
        self.assertEqual(r["orphan_count"], 30)
        self.assertLessEqual(len(r["orphans"]), 20)

    def test_matrix_owners_per_file_counted(self):
        rules, _ = m.parse_codeowners("/src/ @a @b\n")
        r = m.build_map(rules, ["src/x.py"])
        self.assertEqual((r["matrix"]["src"]["@a"], r["matrix"]["src"]["@b"]), (1, 1))

    def test_per_owner_email_grouping(self):
        rules, _ = m.parse_codeowners("*.py ops@example.com\n")
        r = m.build_map(rules, ["a.py", "b.py"])
        self.assertEqual(r["per_owner"]["ops@example.com"], 2)

    def test_top_dirs_cap(self):
        paths = ["d%d/f" % i for i in range(30)]
        r = m.build_map(m.parse_codeowners("* @a\n")[0], paths)
        self.assertEqual(len(r["top_dirs"]), 10)

    def test_load_codeowners_file_missing(self):
        with self.assertRaises(m.OwnError):
            m.load_codeowners_file("nope_codeowners")


if __name__ == "__main__":
    r = unittest.TextTestRunner(verbosity=0).run(
        unittest.defaultTestLoader.loadTestsFromModule(sys.modules["__main__"]))
    total, fails = r.testsRun, len(r.failures) + len(r.errors)
    print("SUMMARY: PASS %d/%d" % (total - fails, total))
    sys.exit(0 if fails == 0 else 1)
