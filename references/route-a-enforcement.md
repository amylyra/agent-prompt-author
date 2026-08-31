# Route A — the rule isn't being followed

**Do not rewrite the rule.** Work down this ladder and stop at the first hit. Wording is the last thing to check, not the first.

## 1. Is it loaded?

Confirm the text is actually in the assembled context. Memory and context files are documented as *context, not enforced configuration*, with no guarantee of compliance. Log the real prompt. In Claude Code: `/context` and `/memory`. Nested files may load only when a file in that directory is read; exclusion settings may skip files entirely.

**If it isn't loaded, that's the finding.** Stop.

## 2. Is it competing?

Compliance decays multiplicatively — at 95% per instruction, ten instructions gives ~60%. Count **live rules in this scope**, not lines in the file. Over ~8 is the finding.

Fix by moving rules out of scope (path-scoped rule files, progressive disclosure into a tree), not by shortening the ones that remain. Length is a constraint; count is the objective. Compressing ten rules into five sentences manufactures ambiguity and changes nothing.

`scripts/audit_prompt.py <file>` counts this for you, per scope, and exits non-zero when a scope is over budget. It needs no API key. It also flags the things steps 4 and 5 below look for — unmeasurable rules, meta-instructions, bans with no replacement, and rules that belong in a schema, an enum, or a hook — so run it before reading further rather than eyeballing the count.

## 3. Does it conflict?

Check pairs **within the same scope only**. Pairwise across 200 rules produces a confident, wrong answer — scoping is what makes conflict detection tractable. `scripts/audit_prompt.py <file> --conflicts` does exactly this pass, one scope at a time; it is the only part of that script that needs an API key.

Conflicts rarely surface as errors. Models seldom recognize contradictions or ask for clarification, so a conflict shows up as drift: the rule holds sometimes. Intermittent compliance is the signature.

Common shapes:
- Two rules constraining the same dimension in opposite directions ("be concise" / "explain your reasoning fully")
- A general rule and a specific exception that never names the general rule
- A rule inherited from a template that contradicts a rule written for this task

## 4. Is it in the wrong layer?

Move the constraint down. Only the bottom actually blocks:

```
prose rule
  → rubric checked by an isolated verifier
    → test case
      → tool enum or output schema
        → hook
```

| If the rule is… | It belongs in… |
|---|---|
| "Always return valid JSON with fields a, b, c" | Output schema |
| "Use search for broad queries, DB for lookups" | Tool names and descriptions |
| "Only one of pending / in_progress / completed" | Enum |
| "Match our house tone" | Rubric + verifier agent |
| "Never commit without running tests" | Hook |

If it can be expressed as a check, it should not be prose.

## 5. Is it obsolete?

Ask whether the rule guards a failure mode **this model still has**. Guardrails written for a weaker generation become dead weight. Anthropic removed over 80% of Claude Code's system prompt for the Claude 5 generation with no measured regression on coding evals.

The counterfactual test: *would this rule have prevented a real, observed mistake?* Check session history, not intuition. If no — flag it, don't auto-delete. Ablation on a stochastic system is noisy and scar tissue often guards a tail case the eval set never sampled.

## Only now does wording matter

If all five clear:

- **Name a specific token rather than requesting a quality.** "Don't write 'delve'" is checkable; "write naturally" is a preference competing with everything else.
- **Pair every ban with its replacement.** A rule that only forbids leaves a gap, and the gap is where invented behavior comes from.
- **Give judgment rules a rationale.** A rule without a "why" collapses at the first edge case, and real work is mostly edge cases. Format rules don't need one — those should have left for the linter at step 4.

## Diagnostic worth surfacing

Wanting to add "make sure to", "do not", "ensure", or "remember to" is the strongest measured **negatively** associated edit family (−0.103 on math tasks, FDR-corrected across 2,095 prompt-pair comparisons).

Two live explanations, both actionable:
1. The model has already internalized the guideline; the instruction is redundant complexity.
2. Optimizers insert meta-instructions specifically when the prompt is already struggling — so the urge is a symptom of an upstream problem, not a fix.

Either way: treat the impulse as a signal to re-run steps 1–5, not as the solution.
