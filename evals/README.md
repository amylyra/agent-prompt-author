# Improving this skill without growing it

The skill documents a ratchet: additions are locally safe, deletions are locally
unverifiable, so artifacts only grow. This directory is what stops that happening
here. Read it before editing anything in the skill.

## The rule

**Every addition requires a deletion of equal or greater size, or a passing case
that the deletion would have broken.**

No exceptions for "this is important." Everything anyone ever added was important
to them at the time. If a line cannot earn its place against a case, it does not
have one.

## Improve by substitution, not accumulation

When a case fails, the fix is a **replacement**, in this order of preference:

| Move | Example | Cost |
|---|---|---|
| Sharpen an existing line | vague step becomes a checkable one | zero |
| Move a line to a lower layer | prose rule becomes a schema, enum, or hook | negative — prose shrinks |
| Move a line to a route file | always-loaded becomes on-demand | negative — SKILL.md shrinks |
| Merge two lines | overlapping guidance collapses into one | negative |
| Add a line | last resort | positive — needs a deletion |

If the answer is always "add a line," the skill has a structural problem, not a
coverage problem.

## Ablation is per-file, not per-rule

Rule-level ablation on a stochastic system is too noisy to trust — the signal is
often smaller than run-to-run variance, and single-rule ablation misses
interactions where rule A only matters when B is absent.

**File-level ablation is cheap enough to run on every change.** Six runs, not a
hundred:

```bash
python run_routing.py --ablate
```

A file whose removal costs nothing is either dead weight or untested by the
current cases. **Decide which before deleting it.** Writing a case that the file
would pass and the ablated version would fail is the honest way to settle it —
and if you cannot write that case, that is the answer.

## Regression protocol

```bash
# once, before any edit
python run_routing.py --snapshot baseline.json

# after every edit
python run_routing.py --compare baseline.json
```

The harness compares **per case**, not just the mean, because a flat average
hides two cases fixed and two broken. Newly-broken cases fail the run even when
the mean improved.

It also runs three times by default and reports the spread. **A gain smaller
than that spread is not a gain.** The decision bar is `max(recorded noise,
current noise, 2.0)`.

## Why routing is the thing measured

A skill's outputs are mostly prose, which is expensive to score and easy to
score wrongly. But two of its outputs are **labels**:

- which route it took
- which finding class it reached

Labels score exactly. Scoring the label instead of the prose is what makes this
harness cheap enough to run on every edit — and route classification is a
structured-output task, which is the one condition where prompt optimization
reliably has headroom.

## The case set

`routing.jsonl` — 24 cases across four kinds. All four kinds matter:

- **Canonical** (a01–e03) — unambiguous cases for each route. Catch gross breakage.
- **Ambiguous** (x01–x03) — cases where two or three routes are defensible. These
  are where the skill actually fails, and where every edit should be checked.
- **Precondition** (p01–p02) — a symptom described with no artifact supplied. The
  skill must ask before diagnosing. This guards against the exact failure the
  skill was written to prevent.
- **Negative** (n01–n03) — the skill should not fire. Without these, you optimize
  toward a skill that fires on everything.

**Replace these with your own.** Cases drawn from real requests beat invented
ones, because invented cases encode the author's theory of what users say rather
than what they actually say. Mine the last fifty sessions for the requests that
should have triggered this skill and the ones that shouldn't have.

## What this does not measure

Honest limits, so nobody mistakes a green run for a working skill:

- **Whether the finding is correct.** Routing to A does not mean the diagnosis
  within A is right.
- **Whether the output contract is followed.** Needs a second harness scoring
  block presence — or better, a `Stop` hook, since a format request is the
  weakest instruction form available.
- **Whether the skill triggers in a real session.** This probe hands the skill
  to the model directly. Real triggering is description matching against a
  crowded skill list; `/doctor` diagnoses that, this does not.
- **Prose quality of the deltas.** Not scored, and probably not worth scoring.

## Next case sets, in priority order

1. **Contract compliance** — does the output carry all five blocks? Cheap to
   score by regex, and it is the most-likely-to-drift behavior.
2. **Finding class within Route A** — given a prompt with a known defect
   (competing count, conflict, wrong layer, obsolete), does it find that one?
   Requires fixture prompts, which is real work, but it is the test that
   measures whether the skill is any good rather than merely well-organized.
3. **Trigger rate** — sample real session openers, measure fire vs. no-fire
   against what should have happened.
