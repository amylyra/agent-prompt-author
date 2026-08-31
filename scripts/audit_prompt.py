#!/usr/bin/env python3
"""
Structural audit of a prompt. Is it sound before you argue about wording?

Route A step 4 says: if it can be expressed as a check, it should not be prose.
The count and conflict guidance in this skill was prose. This is the check.

Everything here is deterministic and free — no API key, no network. It answers
the questions you can answer without a model:

    how many live rules are in each scope, against the 5-8 budget
    which rules are unmeasurable, so nothing can verify them
    which are meta-instructions, the measured-negative edit family
    which ban something without saying what to do instead
    which belong in a schema, an enum, or a hook rather than in prose

Known limit: a document that *discusses* these patterns trips them. This skill's
own `references/route-a-enforcement.md` flags twice, both on sentences quoting the
banned forms in order to teach them. Read the flags, do not obey them blindly.

It does NOT tell you whether the prompt is any good. A clean report on a prompt
that solves the wrong problem is still a clean report. Route B decides whether
the prompt is the bottleneck; this decides whether it is structurally sound.

    python scripts/audit_prompt.py path/to/prompt.md
    python scripts/audit_prompt.py path/to/prompt.md --json
    python scripts/audit_prompt.py path/to/prompt.md --conflicts   # needs a key

Exit code is 1 if any scope is over budget, so it works as a CI gate.
"""

import argparse, json, os, re, sys
from pathlib import Path

BUDGET = 8          # Route D rule 3: 5-8 live rules per scope
BUDGET_IDEAL = 5

# A rule is a sentence that tells the model to do or not do something.
DIRECTIVE = re.compile(
    r"\b(must|should|never|always|do not|don't|avoid|ensure|require[sd]?|only|"
    r"prefer|need to|have to|make sure|remember to|be sure to|shall|cannot|"
    r"can't|no longer|refuse|reject|forbid)\b", re.I)
IMPERATIVE_START = re.compile(
    r"^\**(use|write|keep|stop|start|return|call|check|read|add|remove|delete|"
    r"match|treat|state|name|report|ask|prefer|apply|run|set|pick|choose|give|"
    r"include|exclude|follow|cite|list|explain|describe|limit|split|merge)\b", re.I)

# Anthropic/OpenAI convergent finding: meta-instructions are the strongest
# measured-negative edit family (-0.103 on math, FDR-corrected).
META = re.compile(r"\b(make sure to|be sure to|remember to|do not forget|"
                  r"don't forget|always remember|it is important that|"
                  r"it's important that|you must always|never ever)\b", re.I)

# Requests a quality instead of naming a checkable token.
VAGUE = re.compile(r"\b(appropriate(ly)?|as needed|when relevant|when appropriate|"
                   r"high[- ]quality|natural(ly)?|properly|carefully|thoughtful(ly)?|"
                   r"good|best practices?|reasonable|sensible|clean|nice|"
                   r"as necessary|if needed|etc\.?)\b", re.I)

# Belongs in a lower layer: schema, enum, tool description, or hook.
LAYERABLE = [
    (re.compile(r"\b(valid )?json\b|\bschema\b|\bwell[- ]formed\b", re.I), "output schema"),
    (re.compile(r"\bone of\b.*\||\benum\b|\bexactly one of\b", re.I), "enum"),
    (re.compile(r"\bnever (commit|push|merge|deploy)\b|\bbefore (committing|pushing)\b", re.I), "hook"),
    (re.compile(r"\buse the \w+ tool\b|\bcall \w+ (for|when)\b", re.I), "tool description"),
    (re.compile(r"\b(word|character|token|line)s? (limit|maximum|max)\b|\bat most \d+\b|"
                r"\bno more than \d+\b|\bunder \d+ (word|char|token|line)|"
                r"\bfewer than \d+\b", re.I), "linter or max_tokens"),
]

# A ban tells the reader not to do something. A sentence that merely contains
# "never" is usually describing the world, not prohibiting an action — flagging
# those is how a linter teaches people to ignore it.
BAN = re.compile(r"^\W*(never|do not|don't|avoid|no)\b|"
                 r"\byou (must not|should never|should not|may not)\b", re.I)
REPLACEMENT = re.compile(r"\b(instead|rather than|use .* instead|prefer|in place of|"
                         r"replace .* with|write .* instead)\b", re.I)


def strip_noise(text):
    """Frontmatter is metadata and fenced blocks are illustrations. Neither is
    a rule the model follows, and counting them inflates every number here."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            text = text[end + 4:]
    out, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
            continue
        if not fenced:
            out.append(line)
    return "\n".join(out)


def scopes(text):
    """Split on markdown headings. A scope is what competes for adherence."""
    out, name, buf = [], "(preamble)", []
    for line in text.splitlines():
        m = re.match(r"^(#{1,6})\s+(.*)", line)
        if m:
            if buf: out.append((name, buf))
            name, buf = m.group(2).strip(), []
        else:
            buf.append(line)
    if buf: out.append((name, buf))
    return [(n, b) for n, b in out if any(l.strip() for l in b)]


def units(lines):
    """Bullets and standalone sentences — the things a model reads as one rule."""
    out, para = [], []
    for line in lines:
        st = line.strip()
        if re.match(r"^([-*+]|\d+\.)\s+", st):
            if para: out.append(" ".join(para)); para = []
            out.append(re.sub(r"^([-*+]|\d+\.)\s+", "", st))
        elif st.startswith("|") or st.startswith("```") or st.startswith(">"):
            continue                            # tables, code, quotes are not prose rules
        elif not st:
            if para: out.append(" ".join(para)); para = []
        else:
            para.append(st)
    if para: out.append(" ".join(para))
    return [u for u in out if len(u) > 12]


def is_rule(u):
    return bool(DIRECTIVE.search(u) or IMPERATIVE_START.match(u.strip()))


def audit(text):
    report, total = [], 0
    for name, lines in scopes(text):
        rules = [u for u in units(lines) if is_rule(u)]
        total += len(rules)
        findings = []
        for r in rules:
            short = re.sub(r"\s+", " ", re.sub(r"[*`]", "", r))[:88]
            if META.search(r):
                findings.append(("meta-instruction", short))
            if VAGUE.search(r):
                findings.append(("unmeasurable", short))
            if BAN.search(r) and not REPLACEMENT.search(r):
                findings.append(("ban with no replacement", short))
            for pat, layer in LAYERABLE:
                if pat.search(r):
                    findings.append((f"belongs in {layer}", short)); break
        report.append({"scope": name, "rules": len(rules),
                       "over_budget": len(rules) > BUDGET, "findings": findings})
    return report, total


def conflicts(text, report, model):
    """Pairwise within a scope only. Across a whole file it produces a confident
    wrong answer — scoping is what makes conflict detection tractable."""
    try:
        import anthropic
    except ImportError:
        sys.exit("pip install anthropic")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("--conflicts needs ANTHROPIC_API_KEY; the rest of this audit does not")
    client = anthropic.Anthropic(max_retries=5)
    out = []
    for name, lines in scopes(text):
        rules = [u for u in units(lines) if is_rule(u)]
        if len(rules) < 2:
            continue
        listing = "\n".join(f"{i+1}. {re.sub(r'[*`]', '', r)}" for i, r in enumerate(rules))
        prompt = (
            "Below are the rules in one scope of a system prompt. Find pairs that "
            "constrain the SAME dimension in OPPOSITE directions, or where a specific "
            "rule contradicts a general one without naming it.\n\n"
            "Report only genuine conflicts a model would have to silently pick between. "
            "Overlap is not conflict. If there are none, reply exactly NONE.\n\n"
            f"{listing}\n\nFormat each as: <n> vs <m>: <the dimension they fight over>")
        r = client.messages.create(model=model, max_tokens=400,
                                   output_config={"effort": "medium"},
                                   messages=[{"role": "user", "content": prompt}])
        txt = "".join(b.text for b in r.content if b.type == "text").strip()
        if txt.upper() != "NONE":
            out.append((name, txt))
    return out


def main():
    p = argparse.ArgumentParser()
    p.add_argument("path")
    p.add_argument("--conflicts", action="store_true",
                   help="add a pairwise conflict pass within each scope (needs an API key)")
    p.add_argument("--model", default="claude-sonnet-5")
    p.add_argument("--json", action="store_true")
    a = p.parse_args()

    raw = Path(a.path).read_text()
    text = strip_noise(raw)
    report, total = audit(text)
    over = [s for s in report if s["over_budget"]]

    if a.json:
        print(json.dumps({"total_rules": total, "scopes": report,
                          "over_budget": [s["scope"] for s in over]}, indent=1))
        return 1 if over else 0

    words = len(raw.split())
    print(f"{a.path}: {words} words, ~{int(words * 1.35)} tokens, "
          f"{len(report)} scopes, {total} live rules\n")
    print(f"{'scope':<44} {'rules':>5}")
    for s in report:
        flag = "  OVER" if s["over_budget"] else ("  ok" if s["rules"] <= BUDGET_IDEAL else "")
        print(f"  {s['scope'][:42]:<42} {s['rules']:>5}{flag}")

    flagged = [(s["scope"], k, t) for s in report for k, t in s["findings"]]
    if flagged:
        print(f"\n{len(flagged)} flagged:")
        for scope, kind, txt in flagged:
            print(f"  [{kind}]  {scope[:28]}")
            print(f"      {txt}")

    if a.conflicts:
        print("\nconflict pass (within scope only):")
        found = conflicts(text, report, a.model)
        for name, txt in found or []:
            print(f"  {name}\n    " + txt.replace("\n", "\n    "))
        if not found:
            print("  none found")

    print()
    if over:
        print(f"OVER BUDGET: {len(over)} scope(s) carry more than {BUDGET} live rules. "
              f"Compliance decays multiplicatively;\nat 95% per rule, ten rules is ~60%. "
              f"Move rules out of scope — do not shorten the ones that remain.")
        for s in over:
            print(f"  {s['scope']}: {s['rules']}")
        return 1
    print(f"All scopes within the {BUDGET}-rule budget.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
