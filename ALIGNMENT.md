# ALIGNMENT — code-ownership-map

Round R14, rubric v4.0 (E/F graded). Local-only draft: no git remote, no push, no repo creation.
Date: 2026-10-13.

| # | Item | Status | Evidence |
|---|------|--------|----------|
| 1 | Runnable Python, pure stdlib | PASS | code_ownership_map.py imports only argparse/fnmatch/json/re/sys |
| 2 | argparse CLI | PASS | `map` with `--codeowners/--tree/--json/--min-coverage`; usage errors exit 2, coverage gate exit 1 |
| 3 | self_test inherits scaffold-v2 four defenses | PASS | D1 SystemExit+Exception in run_cli (tested); D2 unicode paths/owners (CJK/emoji, tested); D3 fixtures newline="" via tmp_file (tested, CRLF case); D4 last line SUMMARY |
| 4 | E gate >=60 cases, 3 categories | PASS | SUMMARY: PASS 62/62 — TestParseCodeowners/TestPatternMatching/TestResolveAndMap (functional), TestCli (exception), TestExtremeEdge (10k tree/unicode/CRLF/status lines) |
| 5 | SUMMARY last-line contract | PASS | final line `SUMMARY: PASS 62/62` |
| 6 | README English, <=60-word lead | PASS | README.md opening paragraph is 59 words |
| 7 | README Problem section | PASS | README.md '## Problem' |
| 8 | README How-it-works | PASS | README.md '## How it works' (matching semantics documented) |
| 9 | README Quickstart with timing | PASS | README.md '## Quickstart' says "~2 min total (first run: git ls-files)" |
| 10 | why-not-X >=3 alternatives | PASS | README.md '## Why not X' lists 4 incl. real anchors watson/codeowners-audit, dzaba1/CodeownersAudit, erikdoe/code-ownership-map |
| 11 | Performance [Measured] + repro command | PASS | README.md '## Performance': 40.0 ms per 10k-file map [Measured], repro one-liner |
| 12 | Minimal Fallback | PASS | README.md '## Minimal Fallback' (grep/awk recipe with honest gap note) |
| 13 | Design Trade-offs | PASS | README.md '## Design Trade-offs' (4 entries) |
| 14 | Limits & Second-order Effects | PASS | README.md '## Limits & Second-order Effects' (4 entries incl. * @everyone gaming) |
| 15 | FAQ incl When NOT to use | PASS | README.md '## FAQ' first item is 'When NOT to use this?' |
| 16 | Core Assumptions >=3 + confidence + as-of + hygiene | PASS | README.md '[Core Assumptions]' 4 items with confidence; 'As of 2026-10-13'; MIT LICENSE (zhengming contributors); CHANGELOG v0.1.0 -> v0.1.1 with parser fix; no secrets/real names; contact only hcac4735@agent.qq.com |
| + | Ethics/safety | PASS | Reads two local files; no git commands, no network, no API calls |

Round-2 iteration (rule 99): self-review caught a real parser gap (git
status-prefixed lines accepted as paths) plus 4 test-layer errors; suite
grown 54 -> 62; performance measured. See CHANGELOG v0.1.1.
