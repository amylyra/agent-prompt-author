# Route E — revising an existing prompt

## Never rewrite monolithically

LLM regeneration of accumulated context causes **context collapse** — detail erodes into shorter, less informative summaries, with sharp measured performance drops. The paper naming it is explicit that this is a fundamental risk of end-to-end context rewriting, not an artifact of one method.

Edit as **itemized deltas**: discrete changes to named items, merged deterministically. The framework that beat compressing baselines by 10.6% on agent tasks works precisely because its merge step is non-LLM logic operating on structured entries, not a model rewriting prose.

Practical form: if the prompt is one block of prose, your first delta is to itemize it. You cannot safely revise what you cannot address by line.

## Distinguish the two deletion targets

Getting this backwards is the most damaging error available in this route.

| Target | Treatment | Test |
|---|---|---|
| **Obsolete guardrail** — written for a weaker model's failure mode | Delete | Does this model still have the failure? |
| **Accumulated domain knowledge** — hard-won edge cases | Keep, restructure | Would this rule have prevented a real, observed mistake? |

Check the second test against **actual session history**, not intuition about whether the rule sounds useful.

**Under a portability constraint this inverts.** A guardrail is safe to cut only if *every* target model has internalized it — the intersection of what's safe, not the union. See `references/portability.md`.

If it fails: **flag, don't delete.** Ablation on a stochastic system is noisy; single-rule ablation misses interactions where rule A only matters when B is absent; and scar tissue often guards a tail case the eval set was never drawn from. Mark it retained-without-evidence with a reason, and move on.

The reverse direction is also available and cheaper than you'd expect: mine recent sessions for corrections the user keeps making, cluster them, adversarially verify each candidate against "would this have prevented a real mistake," and promote survivors.

## Bound the loop

| Condition | Rounds | Why |
|---|---|---|
| No held-out validation set | **1–2** | Past that, generator and in-context judge jointly exploit weaknesses in their own scoring proxy. "Better" collapses into "reads better" |
| With held-out validation | **~5**, up to 10 | Empirical sweet spot across several independent studies |

Rules that hold in both cases:

- **Select by validation score, not recency.** The best version is frequently not the last. One study's selecting agent most often chose iteration 5 out of 10.
- **Keep every version.** You cannot select from candidates you overwrote.
- **Multiple independent starts beat more rounds on one start.** Stochastic runs converge to different local optima.
- **Prefer generate-and-rank over iterative search at small budgets.** Iterative showed train-test gaps up to 5.6 pts; non-iterative showed none.
- **Focus each round on the single weakest dimension**, not on improving everything simultaneously.
- **Stop when two consecutive rounds move the metric less than your noise floor.**

## Diff behavior, not text

Most models have a **zero-regression rate below 0.25** across multi-round maintenance — assume every round broke something. Only the Opus-class models in that benchmark exceeded 0.5.

A text diff tells you what changed. It does not tell you whether the change was good. Re-run the full case set every round and compare per-case, not just the mean — a flat mean can hide two cases fixed and two broken.

## The accuracy–correction paradox

**Models with higher initial accuracy benefit less from self-correction, or are actively harmed by it.**

Say this out loud when a user's well-written prompt keeps degrading. They are experiencing the documented worst case: a good first draft is the worst possible starting point for a refinement loop. People who start from bad prompts see improvement and conclude the loop works.

Related, and worth naming: unconditional self-correction is a systematic form of compute waste. Measure whether iteration pays on a calibration set before making it a default.

## Retrospective capability decay

Self-evolving systems acquire new competence at the expense of previously mastered tasks. Fixing case 14 quietly breaks cases 1–13, and nothing in the loop reports it.

This is why per-case comparison is non-negotiable and why a Pareto-style approach — keeping a candidate that is best on *at least one* case even when beaten on average — outperforms keeping only the running leader. It preserves the specialists that a mean-based selection discards.
