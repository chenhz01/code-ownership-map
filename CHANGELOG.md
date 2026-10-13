# Changelog

## v0.1.1 (2026-10-13)

Round-2 revisions after first-draft self-review (5 failing tests: 3 wrong
test expectations, 1 bad fixture, 1 real parser gap):

- **Parser fix:** `git ls-files` status-prefixed lines (`M  file`,
  `?? file`) were silently accepted as paths; now filtered and counted as
  bad tree lines.
- Test expectations corrected against the actual (GitHub-faithful)
  semantics: rule count in the default fixture, @docs owning 2 files
  (*.md + root README), matrix sum for all-single-owner trees.
- Coverage-fail CLI fixture rebuilt (previous fixture had a wildcard
  fallback that made the gate untestable).
- Suite raised 54 -> 62 cases (trailing-slash dirs, mixed email owners,
  partial coverage, sample caps, matrix multi-owner, email grouping,
  top-dirs cap, missing-file error); re-run green (SUMMARY: PASS 62/62).
- Performance measured: 40.0 ms per 10k-file map [Measured].

## v0.1.0 (2026-10-13)

First draft:

- CODEOWNERS parser (comments, @user/@org/team/email owners, bad-line
  counting) with documented simplified GitHub matching semantics:
  trailing-slash subtrees, anchored patterns, basename globs,
  last-match-wins resolution.
- Tree loader with status-line/comment/tab filtering and path
  normalization (backslash -> slash).
- Report: coverage %, orphan sample+count, per-owner load (sorted),
  single-owner (bus-factor) hotspots, top-level dir buckets, dir x owner
  matrix; --min-coverage CI gate (exit 1).
- argparse CLI (`map`), self_test with scaffold-v2 four defenses,
  README, LICENSE, ALIGNMENT.
