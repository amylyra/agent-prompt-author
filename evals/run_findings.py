#!/usr/bin/env python3
"""
Finding-class harness: was the audit RIGHT, not just routed correctly?

run_routing.py scores which route the skill picks. That is the cheap half. This
scores what Route F actually finds, against fixtures with defects planted on
purpose:

    recall    — of the planted defects, how many did the audit report?
    invented  — of the findings it reported, how many are not true of the text?

Both matter, and only having the first is how you end up with an audit that
reports nine things about everything. `clean-triage.md` is the negative control:
a well-built prompt where the correct output is almost nothing.

    python run_findings.py                      # score the audit
    python run_findings.py --fixture clean-triage.md
    python run_findings.py --snapshot base.json
    python run_findings.py --compare base.json

Grading is a separate model call per item, one narrow question at a time — a
judge asked "did this specific defect get reported, yes or no" is doing a task
it is reliable at. A judge asked "is this a good audit" is not.
"""
import argparse, json, os, re, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

try:
    import anthropic
except ImportError:
    sys.exit("pip install anthropic")

SKILL = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent

AUDIT = """You have the skill below. Apply Route F to the prompt in <artifact>.

Return ONLY a JSON array, no prose around it. One object per finding:
[{{"finding": "<one sentence stating the defect>", "evidence": "<the text it is about>"}}]

Report every structural defect you find. Do not filter for importance — a
separate step does that. If the prompt is sound, return a short array or [].

<skill>
{skill}
</skill>

<route_f>
{route}
</route_f>

<artifact>
{artifact}
</artifact>"""

RECALL = """A prompt was audited. Did the audit report THIS defect?

<defect>{defect}</defect>

<audit_findings>
{found}
</audit_findings>

Answer YES if some finding describes this defect, even in different words.
Answer NO if none of them do. Do not credit a vague finding that would match
almost any prompt. One word only: YES or NO."""

GROUNDED = """Here is a prompt and one claim an audit made about it.

<prompt>
{artifact}
</prompt>

<claim>{finding}</claim>

Is the claim factually true of that prompt text? A claim can be true and still
be a matter of judgment — answer YES for those. Answer NO only if the claim
misdescribes the prompt or refers to something that is not there.
One word only: YES or NO."""


def ask(client, model, prompt, tokens=16):
    r = client.messages.create(model=model, max_tokens=tokens,
                               output_config={"effort": "low"},
                               messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in r.content if b.type == "text").strip().upper()


def audit(client, model, artifact):
    r = client.messages.create(
        model=model, max_tokens=2000, output_config={"effort": "medium"},
        messages=[{"role": "user", "content": AUDIT.format(
            skill=(SKILL / "SKILL.md").read_text(),
            route=(SKILL / "references/route-f-audit.md").read_text(),
            artifact=artifact)}])
    txt = "".join(b.text for b in r.content if b.type == "text")
    m = re.search(r"\[.*\]", txt, re.S)
    if not m:
        return []
    try:
        return [f for f in json.loads(m.group(0)) if isinstance(f, dict)]
    except json.JSONDecodeError:
        return []


def score_one(client, model, rec):
    artifact = (HERE / "fixtures" / rec["fixture"]).read_text()
    found = audit(client, model, artifact)
    listing = "\n".join(f"- {f.get('finding','')}" for f in found) or "(none)"

    with ThreadPoolExecutor(max_workers=6) as ex:
        rec_hits = list(ex.map(
            lambda p: ask(client, model, RECALL.format(defect=p["defect"], found=listing)).startswith("YES"),
            rec["planted"]))
        grounded = list(ex.map(
            lambda f: ask(client, model, GROUNDED.format(artifact=artifact, finding=f.get("finding", ""))).startswith("YES"),
            found))

    absent = rec.get("absent", [])
    with ThreadPoolExecutor(max_workers=4) as ex:
        false_alarms = list(ex.map(
            lambda p: ask(client, model, RECALL.format(defect=p["defect"], found=listing)).startswith("YES"),
            absent))
    falsely_claimed = [p["id"] for p, hit in zip(absent, false_alarms) if hit]

    planted = rec["planted"]
    recovered = [p["id"] for p, hit in zip(planted, rec_hits) if hit]
    missed = [p["id"] for p, hit in zip(planted, rec_hits) if not hit]
    invented = [f.get("finding", "")[:70] for f, g in zip(found, grounded) if not g]
    by_class = {}
    for p, hit in zip(planted, rec_hits):
        got, tot = by_class.get(p["class"], (0, 0))
        by_class[p["class"]] = (got + hit, tot + 1)

    return {"fixture": rec["fixture"], "reported": len(found),
            "falsely_claimed": falsely_claimed, "n_absent": len(absent),
            "recall": (len(recovered) / len(planted)) if planted else None,
            "recovered": recovered, "missed": missed,
            "invented": invented, "by_class": by_class,
            "max_missed": rec.get("max_missed", 0),
            "expect_recall": rec.get("expect_recall"),
            }


def repeat(client, model, rec, runs):
    """Average `runs` scorings of the same fixture and keep the spread.

    A single audit is one sample of a stochastic process. Measured here, recall
    on the same fixture and the same skill moved 42-75% across runs, so a
    one-run score is not evidence that an edit helped.
    """
    rs = [score_one(client, model, rec) for _ in range(runs)]
    recalls = [r["recall"] for r in rs if r["recall"] is not None]
    agg = dict(rs[-1])
    agg["runs"] = runs
    agg["recall"] = (sum(recalls) / len(recalls)) if recalls else None
    agg["recall_spread"] = (max(recalls) - min(recalls)) if len(recalls) > 1 else 0.0
    agg["invented"] = max(rs, key=lambda r: len(r["invented"]))["invented"]
    agg["reported"] = sum(r["reported"] for r in rs) / runs
    # A defect counts as missed only if it was missed in every run; a class the
    # skill finds sometimes is flaky, not absent, and the two need different fixes.
    agg["missed"] = sorted(set.intersection(*[set(r["missed"]) for r in rs]))
    agg["flaky"] = sorted(set.union(*[set(r["missed"]) for r in rs]) - set(agg["missed"]))
    agg["falsely_claimed"] = sorted(set.intersection(*[set(r["falsely_claimed"]) for r in rs])) \
        if rs[0]["n_absent"] else []
    return agg


def report(r):
    print(f"\n{r['fixture']}  —  {r['reported']:.1f} findings reported (mean)")
    if r["recall"] is not None:
        print(f"  recall    {r['recall']*100:.0f}%  mean of {r['runs']} runs, "
              f"spread {r['recall_spread']*100:.0f} pts")
        for cls, (got, tot) in sorted(r["by_class"].items()):
            print(f"      {cls:<12} {got}/{tot}")
        if r["missed"]:
            print(f"  missed    {', '.join(r['missed'])}   (every run)")
        if r["flaky"]:
            print(f"  flaky     {', '.join(r['flaky'])}   (found in some runs)")
    if r["n_absent"]:
        print(f"  absent    {r['n_absent']-len(r['falsely_claimed'])}/{r['n_absent']} correctly not claimed")
    print(f"  invented  {len(r['invented'])}")
    for i in r["invented"]:
        print(f"      {i}")

    ok = True
    # Gate on the stable signals only. Recall swung 25-50 points across three
    # runs of an unchanged skill, so thresholding it would fail at random; it is
    # reported as a band and a diagnostic instead. `invented` is also ungated:
    # the grounded judge and the recall judge disagreed about the same finding
    # string, so it is not yet trustworthy enough to block on.
    if len(r["missed"]) > r["max_missed"]:
        print(f"  FAIL {len(r['missed'])} defect(s) missed by every run "
              f"(allowed {r['max_missed']}) — a class the route does not cover"); ok = False
    lo, hi = r["expect_recall"] or (0, 1)
    if r["recall"] is not None and not (lo <= r["recall"] <= hi):
        print(f"  note  recall {r['recall']:.0%} outside the {lo:.0%}-{hi:.0%} band "
              f"seen when this was calibrated. Not a failure — re-measure before believing it")
    if r["falsely_claimed"]:
        print(f"  FAIL negative control, claimed absent classes: "
              f"{', '.join(r['falsely_claimed'])}"); ok = False
    return ok


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default="claude-sonnet-5")
    p.add_argument("--fixture", help="score one fixture instead of all")
    p.add_argument("--runs", type=int, default=3,
                   help="repeats. An audit is a stochastic output and one run of it is "
                        "not a measurement; the spread across runs is your noise floor.")
    p.add_argument("--snapshot")
    p.add_argument("--compare")
    a = p.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("set ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(max_retries=5)

    recs = [json.loads(l) for l in open(HERE / "findings.jsonl") if l.strip()]
    if a.fixture:
        recs = [r for r in recs if r["fixture"] == a.fixture] or sys.exit("no such fixture")

    results = [repeat(client, a.model, r, a.runs) for r in recs]
    ok = all([report(r) for r in results])

    if a.snapshot:
        json.dump(results, open(a.snapshot, "w"), indent=1)
        print(f"\nbaseline written to {a.snapshot}")

    if a.compare:
        old = {r["fixture"]: r for r in json.load(open(a.compare))}
        print()
        for r in results:
            o = old.get(r["fixture"])
            if not o:
                continue
            broke = sorted(set(r["missed"]) - set(o["missed"]))
            fixed = sorted(set(o["missed"]) - set(r["missed"]))
            if fixed: print(f"  {r['fixture']}: now found  {', '.join(fixed)}")
            if broke:
                print(f"  {r['fixture']}: NOW MISSED {', '.join(broke)}")
                ok = False
        print("\n  regression." if not ok else "\n  no regression.")

    print("\nPASS" if ok else "\nFAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
