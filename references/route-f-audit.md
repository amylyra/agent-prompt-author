# Route F — is this prompt structurally sound?

For "review this prompt", "is this any good", "how much of this is still needed" —
a standing artifact with no specific failure attached and no eval set in hand.

**This is a reading, not a measurement.** It tells you whether the prompt is built
correctly. It cannot tell you whether it works: that is Route B, and it needs cases.
Say which one you did. An audit that gets reported as a verdict on quality is the
more damaging of the two mistakes available here.

Do not run it as a checklist top to bottom. Read the prompt once, then answer the
three questions in order. **Stop at the first one that fails** — a prompt with the
wrong shape does not benefit from a scaffolding inventory.

## 1. Shape

Is the thing organized so a rule can be found and followed?

- **Scopes, and rule count per scope.** Count live rules where they compete, not per
  file. Over ~8 in one scope is the finding; see Route A step 2 for what to do about
  it. Counting is the only mechanical part of this route, and it is still a judgment
  call — "one rule" is what the model must hold at once, not what the bullet points.
- **Sections are separated and named.** Background, instructions, tool guidance,
  output contract. For Claude, XML tags with consistent descriptive names; Markdown
  headers if the prompt must also run on another family (`portability.md`).
- **Long inputs sit at the top, the ask at the bottom.** Documents above instructions
  above the query. Worth up to ~30% on multi-document inputs, and it is free.
- **Each instruction appears exactly once.** Restating a rule in three places was
  correct for a weaker generation. Now it mostly creates a conflict surface.
- **Effort, verbosity, and thinking depth are API parameters, not prose.** A prompt
  that argues with a dial it also sets is a prompt with a bug in it.

## 2. Scaffolding

**The inversion worth understanding: current models need less behavioural
scaffolding and more scope specification than the prompts written for them assume.**
They got better at doing the work, so "try harder" instructions are now dead weight
or actively harmful. They also got more literal, so "how far, how long, how much" —
which used to be inferred — now has to be stated. Most audited prompts are wrong in
both directions at once.

**Cut on sight.** Each of these is named in current Anthropic model guidance as
counterproductive on this generation, not merely unnecessary:

| Scaffolding | Why it goes |
|---|---|
| "Include a verification step", "use a subagent to verify" | Opus 5 verifies unprompted. These compound into over-verification and cost tokens with no quality gain |
| "Double-check your answer", "re-verify before responding" | Same compounding, on self-correction the model already does |
| "Be thorough", "if in doubt use \[tool]", "default to \[tool]" | Anti-laziness prompting written for models that undertriggered. Now overtriggers. Replace blanket defaults with conditional ones — "use \[tool] when it would improve your understanding" |
| "After every N tool calls, summarise progress" | The model narrates readily now. Remove it, then re-add a *cadence* description only if what you get is wrong |
| Any rule telling the model not to think or not to reason | Measurably increases internal-tag leakage. Strictly harmful |
| Prefilled assistant turns, `budget_tokens`, `temperature` on Sonnet 5 | Not scaffolding any more — these are removed or return 400 |

**Keep, and add if missing.** These target failures the current generation actually
has:

| Scaffolding | Why it stays |
|---|---|
| Scope limits — deliver what was asked, don't widen or transform it | Current models expand scope and over-engineer without it |
| Response and deliverable length | Effort controls thinking, not visible output. Length has to be prompted |
| Delegation caps — when a subagent is worth it, and how many | Delegation is readier now and multiplies cost on small tasks |
| Explicit breadth on any rule meant to generalise | Literal following means "apply to every section, not just the first" is now load-bearing |
| A concrete bar wherever the prompt says "important" or "high-severity" | A qualitative bar gets followed faithfully and silently drops work. Name the threshold |
| Domain knowledge and hard-won edge cases | Never scaffolding. This is the content |

For anything not on either list, the test is Route E's: **would this rule have
prevented a real, observed mistake?** Check session history, not intuition. If no,
flag it — do not auto-delete. Under a portability constraint the test inverts to the
intersection across models; see `portability.md`.

## 3. Coherence

Only now, and only within a scope — pairwise across a whole file produces a
confident, wrong answer.

- **Two rules constraining one dimension in opposite directions.** "Be concise" and
  "explain your reasoning fully" is the canonical pair. Conflicts rarely surface as
  errors; they surface as a rule that holds sometimes. Intermittent compliance is the
  signature.
- **A general rule and an exception that never names it.**
- **Rules that are requests for a quality rather than a checkable property.**
  "Sound natural", "use good judgment", "high quality". Name a token or a threshold,
  or move it to a rubric with a verifier.
- **Bans with no replacement.** The gap is where invented behaviour comes from. Prefer
  showing the wanted behaviour over stating the unwanted one — positive examples beat
  negative instructions on current models.
- **Rules that should not be prose at all.** Walk Route A's layer ladder. A format
  rule belongs in a schema, a fixed vocabulary in an enum, a tool-choice rule in the
  tool description, a hard gate in a hook.
- **Examples.** 3–5, relevant and diverse, wrapped so they are distinguishable from
  instructions. A laundry list of edge cases constrains the model to the space it
  demonstrates.

## Report

Use the standard output contract. Two additions specific to this route:

- **Lead with the count.** Rules per scope against the budget, before any prose. It is
  the finding that most often makes the rest moot.
- **Separate "obsolete" from "unverified".** A guardrail you can show is obsolete is a
  DELETA; one that merely looks obsolete is UNVERIFIED with the reason. On a prompt
  nobody has evals for, most of the interesting findings are the second kind, and
  reporting them as the first is how an audit does damage.

Close by naming what this did not cover: whether the prompt works. If they want that,
they are going to Route B and they are going to need 20 cases.

---

*Scaffolding lists are dated: August 2026, against Claude Opus 5 / Sonnet 5 guidance.
They are the fastest-decaying content in this skill — every one of these entries exists
because a previous generation needed the opposite. Re-read the current model guidance
before trusting the table.*
