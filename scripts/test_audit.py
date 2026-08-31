#!/usr/bin/env python3
"""
Does the structural audit fire on a bad prompt and stay quiet on a good one?

A linter with false positives is worse than no linter, because people learn to
skip the output. So this checks both directions:

    fixtures/over_budget.md  — a deliberately bad prompt. Every category the
                               audit knows about is planted in it once.
    ../SKILL.md              — the skill itself, which is tuned. A handful of
                               flags is expected; a flood means the rules drifted
                               loose and the report has stopped being readable.

    python scripts/test_audit.py

No API key needed — the conflict pass is not exercised here.
"""

import importlib.util, pathlib, sys

HERE = pathlib.Path(__file__).parent
MAX_FLAGS_ON_SKILL = 4    # tuned prompt: a few is honest, a flood is drift


def load():
    spec = importlib.util.spec_from_file_location("audit", HERE / "audit_prompt.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    a = load()
    ok = True

    bad = a.strip_noise((HERE / "fixtures/over_budget.md").read_text())
    report, total = a.audit(bad)
    kinds = {k for s in report for k, _ in s["findings"]}
    over = [s for s in report if s["over_budget"]]
    want = {"meta-instruction", "unmeasurable", "ban with no replacement",
            "belongs in output schema", "belongs in enum", "belongs in hook",
            "belongs in linter or max_tokens"}
    missing = want - kinds

    print(f"fixture: {total} rules, {len(over)} scope(s) over budget, {len(kinds)} categories")
    for label, cond in [("detects an over-budget scope", bool(over)),
                        ("detects every planted category", not missing)]:
        print(f"  {label:<34} {'ok' if cond else 'FAIL'}")
        ok &= cond
    if missing:
        print(f"      missed: {sorted(missing)}")

    skill = a.strip_noise((HERE.parent / "SKILL.md").read_text())
    report, total = a.audit(skill)
    flags = sum(len(s["findings"]) for s in report)
    over = [s["scope"] for s in report if s["over_budget"]]
    print(f"\nSKILL.md: {total} rules across {len(report)} scopes, {flags} flagged")
    for label, cond in [(f"stays under {MAX_FLAGS_ON_SKILL} flags", flags <= MAX_FLAGS_ON_SKILL),
                        ("no scope over budget", not over)]:
        print(f"  {label:<34} {'ok' if cond else 'FAIL'}")
        ok &= cond
    if over:
        print(f"      over: {over}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
