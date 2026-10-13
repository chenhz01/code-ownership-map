#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""code-ownership-map — path x owner matrix from CODEOWNERS + file tree.

Parses a GitHub-style CODEOWNERS file and a file list (e.g. `git ls-files`
output), resolves the owning team/user for every file (last matching pattern
wins, GitHub semantics), and reports: coverage, orphan paths, per-owner
load, and single-owner (bus-factor) hotspots. Reads two local files only —
no git, no network, no API calls. Pure stdlib.
"""
import argparse
import fnmatch
import json
import re
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", newline="\n")
    sys.stderr.reconfigure(encoding="utf-8", newline="\n")
except Exception:
    pass

VERSION = "0.1.1"


class OwnError(Exception):
    """Input problem that maps to exit code 2."""


def valid_owner(tok):
    """Owner is @user, @org/team, or an email containing @."""
    return tok.startswith("@") or ("@" in tok and not tok.startswith("@@"))


def parse_codeowners(text):
    """Parse CODEOWNERS. Returns (rules, bad_lines).
    rules: list of (pattern, owners, lineno) in file order."""
    rules, bad = [], []
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 2 or not all(valid_owner(p) for p in parts[1:]):
            bad.append({"lineno": lineno, "line": line})
            continue
        rules.append((parts[0], parts[1:], lineno))
    return rules, bad


def pattern_matches(pattern, path):
    """GitHub-style CODEOWNERS matching (simplified, documented):
    - pattern ending with '/': matches any file under that directory
    - pattern containing '/': anchored to repo root
    - otherwise (e.g. '*.md' or 'Makefile'): matches the basename at any level
    """
    p = pattern.rstrip("/")
    path_norm = path.replace("\\", "/")
    if pattern.endswith("/"):
        prefix = p.lstrip("/") + "/"
        return path_norm.startswith(prefix)
    if "/" in p:
        anchor = p.lstrip("/")
        return path_norm == anchor or path_norm.startswith(anchor + "/")
    base = path_norm.rsplit("/", 1)[-1]
    return fnmatch.fnmatch(base, p)


def resolve_owners(rules, path):
    """Last matching pattern wins (GitHub semantics). Returns owners list."""
    owners = []
    for pattern, owns, _ in rules:
        if pattern_matches(pattern, path):
            owners = owns
    return owners


def load_tree(path):
    """Load file list, one path per line. Returns (paths, bad_lines)."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError as e:
        raise OwnError("cannot read tree file: %s" % e)
    paths, bad = [], 0
    status_rx = re.compile(r"^[MADRC?!U]{1,2}\s")
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        if ln.startswith((";", "#")) or "\t" in ln or status_rx.match(ln):
            bad += 1
            continue
        paths.append(ln.replace("\\", "/"))
    return paths, bad


def load_codeowners_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError as e:
        raise OwnError("cannot read CODEOWNERS file: %s" % e)


def build_map(rules, paths):
    """Core mapping. Returns report dict."""
    per_owner = {}
    orphans = []
    single_owner_files = []
    top_dirs = {}
    matrix = {}

    for p in paths:
        owners = resolve_owners(rules, p)
        d = p.split("/")[0] if "/" in p else "(root)"
        top_dirs[d] = top_dirs.get(d, 0) + 1
        matrix.setdefault(d, {"(unowned)": 0})
        if not owners:
            orphans.append(p)
            matrix[d]["(unowned)"] += 1
            continue
        for o in owners:
            per_owner[o] = per_owner.get(o, 0) + 1
        if len(owners) == 1:
            single_owner_files.append(p)
        for o in owners:
            matrix[d][o] = matrix[d].get(o, 0) + 1

    total = len(paths)
    covered = total - len(orphans)
    coverage_pct = round(100.0 * covered / total, 1) if total else 100.0
    return {
        "schema": "code-ownership-map/v1",
        "files": total,
        "covered": covered,
        "coverage_pct": coverage_pct,
        "orphans": orphans[:20],
        "orphan_count": len(orphans),
        "per_owner": dict(sorted(per_owner.items(), key=lambda kv: -kv[1])),
        "single_owner_files": single_owner_files[:20],
        "single_owner_count": len(single_owner_files),
        "top_dirs": dict(sorted(top_dirs.items(), key=lambda kv: -kv[1])[:10]),
        "matrix": matrix,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="code-ownership-map",
        description="Build a path x owner map from CODEOWNERS + a file list; find orphans and bus-factor hotspots.")
    parser.add_argument("--version", action="version", version="%(prog)s " + VERSION)
    sub = parser.add_subparsers(dest="cmd")

    p = sub.add_parser("map", help="map ownership for a file tree")
    p.add_argument("--codeowners", required=True, help="CODEOWNERS file path")
    p.add_argument("--tree", required=True, help="file list (one path per line, e.g. git ls-files)")
    p.add_argument("--json", action="store_true")
    p.add_argument("--min-coverage", type=float, default=None,
                   help="exit 1 when coverage %% falls below this")

    args = parser.parse_args(argv)
    if args.cmd != "map":
        parser.print_usage(sys.stderr)
        return 2
    try:
        rules, bad_rules = parse_codeowners(load_codeowners_file(args.codeowners))
        paths, bad_tree = load_tree(args.tree)
        report = build_map(rules, paths)
        report["bad_codeowners_lines"] = len(bad_rules)
        report["bad_tree_lines"] = bad_tree
    except OwnError as e:
        print("error: %s" % e, file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=True, indent=2))
    else:
        print("code-ownership-map: %d file(s), coverage %.1f%%, orphans %d, "
              "single-owner %d, owners %d"
              % (report["files"], report["coverage_pct"], report["orphan_count"],
                 report["single_owner_count"], len(report["per_owner"])))
        for o, n in list(report["per_owner"].items())[:5]:
            print("  %-24s %d file(s)" % (o, n))
        if report["orphan_count"]:
            print("  orphan sample: %s" % ", ".join(report["orphans"][:3]))
        if bad_rules:
            print("  note: %d CODEOWNERS line(s) ignored (bad format)" % len(bad_rules))
        if bad_tree:
            print("  note: %d tree line(s) ignored" % bad_tree)

    if args.min_coverage is not None and report["coverage_pct"] < args.min_coverage:
        print("error: coverage %.1f%% below minimum %.1f%%"
              % (report["coverage_pct"], args.min_coverage), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
