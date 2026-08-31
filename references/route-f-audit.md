# Route F — is this prompt structurally sound?

For "review this", "is this any good", "how much of this is still needed" — a
standing artifact with no specific failure attached and no eval set in hand.

**This is a reading, not a measurement.** It tells you whether the prompt is built
correctly. It cannot tell you whether it works: that is Route B, and it needs cases.
Say which one you did. An audit reported as a verdict on quality is the more damaging
of the two mistakes available here.

**Audit the system, not the file.** Behaviour comes from the model, runtime settings,
the prompt, tool definitions, retrieved context, history and memory together. The
tool that fires too often is usually an over-eager tool *description*; the objective
lost at turn 30 is usually compaction. If the cause is outside the text, that is the
finding — say so and stop, rather than auditing prose that was never the problem.

## 0. Classify first, in one line

Target model and reasoning mode; one-shot or long-horizon; tools none, read-only or
side-effecting; cost of failure. A good prompt for a classifier is a bad prompt for an
autonomous agent, and everything below is weighted by these answers.

## 1. Shape

- **Rule count per scope**, counted where rules compete rather than per file. Over ~8
  is the finding; Route A step 2 has the fix. Counting is a judgment call — a rule is
  what the model must hold at once, not what the bullet points.
- **Named sections**: role and outcome, success criteria, constraints, evidence and
  authority boundaries, domain context, output contract. XML tags for Claude, Markdown
  headers if it must also run elsewhere (`portability.md`).
- **Long inputs at the top, the ask at the bottom.** Worth up to ~30% on
  multi-document inputs, and free.
- **Each behaviour specified in exactly one control plane.** Not just once in the
  prompt — once across the prompt, the tool description, the wrapper and the parser.
  Duplicate control planes drift apart and then conflict.
- **Effort, verbosity and thinking depth are API parameters.** A prompt arguing with a
  dial it also sets has a bug in it.

## 2. Invariants versus defaults

The highest-yield question in this route, and the one most prompts have never asked:

> **If the user explicitly asks for the opposite, should the model still obey this?**

Yes → invariant. No → default. Most prompts have quietly promoted every preference to
a hard rule, then bolted on exceptions to walk it back:

```
Never use bullet points.  /  Use tables for comparison.
Answer in prose.  /  If the user asks for a checklist, give a checklist.
```

That is an exception graph pretending to be a policy. One default replaces it: *default
to prose; use tables, bullets or checklists where the task benefits or the user asks.*
Collapsing an exception graph into a stated default is the single most common
structural repair on this route.

## 3. Scaffolding

**The inversion worth understanding: current models need less behavioural scaffolding
and more scope specification than the prompts written for them assume.** They got
better at the work, so "try harder" instructions are dead weight or worse. They got
more literal, so "how far, how long, how much" now has to be stated. Most audited
prompts are wrong in both directions at once.

Sort every rule into four classes:

| Class | Treatment |
|---|---|
| **Product invariant** — required regardless of which model runs it | Keep |
| **Model compensation** — added because a model failed without it | Keep *only while measured*. Re-test on every upgrade |
| **Redundant reinforcement** — restates behaviour already encoded | Merge or delete |
| **Speculative guard** — protects against a failure never observed | Usually delete, but flag rather than cut if no eval samples it |

Model compensation is where the debt sits, and current Anthropic guidance names the
families that have gone stale on this generation — counterproductive now, not merely
unnecessary:

- "Include a verification step", "use a subagent to verify", "double-check your
  answer" — Opus 5 verifies and self-corrects unprompted. These compound
- "Be thorough", "if in doubt use \[tool]", "default to \[tool]" — written for models
  that undertriggered. Make blanket defaults conditional
- "After every N tool calls, summarise progress" — the model narrates readily now
- Any rule telling the model not to think — measurably increases tag leakage
- "Make sure to", "be sure to", "remember to", "it is important that" — the
  meta-instruction family, the strongest measured-*negative* edit family there is.
  Either the model already does it, or the phrasing is a symptom of an upstream
  problem. Rewrite as the plain instruction or cut it
- Prefilled turns, `budget_tokens`, `temperature` on Sonnet 5 — removed or 400 now

And what this generation needs that older ones inferred: scope limits, explicit output
and deliverable length, delegation caps, explicit breadth on any rule meant to
generalise ("every section, not just the first"), and a concrete threshold anywhere the
prompt says "important" or "high-severity" — a qualitative bar now gets followed
faithfully and silently drops work.

**A rule survives if any one of these holds.** Otherwise the default is suspicion:

1. It is a genuine product invariant.
2. Removing it measurably worsens a representative eval.
3. It defines a non-obvious authority, safety, evidence or side-effect boundary.
4. It supplies domain context the model cannot infer.
5. A downstream consumer requires that output shape.
6. It resolves a real ambiguity between otherwise-valid behaviours.

Asymmetric on purpose. Adding a rule costs attention, interacts with every other rule,
becomes maintenance surface, and may be obsolete at the next upgrade. Under a
portability constraint the deletion test inverts to the intersection across models
(`portability.md`).

## 4. Coherence

Within a scope only — pairwise across a whole file produces a confident, wrong answer.
Conflicts rarely surface as errors; they surface as a rule that holds *sometimes*.
Intermittent compliance is the signature.

- **Direct contradiction.** Both cannot be satisfied on some real input.
- **Priority ambiguity.** "Be concise" and "be comprehensive" are not contradictory —
  they just never say what gets sacrificed first. Name what survives the cut.
- **Resource conflict.** Under 100 words, *and* reasoning, three examples, sources and
  caveats. Two reasonable rules competing for one budget.
- **Autonomy collision.** "Default to action" against "never modify without approval".
  Current agentic models are the most sensitive to this class.
- **Epistemic collision.** "Take a position", "never speculate", "always answer". The
  missing rule is how to behave under genuine uncertainty.
- **Exception inversion.** A narrow exception written strongly enough to override the
  general policy everywhere.
- **Unobservable rules.** *Could two competent evaluators independently decide whether
  this was followed?* If not, rewrite it or demote it to an aspiration. "Be insightful"
  fails; "if the user's premise is materially questionable, test it before solving the
  downstream problem" passes.
- **Wrong layer.** The highest-yield class and the easiest to read past, because a
  misplaced rule is usually written correctly — it is just in prose. Check every rule
  against this table before moving on:

  | The rule says | It belongs in |
  |---|---|
  | Return valid JSON / these fields / this shape | Output schema |
  | Exactly one of a fixed set of values | Enum |
  | Which tool to use, or when to use it | Tool description |
  | Under N words, at most N items | `max_tokens` or a linter |
  | Never take \<side-effecting action> without \<check> | Hook or an authorization boundary outside the model |
  | Match our tone / house style | Rubric plus a verifier in a separate context |

  Prompting around a schema and prompting around a permission are both this class,
  and the permission one is the dangerous half: a request is not a control.
- **Examples added as cargo cult.** They cost context and narrow behaviour to the
  space they demonstrate. Route D rule 5 has the bar they have to clear.

## Filter at the end, never while reading

**Find first, at full coverage.** Passes 1–4 are a sweep: write down everything,
including what you are unsure about. Do not weigh importance while reading — a
conservatism instruction applied during the sweep gets followed faithfully and you
lose real defects without noticing. This is measured behaviour on current models, not
a stylistic preference.

**Then drop these from the list before reporting.** This filter applies only to gaps
you are about to *invent*. It says nothing about defects you *found in the text* — a
speculative guard written in the prompt is a finding, always, and so is an
unmeasurable rule or a stale scaffold. The two are opposite directions.

- **Unhandled hypotheticals.** "No fallback if the lookup fails", "does not cover a
  three-way tie". You would delete these as speculative guards if the prompt had them;
  do not add them as gaps because it doesn't.
- **Missing content with no evidence it is needed.** A prompt is not defective for
  omitting a rule nobody has needed yet.
- **Anything true of almost any prompt.** If the finding does not quote this
  artifact's text, it is filler.

A *gap* is only a finding when the prompt already implies the behaviour and leaves it
unspecified: a rule that cannot be satisfied under the stated boundaries, a decision
it asks for without giving the vocabulary to make, a tie it creates and never breaks.

## Report

Standard output contract, with two additions:

- **Lead with the count** — rules per scope against the budget. It most often makes the
  rest moot.
- **Separate obsolete from unverified.** A guardrail you can *show* is obsolete is a
  REMOVED; one that merely looks obsolete is UNVERIFIED with the reason. On a prompt
  with no evals most findings are the second kind, and reporting them as the first is
  how an audit does damage.

Then say plainly that you did not test it, and that Route B needs 20 cases.

---

*The scaffolding lists are dated — August 2026, against Claude Opus 5 / Sonnet 5
guidance — and are the fastest-decaying content in this skill. Every entry exists
because a previous generation needed the opposite. Re-read current model guidance
before trusting the table.*
