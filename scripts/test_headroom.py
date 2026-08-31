#!/usr/bin/env python3
"""
Does the headroom test survive a world with no headroom in it?

A go/no-go tool whose own decision rule is untested is the failure this skill
warns about: a loop with no external verifier, optimizing for looking right.
So this simulates two worlds against a stub model and checks the verdicts.

    NULL   — every candidate is identical in truth. Any apparent gain is luck.
             The script must report FLAT. False positives here are the whole
             risk: the tool exists to stop wasted optimization work, and a
             tool that green-lights noise causes the thing it prevents.
    EFFECT — one candidate is genuinely better. The script should find it,
             including when the screen ranks a luckier candidate first.

Deliberately brutal conditions: 20 binary-scored cases at a 50% baseline, so
a single run's standard error is ~11 points. Real case sets are usually
quieter. The point is that the verdict holds when they are not.

    python scripts/test_headroom.py

No API key needed and no network calls — `run_case` is stubbed.
"""

import contextlib, importlib.util, io, json, os, pathlib, random, sys, tempfile, types

SEEDS = 12
NULL_MAX_FALSE_POSITIVES = 2   # nominal alpha is 0.05; 2/12 allows for noise
EFFECT_MIN_TRUE_POSITIVES = 6


def load(path):
    os.environ.setdefault("ANTHROPIC_API_KEY", "stub")
    sys.modules["anthropic"] = types.SimpleNamespace(
        Anthropic=lambda **kw: None, NOT_GIVEN=object())
    spec = importlib.util.spec_from_file_location("headroom", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def fixtures(tmp, n_cases=20, n_candidates=12):
    cases = pathlib.Path(tmp, "cases.jsonl")
    cases.write_text("".join(
        json.dumps({"input": f"q{i}", "expected": "a"}) + "\n" for i in range(n_cases)))
    cands = pathlib.Path(tmp, "candidates.txt")
    cands.write_text("\n---\n".join(f"candidate {i}" for i in range(n_candidates)))
    return str(cases), str(cands), n_candidates


def run(mod, cases, cands, effect, winner, seed):
    """Stub the model: `winner` scores `effect` higher, everything else is a coin flip."""
    sys.argv = ["headroom_test.py", "--cases", cases, "--candidates", cands, "--runs", "3"]
    random.seed(seed)
    mod.run_case = lambda client, model, system, case, effort=None: (
        1.0 if random.random() < 0.5 + (effect if system and system == winner else 0.0) else 0.0)
    with contextlib.redirect_stdout(io.StringIO()):
        return mod.main()   # 0 = headroom found, 1 = flat


def main():
    here = pathlib.Path(__file__).parent
    mod = load(here / "headroom_test.py")
    with tempfile.TemporaryDirectory() as tmp:
        cases, cands, n = fixtures(tmp)
        winner = f"candidate {n - 1}"
        null = sum(run(mod, cases, cands, 0.00, winner, s) == 0 for s in range(SEEDS))
        real = sum(run(mod, cases, cands, 0.30, winner, s) == 0 for s in range(SEEDS))

    ok_null = null <= NULL_MAX_FALSE_POSITIVES
    ok_real = real >= EFFECT_MIN_TRUE_POSITIVES
    print(f"null world   {null:>2}/{SEEDS} called HEADROOM  "
          f"(want <= {NULL_MAX_FALSE_POSITIVES})  {'ok' if ok_null else 'FAIL'}")
    print(f"real effect  {real:>2}/{SEEDS} called HEADROOM  "
          f"(want >= {EFFECT_MIN_TRUE_POSITIVES})  {'ok' if ok_real else 'FAIL'}")
    return 0 if (ok_null and ok_real) else 1


if __name__ == "__main__":
    sys.exit(main())
