---
name: agent-prompt-author
description: Write, revise, and diagnose system prompts, orchestrator instructions, subagent delegation contracts, tool descriptions, and harness text for LLM agents you build and ship. Use whenever someone wants an agent to behave differently by changing its text — "write a system prompt for X", "improve this orchestrator prompt", "my agent keeps ignoring this rule", "the prompt got worse after I edited it", "add a constraint so it stops doing Y", "write a tool description", "should I run GEPA or DSPy on this", "review this agent prompt". Also use when a prompt has grown past ~200 lines, when a refinement loop has stopped helping, or before investing in automated prompt optimization. Do NOT use for one-off chat prompts, for CLAUDE.md and repo context files (opposite policy — see Route C), or for brand voice and creative style guides.
---

# Agent Prompt Author

Prompt work fails for four reasons, in descending order of frequency:

1. **The prompt was never the bottleneck.** Most requests to improve a prompt should end here.
2. **The rule lives in a layer that cannot enforce it.** Prose is a request; hooks are a gate.
3. **Rules written for an older model are still firing.**
4. **The revision loop has no external verifier**, so it optimizes readability instead of behavior.

Skipping to "write a better rule" is the default failure mode of this task.

## Precondition

**Always name the route.** Routing is done from what the user said and never
needs the artifact. Route D needs nothing further at all — a prompt that does
not exist yet has no text to ask for.

**Do not diagnose from description alone.** What needs the artifact is the
FINDING, not the route. On A, B, C, and E, before you produce one, get:

- The actual artifact text, or the assembled context if the artifact is templated.
- One concrete failure — the input, what happened, what should have happened.
- For Route E, the previous version too. Regression is invisible without a diff.
- **Which model families the artifact must run on.** If more than one, read
  `references/portability.md` alongside your route — several rules invert.

If the user describes a symptom without producing the artifact, name the route, then ask for it once, plainly. A diagnosis built on a description of a prompt is a guess about a class of prompts, not a finding about theirs.

## Route

Match the request, then read **only** that route's file.

| What they said | Route | Read |
|---|---|---|
| "It ignores this rule" / "it won't stop doing X" / it has grown past ~200 lines | **A — Enforcement** | `references/route-a-enforcement.md` |
| "Improve / optimize / review this prompt" (no specific failure) | **B — Headroom** | `references/route-b-headroom.md` |
| "Should I run GEPA / DSPy / an optimizer" | **B**, then D | `references/route-b-headroom.md` |
| "Write a prompt for [new agent / subagent / tool]" | **D — Authoring** | `references/route-d-authoring.md` |
| "It regressed after editing" / "each round makes it worse" | **E — Revision** | `references/route-e-revision.md` |
| It's a CLAUDE.md, repo rules file, or ambient skill | **C — Wrong artifact** | Below. Do not read further |

Length routes to A, not B. Line count is a rule-count problem, and Route A step 2 measures it — no eval set required.

Read `references/portability.md` when the artifact targets more than one model family.
Read `references/evidence.md` only when a user challenges a claim or asks for sources.

## Route C — wrong artifact class

Context files and product prompts take **opposite** policies. Name which one this is, then redirect.

| | Context (CLAUDE.md, repo rules, memory) | Product prompt (orchestrator, harness, shipped agent) |
|---|---|---|
| Failure mode | Adherence decay, conflict tax | Customer-visible inconsistency |
| Ground truth | The repo, tests, the running app | Your eval set, or nothing |
| Policy | Delete aggressively, trust judgment | Specify deliberately, gate on evals |

For context files, point to `/doctor`, path-scoped rules, and gotchas-over-conventions. This skill does not cover them.

## Verification — applies to every route

**A single context window cannot audit its own prompt.** Self-preferential bias is strongest precisely when a model judges output against a rubric. If verification matters, it runs in a separate context with an agent whose job is to refute, not confirm.

Three failure modes to design against:

- **Agentic laziness** — declares done after partial progress. A single pass over 200 rules covers maybe 140.
- **Self-preferential bias** — prefers its own results, worst under rubric judging.
- **Goal drift** — original constraints lost across turns, especially after compaction.

**Grading ≠ ranking.** One output against a fixed rubric: a single judge emitting 0.0–1.0 plus pass/fail. Many candidates against each other: pairwise tournament beats absolute scoring.

**Narrow gates backfire.** Adding a static-analysis check to an iterative loop *raised* latent degradation from 12.5% to 20.8% — the model optimizes to the gate and you stop looking. A check must cover the property you actually care about.

## Output contract

Return, in this order. Never a silent full rewrite.

```
ROUTE      A — enforcement. Rule is present but competing.

FINDING    orchestrator.md carries 23 live rules in one scope. The
           "always cite sources" rule sits at #19. Compliance at this
           count is ~30% before any conflict is considered.

DELTAS     1. Move rules 14–23 to references/citation-policy.md,
              loaded on the cite path only.  [count 23 → 13]
           2. Merge rules 4 and 11 — both constrain output length,
              4 says "concise", 11 says "at least three paragraphs".
              Kept 11; 4 was unmeasurable.

REMOVED    Rule 7 ("do not hallucinate"). Failed the counterfactual:
           no session in the log shows it preventing anything, and
           the model has no observed failure it guards.

UNVERIFIED Rule 16 kept on judgment. Looks obsolete for this model
           generation, but it guards a tail case the eval set does
           not sample. Flagged, not cut.
```

If Route B returned a flat landscape, the FINDING is the whole answer. Say the prompt is not the bottleneck and stop. **Recommending prompt work the evidence says won't help is worse than declining.**

## Shelf life

Optimization effects are strongly model-specific: the same task went from 6/6 optimizers beating zero-shot on one model to 1/6 on another. Base models keep absorbing the scaffolding these techniques were built to discover. Re-run Route B after every model update.

The standing question for any existing prompt is not *what rule is missing* but **what can I stop doing.**

---

*Written August 2026 against Claude Opus 5 / Fable 5-generation behavior. Every number in this skill is sourced in `references/evidence.md`. Re-check the numbers against a current model before treating them as thresholds.*
