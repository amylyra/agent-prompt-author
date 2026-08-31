# Route B — does optimization help at all?

**Run this before any optimization work, always.** Across 72 runs of six optimizers (APE, OPRO, EvoPrompt, PromptBreeder, DSPy-style bootstrap, and a risk-aware method) on Claude Haiku 4.5, 49% scored *below* zero-shot — binomial p = 0.91, indistinguishable from random.

## Step 0 — classify the task. Free, and it decides most cases

Optimization helps when the task needs an output format the model **can** produce but does not default to. That is a property of the task, readable before you have a single eval case.

| Has headroom | Flat |
|---|---|
| Structured schemas, JSON, XML output | Free-form natural language |
| Rubric-scored evaluation with fixed dimensions | Open-ended summarization |
| Domain formatting conventions (citations, legal, clinical) | General question answering |
| Classification into a non-obvious taxonomy | Conversational response |

**If the task sits entirely in the right column, that is the finding.** Report a flat landscape and stop. You do not need cases to say so, and asking for 20 before answering a question you can already answer is how this route becomes a dead end nobody walks back from.

In the source study, the one task where all six methods beat zero-shot required structured rubrics and JSON output — the model's default was unstructured prose, and closing that gap was worth 6.8 points. The three free-form tasks gained 1.1, 0.7, and 0.6 — all inside noise.

Mechanism: instruction-tuning trains consistent outputs across diverse input phrasings, which compresses input style into a narrow output distribution and eliminates the phrasing-sensitivity optimization exploits.

**If it sits in the left column, or straddles**, the structural read is suggestive and not a verdict. Measure.

## The headroom test

**Cost:** ~$5, ~10 minutes. **Output:** a go/no-go on all downstream prompt work.

### Step 1 — assemble cases

20 held-out cases the prompt has never been tuned against. Real inputs, real expected outputs. If the user has none, offer to build 20 as the highest-value available work — for a left-column task it is the only thing that turns a guess into a measurement.

**If they decline:** proceed in degraded mode. Say explicitly that you are working without ground truth, restrict yourself to Route A (layer and count problems are visible without evals) and to the Step 0 read, and refuse Step 4's verdict. Do not substitute your own judgment for a measurement and present it as one.

### Step 2 — generate candidates

10–20 diverse variants. Diversity is the point; near-duplicates waste the budget. Vary along axes that plausibly matter:

- Output format specification (none → described → schema → schema plus example)
- Role framing (none → task-framed → expertise-framed)
- Reasoning instruction (none → "think step by step" → structured decomposition)
- Constraint density (bare task → 3 constraints → 8 constraints)
- Ordering (task first vs. context first)

Generate these mechanically, not by taste. The point is to sample the space, not to write good prompts.

### Step 3 — score

Run each candidate plus a zero-shot baseline across all 20 cases. Same model, same temperature, same scoring function. Record per-case results, not just the mean — you need the variance.

`scripts/headroom_test.py` runs this loop if the user has no harness.

### Step 4 — decide

| Result | Meaning | Action |
|---|---|---|
| Best candidate gains **< ~2 pts** over zero-shot | Flat landscape | **Stop.** No method in the literature reliably helps. Report this as the finding |
| Best gains **> ~2 pts** | Real headroom | Identify what the winner does differently, then Route D |
| High variance, unstable ranking across repeats | Noise floor exceeds signal | Fix the eval set before optimizing anything |

**Recalibrate the 2-point threshold against your own noise floor.** Run the zero-shot baseline three times; the spread between runs is your floor. A "gain" smaller than that spread is not a gain.

## Before blaming the prompt

Question difficulty explained **19–91% of total variance** in the source study — far more than any prompt effect. If your eval scores swing on which cases you sampled, prompt work cannot move the number. Stratify by difficulty before concluding anything.

## Multi-agent corollary

Optimize each agent independently by default. Agent interaction was **never statistically significant** across 18,000 evaluations — all F below 1.0, 0.18–2.15% of variance. Expert predictions about which pipelines would be coupled were wrong.

**The coupling test** (~$80, 1 day): 10×10 prompt grid across two agents, n=30, two-way ANOVA. Interaction F below 1 → optimize independently, skip joint optimization tooling entirely.

Coupling *may* emerge with shared mutable state, output-schema dependencies between agents, feedback loops, 3+ agent chains, or structured-data rather than natural-language communication. Measure rather than assume in either direction.

## Multiple target models

Run the headroom test **per model** and keep per-model scores, never an average. The same task went from 6/6 methods beating zero-shot on one model to 1/6 on another, with reversals in both directions. Select on the worst case across models: a candidate that wins on one and loses on the other is a regression wearing a gain. See `references/portability.md`.

## If you proceed to an optimizer

- **Prefer generate-and-rank over iterative search at small budgets.** Iterative methods showed train-test gaps up to 5.6 pts; non-iterative APE showed none.
- **Known GEPA failure mode:** over-indexing on surface patterns in the training minibatch — specific usernames, document titles, domain terms. Add an anti-overfit instruction and hold out a test set.
- **GEPA's early rounds insert verbatim training content** before later rounds abstract it. Stopping early catches it mid-bloat.
- **GEPA's own production guidance** is to incrementally optimize a set of human-written instruction bullets rather than regenerate wholesale — which is the same structure Route E prescribes.
