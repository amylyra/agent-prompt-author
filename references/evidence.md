# Evidence

Every quantitative claim in this skill, with its source. Read this file only when a claim is challenged or sources are requested.

Sources marked **[full]** were read end to end. The rest are from abstracts or secondary coverage — verify before treating them as load-bearing.

## Deletion and context collapse

| Claim | Source |
|---|---|
| Over 80% of Claude Code's system prompt removed for Claude 5 generation, no measurable loss on coding evals | Shihipar, "The new rules of context engineering for Claude 5 generation models," Anthropic, 24 Jul 2026 **[full]** |
| Context collapse and brevity bias; accumulating beat compressing by +10.6% on agents, +8.6% on finance; deterministic non-LLM merge of delta entries | Zhang et al., "Agentic Context Engineering," arXiv 2510.04618, ICLR 2026 |
| One-verifier-per-rule; skeptic persona; "would this rule have prevented a real mistake" counterfactual | Shihipar & Bidasaria, "A harness for every task," Anthropic, 2 Jun 2026 **[full]** |

**Note the tension.** These operate on different objects — obsolete guardrails versus accumulated domain knowledge. Neither result generalizes to the other's object.

## Instruction count and adherence

| Claim | Source |
|---|---|
| Prompt-level accuracy = per-instruction accuracy ^ n; Claude 3.5 Sonnet at 44% on 10 instructions | Harada et al., ManyIFEval / "Curse of Instructions" |
| Instruction-level self-refinement lifted 10-instruction compliance 44% → 58% | same |
| No consistent relationship between instruction position and follow rate | arXiv 2510.14842 |
| Memory files are context, not enforced configuration | Claude Code memory documentation, via Lorenz, primeline.cc, 15 Aug 2026 — *secondhand, verify* |
| Models seldom recognize contradictions or ask for clarification | ConInstruct, AAAI 2026 |

Measured on Claude 3.5. Re-verify against a current model before using 44% as a threshold.

## Optimization

| Claim | Source |
|---|---|
| 49% of 72 runs below zero-shot, binomial p = 0.91; agent interaction never significant (all F < 1.0, 0.18–2.15% of variance); difficulty explains 19–91% of variance; the one successful task required structured rubrics + JSON (+6.8 vs +1.1/+0.7/+0.6); iterative train-test gaps to 5.6 pts; two-stage diagnostic at ~$85 | Zhang et al., "Prompt Optimization Is a Coin Flip," arXiv 2604.14585 **[full]** |
| Meta-instruction insertion × math = −0.103 ACMGD, FDR-corrected; clarity-constraint × logical = −0.083; 2,095 DSPy pairs + 17,708 TextGrad/GEPA | Gong & Wen, arXiv 2605.26655 **[full]** |
| GEPA beats GRPO by up to 20% with 35× fewer rollouts; beats MIPROv2 by >10% | Agrawal et al., arXiv 2507.19457, ICLR 2026 |
| GEPA over-indexes on minibatch surface patterns; early rounds insert verbatim training content; production guidance is incremental bullet optimization | gepa-ai/gepa FAQ |
| +10% SWE-bench optimizing only CLAUDE.md; +15% Cline; ~150 examples | Arize AI |
| ~9% of surveyed agents use any automated optimization | Nie et al., arXiv 2603.23994 |
| GEPA gave only modest gains: 81.0%→84.0% compile, 5.0%→7.5% test pass | SuperCoder, arXiv 2505.11480 |

**Caveats on the coin-flip result:** observational grid on two mid-tier models (Claude Haiku 4.5, Amazon Nova Lite); whole-prompt substitutions, so finer edits could expose interaction; 20 training questions; single two-agent feed-forward architecture. The authors name conditions under which coupling may still emerge.

**Caveats on the edit-level result:** IPTW-adjusted associations, not causal effects. Only 2 of 60 feature tests survive FDR correction against ~3 false positives expected by chance. The math effect concentrates in one dataset (MultiArith −0.277, n=64 vs GSM8K −0.019, n=14). Reasoning benchmarks, not agentic system prompts.

## Iteration and degradation

| Claim | Source |
|---|---|
| Largest gains in first 1–2 rounds; failure mode is reward hacking between generator and in-context judge | Self-refinement survey literature |
| Second iteration counterproductive after first improved nearly all metrics | arXiv 2601.11578 |
| 43.7% of GPT-4o chains had more vulnerabilities than baseline after 10 rounds; SAST gating raised latent degradation 12.5% → 20.8% | SCAFFOLD-CEGIS, arXiv 2603.08520 |
| Accuracy–correction paradox; unconditional self-correction as compute waste | arXiv 2604.22273 |
| Retrospective capability decay; Capability-Preserving Evolution 41.8% → 52.8% retained | arXiv 2605.09315 |
| Zero-regression rate below 0.25 for most models; only Opus-class above 0.5 | SWE-CI, arXiv 2603.03823 |
| Iteration-5 peak; selecting agent most often picks 5, not the last | CC-GSEO-Bench, arXiv 2509.05607 |
| 5–10 iterations, weakest dimension first, select by held-out validation | arXiv 2603.27440 |

## Audit and current-generation scaffolding

Route F's cut/keep lists. All read in full, August 2026 — these are the fastest-decaying
claims in the skill because each one exists where a previous generation needed the opposite.

| Claim | Source |
|---|---|
| Remove verification instructions and "double-check your answer" — Opus 5 verifies and self-corrects unprompted, and these compound into over-verification with no quality gain; scope expansion and delegation need explicit caps | Anthropic, "Prompting Claude Opus 5," platform docs **[full]** |
| More literal instruction following — the model does not silently generalise an instruction from one item to another, so breadth must be stated; a qualitative bar ("only high-severity") is followed faithfully and drops findings, lowering measured recall without a capability loss; `temperature` / `top_p` / `top_k` return 400 | Anthropic, "Prompting Claude Sonnet 5," platform docs **[full]** |
| Dial back anti-laziness prompting — instructions that fixed undertriggering now overtrigger; replace blanket defaults with conditional ones; a rule telling the model not to think increases internal-tag leakage; long inputs at the top with the query last is worth up to ~30% on multi-document inputs; 3–5 examples | Anthropic, "Prompting best practices," platform docs **[full]** |
| `output_config.effort` defaults to `high` and is billed on thinking tokens as well as output | Anthropic, "Effort," platform docs **[full]** |
| Invariant-versus-default test; the four scaffolding classes; the six-condition survival rule; the conflict taxonomy; the two-evaluator operationalization test | "A 2026 Framework for Auditing LLM Prompts," 31 Aug 2026 — a synthesis of the above plus current OpenAI guidance, not a primary source. Its structural tests are reasoning, not measurements; its quantitative claims trace to the rows above and to `portability.md` |

## Agent design

| Claim | Source |
|---|---|
| Four-part delegation contract; effort scaling rules; semiconductor-shortage failure; tool-testing agent → 40% faster completion | Hadfield et al., "How we built our multi-agent research system," Anthropic, 13 Jun 2025 **[full]** |
| Tool description refinements → SOTA on SWE-bench Verified; UUID resolution reduces hallucination; response_format 72 vs 206 tokens; 25,000-token default response cap | Aizawa, "Writing effective tools for agents," Anthropic, 11 Sep 2025 **[full]** |
| Right altitude; minimal ≠ short; start minimal on best model then add from observed failures; diverse canonical examples | "Effective context engineering for AI agents," Anthropic, 29 Sep 2025 **[full]** |
| Agentic laziness, self-preferential bias, goal drift; comparative > absolute for ranking; six orchestration patterns | "A harness for every task," Anthropic, 2 Jun 2026 **[full]** |
| Single judge, one prompt, 0.0–1.0 + pass/fail most consistent for grading one output | Hadfield et al. **[full]** |
| Harness assumptions go stale; context resets became dead weight one generation later | Martin, "Agent Harness Design," Anthropic, 2 Apr 2026 **[full]** |
| All 18 frontier models degrade with input length at every increment | Chroma, "Context Rot," 2025 |
