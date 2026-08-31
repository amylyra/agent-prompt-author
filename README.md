# agent-prompt-author

A Claude Skill for diagnosing and writing system prompts, orchestrator instructions, subagent delegation contracts, and tool descriptions. Prompt work fails for four predictable reasons:

1. The prompt was never the bottleneck.
2. The rule lives in a layer that can't enforce it — prose is a request, a hook is a gate.
3. Rules written for an older model are still firing.
4. The revision loop has no external verifier, so it optimizes readability instead of behavior.

Skipping straight to "write a better rule" is the default failure mode this skill is built to interrupt. Instead of rewriting on request, it routes through one of five diagnostic tests first: is the file even loaded into context, is optimization worth anything here (a $5, ten-minute check), do your agents actually interact (measured, not assumed), is the rule in a layer that can enforce it, and can anything fail — since a prompt with no runnable check optimizes for "looks done" instead of correctness.

Full writeup: [Prompt Engineering Best Practices in 2026: Why the Advice Contradicts Itself](https://www.amyzyuan.com/thoughts/prompt-engineering-best-practices-2026)

## What's in here

- `SKILL.md` — the skill definition and routing table
- `references/` — one file per route: enforcement, headroom, authoring, revision, portability across model families, and sourced evidence for every claim
- `scripts/headroom_test.py` — runs candidate prompts against a held-out case set and returns a go/no-go on whether optimization has anything to find
- `scripts/test_headroom.py` — checks that go/no-go against a simulated world with no headroom in it, because a decision rule nobody tested is the failure this skill is about
- `evals/` — a routing regression harness with 24 labeled cases (canonical, ambiguous, precondition, negative), so edits to the skill are checked against regressions instead of judged by feel

## Install

**Skills CLI** — Claude Code, Cursor, Windsurf, VS Code, JetBrains. Node 18+.

```bash
npx skills add amylyra/agent-prompt-author -g
```

Drop `-g` to install into the current project instead of globally.

**Claude Code plugin marketplace**

```
/plugin marketplace add amylyra/skills-marketplace
/plugin install agent-prompt-author@amy-skills
```

**Manual** — drop this directory into `.claude/skills/agent-prompt-author/` in a project, or wherever your Claude setup loads skills from.

**claude.ai** — Settings → Capabilities → Skills, upload a `.zip` of this folder with the folder as the zip root. Needs Pro, Max, Team, or Enterprise with code execution enabled.

## Improving it

The skill documents a ratchet: additions are locally safe, deletions are locally unverifiable, so artifacts only grow unless something stops it. See `evals/README.md` for the rule — every addition needs a deletion of equal size, or a passing case that justifies it — checked with:

```bash
python evals/run_routing.py --snapshot baseline.json   # before editing
python evals/run_routing.py --compare baseline.json    # after editing
python evals/run_routing.py --ablate                   # which files earn their tokens
```
