# agent-prompt-author

**A Claude Skill that tells you why your AI agent is ignoring its system prompt — before you rewrite it again.**

Your agent won't follow a rule. You add the rule again, in caps. It still won't follow it.
You add an example. Now something else broke. Six edits later the system prompt is 300 lines,
nobody remembers which rules are load-bearing, and it behaves worse than it did in week one.

That loop is the problem this solves. Not by writing you a better prompt — by finding out
whether the prompt was ever the thing that was broken.

Works on system prompts, orchestrator instructions, subagent delegation contracts, and tool
descriptions, for agents built on Claude, GPT-5.6, or both. Instruction following, prompt
optimization, context engineering, and prompt audit are all the same question underneath:
which of these lines is earning its place?

## What you get

Say *"review this prompt"* and paste a support agent prompt. It returns this:

```
ROUTE      F — audit. Structural read, no eval set in play.

COUNT      Rules scope   13 live rules   OVER (budget 8)

FINDING    Three of the 13 are not prose rules at all — they are a schema,
           an enum, and a permission gate wearing sentences. Four more are
           unobservable. Two compete for the same budget. What is left is
           about five real rules, inside budget, no scope split needed.

           Live bug: the enum constrains a `status` field that the declared
           output (reply, sentiment, escalate) does not contain. Nothing in
           prose can reconcile that.

DELTAS     1. "Return valid JSON with reply, sentiment, escalate"  -> schema
              "Exactly one of pending|in_progress|resolved"        -> enum
              "Never refund without a fraud check"                 -> hook
              "Under 200 words"                                    -> max_tokens
              [13 -> 9 rules]

           2. "Never use jargon" fails the invariant test — a technical
              customer asking for an error code should get one. Collapse
              four rules into one default.            [9 -> 7]

REMOVED    "Do not hallucinate."  No observed failure it guards.
           "Remember to check the order database."  Meta-instruction, and
           it belongs in the tool description as a when-to-use.

UNVERIFIED "Avoid being repetitive."  Reads speculative, but repetition is
           a real multi-turn failure and nothing here samples multi-turn.
           Flagged, not cut.

NOT TESTED Whether any of this improves behaviour. This was a reading.
```

Thirteen rules to seven, one real bug, and an explicit line about what it did *not* check.

## Why it works

Because it refuses to answer the question you asked until it has checked four things that
are more often the cause. In descending order of how often they turn out to be the real problem:

1. **The prompt was never the bottleneck.** Most requests to improve a prompt should end here.
   Across 72 runs of six prompt optimization methods — APE, OPRO, EvoPrompt, PromptBreeder,
   DSPy-style bootstrap and a risk-aware method — 49% scored *below* zero-shot, indistinguishable
   from a coin flip. The skill has a ten-minute test that tells you which case you are in before
   you spend a day on it.
2. **The rule is in a layer that cannot enforce it.** Prose is a request. A schema, an enum,
   or a hook is a gate. "Always return valid JSON" in a system prompt is a wish; in a response
   schema it is a fact.
3. **Rules written for an older model are still firing.** Anthropic removed over 80% of Claude
   Code's system prompt for the Claude 5 generation with no measured regression. "Be thorough"
   and "double-check your answer" now cause over-verification rather than preventing laziness.
4. **The revision loop has no external verifier**, so it optimizes for reading better rather
   than working better. Models with higher initial accuracy benefit *less* from self-correction —
   a good first draft is the worst possible starting point for a refinement loop.

This is context engineering rather than prompt engineering: the behaviour of an LLM agent comes
from the model, the runtime settings, the system prompt, the tool definitions, the retrieved
context and the conversation history together. The rule that keeps getting ignored is often
being overruled somewhere that is not the prompt.

Every number above is sourced in [`references/evidence.md`](references/evidence.md), marked for
whether the source was read in full or via secondary coverage.

## Install

**Claude Code plugin**

```
/plugin marketplace add amylyra/skills-marketplace
/plugin install agent-prompt-author@amy-skills
```

**Skills CLI** — Claude Code, Cursor, Windsurf, VS Code, JetBrains. Node 18+.

```bash
npx skills add amylyra/agent-prompt-author -g
```

**claude.ai** — Settings → Capabilities → Skills, upload a `.zip` of this folder with the
folder as the zip root. Needs Pro, Max, Team, or Enterprise with code execution enabled.

**Manual** — drop this directory into `.claude/skills/agent-prompt-author/`.

No API key, no configuration, nothing to run. It fires on its own when you describe a prompt
problem.

## What it handles

It asks for the artifact and one concrete failure, then takes one of six routes and loads only
that route's file — a diagnosis costs one file, not the whole skill.

| Say this | It does |
|---|---|
| "my agent keeps ignoring this rule" | **Enforcement.** Is it loaded, is it competing, is it conflicting, is it in a layer that can enforce it, is it obsolete. Wording is checked last, not first |
| "improve this prompt" / "should I run DSPy or GEPA" | **Headroom.** Whether optimization has anything to find here at all, on a test you can price before running |
| "review this prompt" / "is this any good" | **Audit.** Structure, scaffolding debt, coherence. A reading, not a measurement |
| "write a prompt for this agent / subagent / tool" | **Authoring.** Minimal draft, six rules, delegation contracts, tool descriptions |
| "it got worse after I edited it" | **Revision.** Itemized deltas, bounded loops, per-case diffing |
| it's a `CLAUDE.md` or repo rules file | **Redirect.** Context files take the opposite policy. It says so and stops |

It also handles prompts that must run on **more than one model family** — GPT-5.6 and Claude,
say — where several of the standard recommendations invert. Deletion is the dangerous one:
a guardrail is safe to cut only if *every* target model has internalised it.

## When not to use it

One-off chat prompts. `CLAUDE.md` and repo context files — opposite policy, and it will redirect
you. Brand voice and creative style guides.

It will also tell you to stop, fairly often. A flat headroom result is a real answer, not a
failed run.

## Does it actually work

It ships two eval harnesses and reports its own numbers rather than asking you to trust it.

| | measured |
|---|---|
| Routing — picks the right route and knows when to ask for the artifact | 42 cases, **97.6%**; 6 held-out cases, **100%** |
| Findings — recovers defects planted in fixture prompts | **81%** recall, 25 pt spread across runs |
| Findings — invents defects that are not there | **0** across every run measured |

Read [`evals/README.md`](evals/README.md) before believing those. It documents the noise floor,
which signals are stable enough to gate on, and where the graders disagree with each other.

Full writeup: [Prompt Engineering Best Practices in 2026: Why the Advice Contradicts Itself](https://www.amyzyuan.com/thoughts/prompt-engineering-best-practices-2026)

## For maintainers

Everything below is for changing the skill, not for using it.

- [`SKILL.md`](SKILL.md) — routing table and output contract
- [`references/`](references/) — one file per route, loaded on demand
- [`scripts/headroom_test.py`](scripts/headroom_test.py) — the go/no-go on whether optimization
  is worth running. `scripts/test_headroom.py` tests its decision rule offline
- [`evals/`](evals/) — the two harnesses, the case sets, and the honest limits

The skill documents a ratchet: additions are locally safe, deletions are locally unverifiable,
so artifacts only grow unless something stops them. Every addition needs a deletion of equal
size or a passing case that justifies it.

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...          # a Pro/Max plan is not an API key

python evals/run_routing.py  --snapshot baseline.json   # before editing
python evals/run_routing.py  --compare  baseline.json   # after
python evals/run_routing.py  --ablate                   # which files earn their tokens
python evals/run_findings.py --snapshot findings.json   # does the audit still find things
```

## License

MIT
