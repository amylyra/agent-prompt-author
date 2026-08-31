#!/usr/bin/env python3
"""
Routing regression harness for agent-prompt-author.

Scores WHICH ROUTE the skill takes for each case — a label, not prose — so
regression is detectable without judging writing quality.

    python run_routing.py --snapshot baseline.json      # record a baseline
    python run_routing.py --compare baseline.json       # check for regression
    python run_routing.py --ablate                      # which files earn their tokens

Ablation is per-FILE, not per-rule. Six runs, not a hundred. Rule-level
ablation on a stochastic system is too noisy to be worth it; file-level is
cheap enough to run on every change.
"""
import argparse, json, os, sys, re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

try:
    import anthropic
except ImportError:
    sys.exit("pip install anthropic")

SKILL = Path(__file__).resolve().parent.parent
ROUTES = ["A", "B", "C", "D", "E", "F", "NONE"]
# Two labels out. High effort here bills thinking tokens for a classification.
EFFORT = "low"

PROBE = """You have the skill below available. A user sends the message in <request>.

Answer with TWO lines only, in exactly this form:
ROUTE: <A|B|C|D|E|NONE>
ASK: <YES|NO>

ROUTE is which route the skill takes. NONE means the skill should not fire.
ASK is whether the skill must request the artifact before it can give a finding.
These are independent: a request can route cleanly and still need the artifact.

<skill>
{skill}
</skill>

<request>
{req}
</request>"""


def load_skill(exclude=None):
    """SKILL.md is what determines routing. Route files load after."""
    text = (SKILL / "SKILL.md").read_text()
    if exclude == "SKILL.md":
        return "(skill unavailable)"
    return text


def cases(path=None):
    """Defaults to the tuned set. Point --cases at holdout.jsonl to measure the
    train-test gap, and never tune against whatever you point it at."""
    return [json.loads(l) for l in open(path or Path(__file__).parent / "routing.jsonl") if l.strip()]


def probe(client, model, skill_text, case):
    """Returns (route, ask). Two dimensions, because they are independent:
    a request can route cleanly and still need the artifact before a finding."""
    try:
        r = client.messages.create(
            model=model, max_tokens=24, output_config={"effort": EFFORT},
            messages=[{"role": "user", "content": PROBE.format(skill=skill_text, req=case["input"])}],
        )
        out = "".join(b.text for b in r.content if b.type == "text").upper()
        m = re.search(r"ROUTE:\s*([A-Z]+)", out)
        a = re.search(r"ASK:\s*(YES|NO)", out)
        return (m.group(1) if m and m.group(1) in ROUTES else "UNPARSED",
                (a.group(1) == "YES") if a else None)
    except Exception as e:
        print(f"  {case['id']} failed: {e}", file=sys.stderr)
        return ("ERROR", None)


def run(client, model, skill_text, cs, workers=8):
    with ThreadPoolExecutor(max_workers=workers) as ex:
        got = list(ex.map(lambda c: probe(client, model, skill_text, c), cs))
    results = {}
    for c, (route, ask) in zip(cs, got):
        results[c["id"]] = {
            "want": c["route"], "got": route,
            "want_ask": c["ask"], "got_ask": ask,
            "route_ok": c["route"] == route,
            "ok": c["route"] == route and c["ask"] == ask,
        }
    acc = 100.0 * sum(r["ok"] for r in results.values()) / len(results)
    return results, acc


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="claude-sonnet-5")
    p.add_argument("--runs", type=int, default=3, help="repeats, to measure the noise floor")
    p.add_argument("--snapshot")
    p.add_argument("--compare")
    p.add_argument("--ablate", action="store_true")
    p.add_argument("--cases", help="case file; defaults to evals/routing.jsonl")
    a = p.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("set ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(max_retries=5)
    cs = cases(a.cases)
    skill_text = load_skill()

    if a.ablate:
        print("ABLATION — does each file earn its tokens?\n")
        base_r, base_acc = run(client, a.model, skill_text, cs)
        print(f"  full skill: {base_acc:.1f}%")
        for f in sorted((SKILL / "references").glob("*.md")):
            trimmed = skill_text.replace(f"references/{f.name}", "(removed)")
            _, acc = run(client, a.model, trimmed, cs)
            delta = acc - base_acc
            verdict = "LOAD-BEARING" if delta < -4 else ("dead weight?" if delta >= -1 else "marginal")
            print(f"  without {f.name:<30} {acc:5.1f}%  ({delta:+.1f})  {verdict}")
        print("\nA file whose removal costs nothing is either unnecessary or untested by these cases.")
        print("Decide which before deleting it.")
        return 0

    print(f"{len(cs)} cases x {a.runs} runs, model {a.model}\n")
    accs, last = [], None
    for i in range(a.runs):
        results, acc = run(client, a.model, skill_text, cs)
        accs.append(acc); last = results
        print(f"  run {i+1}: {acc:.1f}%")
    mean = sum(accs) / len(accs)
    noise = max(accs) - min(accs) if len(accs) > 1 else 0.0
    print(f"\n  mean {mean:.1f}%   noise floor {noise:.1f} pts")

    misses = {k: v for k, v in last.items() if not v["ok"]}
    if misses:
        print(f"\n  misroutes ({len(misses)}), last run:")
        by_id = {c["id"]: c for c in cs}
        for k, v in misses.items():
            ask = "" if v["route_ok"] else " "
            print(f"    {k}  want {v['want']}/ask={v['want_ask']:<5} "
                  f"got {v['got']}/ask={v['got_ask']}{ask}  {by_id[k]['note'][:44]}")

    if a.snapshot:
        json.dump({"mean": mean, "noise": noise, "results": last}, open(a.snapshot, "w"), indent=1)
        print(f"\n  baseline written to {a.snapshot}")

    if a.compare:
        old = json.load(open(a.compare))
        bar = max(old.get("noise", 0), noise, 2.0)
        delta = mean - old["mean"]
        print(f"\n  baseline {old['mean']:.1f}%  →  now {mean:.1f}%  ({delta:+.1f}, bar {bar:.1f})")
        newly_broken = [k for k, v in last.items()
                        if not v["ok"] and old["results"].get(k, {}).get("ok")]
        newly_fixed = [k for k, v in last.items()
                       if v["ok"] and not old["results"].get(k, {}).get("ok", True)]
        if newly_fixed:  print(f"  fixed:  {', '.join(newly_fixed)}")
        if newly_broken: print(f"  BROKE:  {', '.join(newly_broken)}")
        if newly_broken:
            print("\n  REGRESSION. A flat mean can hide equal numbers fixed and broken —")
            print("  which is why this compares per case, not just the average.")
            return 1
        if delta < -bar:
            print("\n  REGRESSION on the mean."); return 1
        print("\n  no regression.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
