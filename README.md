# agent-prompt-author

A Claude Skill for diagnosing and writing system prompts, orchestrator instructions, subagent delegation contracts, and tool descriptions. Prompt work fails for four predictable reasons:

1. The prompt was never the bottleneck.
2. The rule lives in a layer that can't enforce it — prose is a request, a hook is a gate.
3. Rules written for an older model are still firing.
4. The revision loop has no external verifier, so it optimizes readability instead of behavior.

Skipping straight to "write a better rule" is the default failure mode this skill is built to interrupt. Instead of rewriting on request, it routes through one of six diagnostic tests first: is the file even loaded into context, is optimization worth anything here (a ten-minute check you can price before running), do your agents actually interact (measured, not assumed), is the rule in a layer that can enforce it, and can anything fail — since a prompt with no runnable check optimizes for "looks done" instead of correctness.

Full writeup: [Prompt Engineering Best Practices in 2026: Why the Advice Contradicts Itself](https://www.amyzyuan.com/thoughts/prompt-engineering-best-practices-2026)

## What's in here

- `SKILL.md` — the skill definition and routing table
- `references/` — one file per route: enforcement, headroom, authoring, revision, audit, portability across model families, and sourced evidence for every claim
- `scripts/headroom_test.py` — runs candidate prompts against a held-out case set and returns a go/no-go on whether optimization has anything to find
- `scripts/test_headroom.py` — checks that go/no-go against a simulated world with no headroom in it, because a decision rule nobody tested is the failure this skill is about
- `evals/` — two harnesses. `run_routing.py` scores which route the skill picks, over 42 labeled cases plus a 6-case unburned holdout, on two independent dimensions. `run_findings.py` scores whether the audit Route F produces is actually right, against fixtures with defects planted on purpose. Routing correctly says nothing about diagnosing correctly, which is why there are two

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

## When to use it

**Use it when** you are changing the text of something you ship — a system prompt, an orchestrator, a subagent delegation contract, a tool description — and you want to know *what* to change before you change it. It is most useful at the two moments people usually skip: before adding a rule, and before running an optimizer.

**Do not use it for** one-off chat prompts, `CLAUDE.md` and repo context files (opposite policy — the skill will redirect you), or brand voice and creative style guides. It will also tell you to stop, fairly often. A flat headroom result is a real answer, not a failed run.

## Running the checks

Three of the scripts talk to the API and two do not.

| | Needs a key | What it costs |
|---|---|---|
| `scripts/headroom_test.py` | **yes** | ~$2 at `--effort low`, ~$5 at `high` — derive it, see `references/route-b-headroom.md` |
| `evals/run_routing.py` | **yes** | ~$1 for a 42-case, 3-run pass |
| `evals/run_findings.py` | **yes** | ~$2 for both fixtures at 3 runs |
| `scripts/test_headroom.py` | no | free, offline, stubbed |

Route F, the audit, needs neither a key nor a script — it is a reading procedure the model runs on your prompt.

```bash
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...      # console.anthropic.com -> API keys
```

Put the export in your shell profile, or use a `.env` and `direnv` — do not paste it into a prompt file, which is a thing that happens. A Claude Pro or Max subscription does **not** give you an API key; the API is billed separately, and these scripts use the API directly rather than going through Claude Code.

## Improving it

The skill documents a ratchet: additions are locally safe, deletions are locally unverifiable, so artifacts only grow unless something stops it. See `evals/README.md` for the rule — every addition needs a deletion of equal size, or a passing case that justifies it — checked with:

```bash
python evals/run_routing.py --snapshot baseline.json   # before editing
python evals/run_routing.py --compare baseline.json    # after editing
python evals/run_routing.py --ablate                   # which files earn their tokens
```
