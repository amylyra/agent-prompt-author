# Route D — authoring a new prompt

## Procedure

**Draft minimal on the strongest available model. Add instructions only in response to failure modes you actually observed.**

Never start from a template and prune. A template inherits someone else's guardrails, written for a different model against failures you don't have — and you cannot tell which of its rules are load-bearing because you didn't watch any of them fail.

Order:
1. Write the minimal task statement plus the output contract. Nothing else.
2. Run it against 10–20 real cases. Watch the transcripts, not the summaries.
3. For each failure, ask which layer should own it (see the ladder in Route A step 4) before writing prose.
4. Add only what step 3 justifies. Re-run.
5. Stop when failures are in the tail rather than the pattern.

**Minimal does not mean short.** The target is the smallest set of high-signal tokens that gets the outcome. Sometimes that's long — a genuinely complex domain needs its context stated. What minimal excludes is content you added defensively without seeing the failure it prevents.

## The six rules. That is the budget.

1. **Right altitude.** Between brittle hardcoded if-else logic and vague guidance that falsely assumes shared context. Specific enough to steer, loose enough to leave strong heuristics.
2. **Heuristics, not prohibitions.** Write the property: "match the surrounding code's comment density, naming, and idiom" beats a list of banned constructs. Properties generalize to cases you didn't enumerate; prohibitions don't.
3. **5–8 live rules per scope**, not per file. The only lever on multiplicative decay. If you need more, you need another scope.
4. **Design the interface instead of giving examples.** A `status` enum of `pending | in_progress | completed` communicates usage with no worked example. Examples constrain the model to the exploration space they demonstrate.
5. **Keep 3–5 diverse canonical examples only where the output shape is genuinely non-obvious** and no type or schema can express it. Diverse and canonical — not a laundry list of edge cases.
6. **State effort explicitly.** Agents cannot judge it. Concrete scaling rules: simple fact-finding = 1 agent, 3–10 tool calls. Direct comparison = 2–4 subagents, 10–15 calls each. Complex research = 10+ with divided responsibilities.

## Delegation contracts

Any subagent, tool handoff, or skill invocation needs four things. Missing one produces duplicated work, gaps, or drift.

| Element | What it answers | Failure if missing |
|---|---|---|
| **Objective** | What does done look like? | Stops early or runs forever |
| **Output format** | What shape does the caller expect? | Caller can't parse; synthesis step fails |
| **Tool and source guidance** | Which tools, which sources, in what order? | Searches the web for something only in the DB |
| **Boundaries** | What is explicitly *not* this agent's job? | Two subagents duplicate; a third area goes uncovered |

"Research the semiconductor shortage" is a failed contract — it produced one subagent investigating the 2021 automotive chip crisis while two others duplicated 2025 supply-chain work.

## Tool descriptions are prompts

Write them for a new hire, not for an API reference.

- **Make implicit context explicit** — specialized query formats, niche terminology, relationships between resources.
- **Name parameters unambiguously.** `user_id`, not `user`.
- **State when to use this tool versus its neighbor.** If a human engineer can't say definitively which applies, the agent can't either.

Precise refinements to tool descriptions alone moved Claude Sonnet 3.5 to state of the art on SWE-bench Verified.

### Tool design

- **Consolidate rather than wrap endpoints.** `schedule_event` beats `list_users` + `list_events` + `create_event`. More tools is not better; agents have limited context where computer memory is cheap.
- **Namespace by service and resource** — `asana_projects_search`, `jira_search`. Prefix versus suffix has non-trivial measured effects that vary by model; pick yours by evaluation.
- **Return high-signal fields only.** Resolve raw UUIDs to semantic names or 0-indexed IDs — this measurably reduces hallucination. Drop `mime_type`, `256px_image_url`, and similar.
- **Expose a `response_format` enum** (concise / detailed) so the agent controls verbosity. One documented case: 72 tokens concise versus 206 detailed.
- **Cap and paginate**, with sensible defaults and a truncation message that steers ("try a narrower query" beats a silent cut).
- **Prompt-engineer error responses.** Specific and actionable, not opaque codes or tracebacks. The error message is an instruction the agent reads at the exact moment it needs one.

## Structure and caching

Organize into distinct sections — background, instructions, tool guidance, output description. Markdown headers are the safer default; XML tagging is Claude-idiomatic and current OpenAI guidance moves away from it. Exact formatting matters less as models improve; the separation is what helps. If the artifact targets more than one model family, see `references/portability.md`.

Cache discipline, if you control the API call: static content first, dynamic last. Append a system-reminder in messages rather than editing the prompt. Don't switch models mid-session — caches are model-specific; use a subagent if you need a cheaper one. Adding or removing a tool invalidates the cached prefix.
