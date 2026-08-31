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
- whether it asked for the artifact before diagnosing

Labels score exactly. Scoring the label instead of the prose is what makes this
harness cheap enough to run on every edit — and route classification is a
structured-output task, which is the one condition where prompt optimization
reliably has headroom.

## The case set

`routing.jsonl` — 42 cases, plus 6 more in `holdout.jsonl`. Every case carries **two** labels, `route` and
`ask`, scored independently:

- `route` — one of A, B, C, D, E, F, NONE.
- `ask` — must the skill request the artifact before it can give a finding?

**These are independent, and conflating them is the trap.** An earlier version of
this harness scored `PRECONDITION` as a seventh route, which made "routes to A"
and "needs the artifact first" mutually exclusive answers to one question. They
never were. Measured on the same skill and the same cases, the one-dimensional
probe scored 34.5% and the two-dimensional one 75.9% before any skill edit — a
41-point gap that was purely an artifact of the label set, with 20 of 29 cases
answering PRECONDITION instead of routing. If you extend this harness, keep asking
whether a new label is a value of an existing dimension or a dimension of its own.

*Those numbers came from a `claude -p` proxy on Claude Sonnet 5, not the API path
this script uses, so a local `CLAUDE.md` was in context throughout. The confound is
constant across the compared conditions, so the deltas hold; treat the absolute
percentages as approximate until re-run through `run_routing.py` with an API key.*

Five kinds of case, all of which matter:

- **Canonical** (a01–e03) — unambiguous cases for each route. Catch gross breakage.
- **Ambiguous** (x01–x03) — cases where two or three routes are defensible. These
  are where the skill actually fails, and where every edit should be checked.
- **Precondition** (p01–p02) — a symptom described with no artifact supplied. These
  route like any other case; what makes them precondition cases is `ask: true`.
  They guard against the exact failure the skill was written to prevent.
- **Negative** (n01–n03) — the skill should not fire. Without these, you optimize
  toward a skill that fires on everything.
- **Portability** (m01–m03) — the artifact targets more than one model family, so
  the route is right only if `portability.md` loads with it. m02 is the one that
  matters: deletion inverts to the intersection of what is safe across models, and
  a skill that misses it gives confidently wrong advice.
- **Gap** (a05, b05) — triggers the description promises that the routing table
  did not cover. Both misrouted until the table rows were widened to match.
- **Held out** (h01–h10) — written *after* the routing changes were finished and
  never tuned against, to size the train–test gap. On them the change measured
  80% → 90% while the tuned set measured 98%. That ~8-point gap is the honest cost
  of five rounds against one case set, and it is why they are labelled.

- **Audit** (b05, f01–f03) — "review this", "is this any good", "how much of this is
  still needed". They route to F, not B: F reads the artifact, B measures it, and
  someone asking for a review generally has no eval set for B to use. b05 was
  labelled B until Route F existed, which is why it is in this group rather than
  with the gaps.

**h01–h10 are burned.** They are in `routing.jsonl` now, so the next person editing
this skill is training on them. `holdout.jsonl` (g01–g06) is the current unburned
set — six cases written after Route F was finished, including two controls that
check whether adding a route pulled the others toward it. Point the harness at it:

```bash
python run_routing.py --cases holdout.jsonl
```

A held-out set is a consumable, not a fixture. Burn `holdout.jsonl` on the next
change and mine fresh cases from real sessions; invented ones encode the author's
theory of what users say.

Known miss: **h03** ("we're on GPT-5.6 and Claude Sonnet 5, should we keep the
'be concise' instruction?") routes to B, should be E. It is a deletion decision
wearing cross-model clothing. Left unfixed on purpose — it was the only holdout
failure, and tuning it away would have meant tuning on the holdout.

**Replace these with your own.** Cases drawn from real requests beat invented
ones, because invented cases encode the author's theory of what users say rather
than what they actually say. Mine the last fifty sessions for the requests that
should have triggered this skill and the ones that shouldn't have.

## What this does not measure

Honest limits, so nobody mistakes a green run for a working skill:

- ~~**Whether the finding is correct.**~~ This is what `run_findings.py` now does,
  for Route F. Routing to A still does not mean the diagnosis within A is right —
  A, B, D and E have no finding-level harness yet.
- **Whether the output contract is followed.** Needs a second harness scoring
  block presence — or better, a `Stop` hook, since a format request is the
  weakest instruction form available.
- **Whether a reference file is any good.** The probe feeds the model `SKILL.md`
  alone, so a green run on `f01` proves the routing table sends audits to Route F —
  not that `route-f-audit.md` gives good advice once it loads. Every reference file
  in this repo is unmeasured in that sense. Scoring the content needs fixture prompts
  with known defects and a check that the right defect comes back, which is the
  "finding class" harness listed below.
- **Whether the skill triggers in a real session.** This probe hands the skill
  to the model directly. Real triggering is description matching against a
  crowded skill list; `/doctor` diagnoses that, this does not.
- **Prose quality of the deltas.** Not scored, and probably not worth scoring.

## The second harness: run_findings.py

`run_routing.py` scores which route the skill picks. That is the cheap half —
routing correctly to F says nothing about whether the audit that follows is any
good. `run_findings.py` scores the finding.

```bash
python run_findings.py                       # both fixtures, 3 runs each
python run_findings.py --fixture clean-triage.md
python run_findings.py --snapshot base.json  # then --compare base.json
```

Fixtures in `fixtures/` carry defects planted on purpose. `findings.jsonl` lists
them. Two numbers come out, and you need both:

- **recall** — of the planted defects, how many did the audit report?
- **invented** — of the findings it reported, how many are not true of the text?

Recall alone gets you an audit that reports nine things about everything.

### Read the spread before you believe the number

Each fixture runs three times and the spread is reported, because **recall on an
unchanged skill and an unchanged fixture moved 42–75% across runs** — a 25 to 50
point spread depending on the fixture. That was discovered the hard way, after
three rounds of "improving" Route F against single-run scores. Two of those
rounds were measuring nothing.

A defect is `missed` only when **every** run missed it, and `flaky` when some
runs found it. The distinction is the useful output: on the last calibration,
1 of 12 defects was truly missed and 6 were flaky. Those need opposite fixes — a
missed class is absent from the route, a flaky one is present but not salient
enough to land reliably.

### What this gates on, and what it only reports

| Signal | Stable? | Gated |
|---|---|---|
| Defects missed by every run | yes | **yes** — a class the route does not cover |
| `absent` classes falsely claimed | yes, 4/4 every run | **yes** |
| Mean recall | no, 25–50 pt spread | reported as a band |
| `invented` count | no, see below | reported only |

Thresholding a number with a 25-point spread is a coin flip dressed as a test,
which is the failure this whole repository is about. So the gates are on the two
signals that held across every run measured, and recall is a diagnostic band.

### The graders disagree with each other

`invented` is not gated because it is not yet trustworthy. On the last run the
recall judge credited the audit with finding the planted `enum-mismatch` defect,
and the grounded judge called *the same finding string* untrue of the prompt.
Both cannot be right.

The grounded judge is also asking the wrong question — *is this claim true* — so
a grounded nitpick passes and materiality goes unmeasured. Fixing this needs a
better-specified judge prompt and a calibration set of its own, which is a
harness for the harness. Until then, read `invented` by hand.

This is a model judging a model, and it is the weakest part of the setup. It is
still better than the alternative here, which was judging by feel.

### The negative control is `absent`, not silence

`clean-triage.md` was written to be defect-free and is not. Three attempts, and
each repair introduced a new real defect — one of them caused directly by fixing
the previous round's finding, which is retrospective capability decay happening
in a prompt rather than a model. Writing a clean prompt is harder than auditing
one.

So it is scored both ways: positive for the four subtle defects it actually has,
and negative through an `absent` list — loud classes it demonstrably does not
have (over-budget, meta-instructions, speculative guards, unhandled
hypotheticals) that the audit must not claim. "Expect silence" was the wrong
instrument. Absence of named classes is falsifiable and cannot be gamed by
writing a better fixture.

## Next case sets, in priority order

1. **Finding harnesses for A, B, D and E.** Route F has one now; the others do
   not, and the same fixture-with-planted-defects pattern extends to them.
2. **Finding class within Route A** — given a prompt with a known defect
   (competing count, conflict, wrong layer, obsolete), does it find that one?
   Requires fixture prompts, which is real work, but it is the test that
   measures whether the skill is any good rather than merely well-organized.
3. **Trigger rate** — sample real session openers, measure fire vs. no-fire
   against what should have happened.
