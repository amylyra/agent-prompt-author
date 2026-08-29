# Cross-model portability

Read when the artifact must run on more than one model family. Applies to the
prompt being authored — not to the harness, which stays whatever you run.

## The convergent core is the portable artifact

As of mid-2026 OpenAI and Anthropic guidance agrees on the fundamentals. Write
to the overlap and most of the portability problem disappears:

| Principle | Both labs |
|---|---|
| Lean beats elaborate | OpenAI: leaner system prompts +10–15% eval score, −41–66% tokens, −33–67% cost. Anthropic: >80% of Claude Code's system prompt removed, no measured loss |
| State each instruction exactly once | OpenAI's strongest single recommendation; older models needed a rule in three places, current ones don't. Anthropic moved instructions out of the system prompt into tool descriptions for the same reason |
| Conflicts cost more than gaps | GPT-5.6 burns reasoning tokens reconciling conflicting rules rather than picking one. Claude must deliberate over overlapping messages before acting |
| Outcome over route | State the result, the boundaries, the evidence required, and the stopping condition. Don't prescribe intermediate steps |
| Start fresh, don't port | Both explicitly warn against carrying an old prompt stack to a new model family |
| Delete by ablation, not intuition | OpenAI: delete group by group on a representative test set, keep the cut only if metrics hold. Anthropic: would this rule have prevented a real, observed mistake? |

If a line in your prompt isn't justified by one of those six, it's the first
candidate to cut — on either model.

## What does not port

| Element | Portable form | Why |
|---|---|---|
| **Structure** | Markdown headers | XML tagging is Claude-idiomatic; GPT-5.6 guidance moves away from it. Both parse Markdown headers well. Models perform better with formats matching their training distribution, so pick the neutral one |
| **Effort / thinking** | API parameter, not prompt text | GPT-5.6 exposes reasoning-effort levels and `text.verbosity`; Claude exposes a thinking budget. Instructing effort in prose duplicates a dial you already have, per-model |
| **Brevity rules** | Delete them, then re-add only if a case fails | GPT-5.6 is more concise by default than 5.5, so inherited "be brief" instructions now over-cut. Same rule can under-cut elsewhere |
| **Tool-call conventions** | Test both | Prefix vs. suffix namespacing has non-trivial measured effects that vary by model |
| **Response format** | Choose by evaluation | XML / JSON / Markdown performance differs by model with no one-size-fits-all |

## Deletion under a portability constraint — the inversion

Route E says delete guardrails the model has internalized. **Under portability
that rule inverts.**

A guardrail is safe to cut only if **every** target model has internalized it —
the *intersection* of what's safe, not the union. A rule that's dead weight on
Claude 5 may be load-bearing on GPT-5.6, and vice versa. Ablate on both, and keep
anything that either one needs.

This is the single most likely way to break a portable prompt while following
otherwise-correct advice.

## Optimization under a portability constraint

**Don't.** Optimization gains are the least transferable thing measured.

The same task went from six of six methods beating zero-shot on one model to one
of six on another, with complete reversals in both directions. An optimized
prompt's superiority on one benchmark often fails to transfer, and this persists
across backbones.

If you optimize on Claude and ship to both, you may have made GPT-5.6 worse and
have no signal that you did.

**If you optimize anyway:** run Route B's headroom test **per model**, keep
per-model scores rather than an average, and select on the worst case across
models rather than the mean. A candidate that wins on one and loses on the other
is a regression wearing a gain.

## Authoring checklist

1. Write to the six convergent principles above. Nothing else, first pass.
2. Markdown headers. No XML tags.
3. Effort, verbosity, and thinking budget stay in API parameters.
4. Structure the contract explicitly: role, goal, success criteria, constraints,
   tools, output shape, stopping condition. That skeleton is close to what both
   labs now recommend and it is model-neutral.
5. Evaluate on **both** models before shipping. A prompt validated on one is an
   untested prompt on the other.
6. When a case fails on one model only, prefer fixing it in the schema, the tool
   description, or the stopping condition — structure ports better than phrasing.
7. Re-run everything on every model update, on either side. Both labs say
   explicitly that prompts tuned to a prior family should not be assumed forward-
   compatible.

## Sources

- OpenAI, "Prompting guidance for GPT-5.6 Sol" and Model guidance, July 2026 —
  lean-prompt numbers, state-once, conflict instability, group-ablation protocol,
  eight-element prompt skeleton. *Secondhand via coverage; verify against the
  primary guide before treating numbers as thresholds.*
- OpenAI GPT-5.5 prompting guide, April 2026 — fresh-baseline migration advice.
- Anthropic sources as listed in `evidence.md`.
- Cross-model non-transfer of optimization gains: arXiv 2604.14585 and 2605.26655.
