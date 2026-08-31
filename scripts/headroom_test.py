#!/usr/bin/env python3
"""
Headroom test: does prompt optimization have anything to find here?

Screens N candidate prompts against a held-out case set, re-measures the
winner to strip out selection bias, and returns a go/no-go. If the winner's
confirmed gain is inside the noise floor, no known optimization method
reliably helps and prompt work should stop.

Two stages, because the winner of a one-run screen is biased upward: with 12
candidates the top single run is usually the luckiest one rather than the best
one, and the true winner often does not rank first at all. Stage 1 ranks
cheaply. Stage 2 re-measures the top few on fresh runs, and because that
measurement is independent of the screen that selected them, the confirmed
score is unbiased. The decision uses the confirmed score against a bar set by
the standard error of the difference, Bonferroni-corrected for how many
candidates were confirmed.

Against a simulated null case set where no candidate is genuinely better, the
single-stage version of this script reported HEADROOM FOUND in 6 of 12 runs.
This one reports it in 1 of 12. See scripts/test_headroom.py.

Usage:
    python headroom_test.py --cases cases.jsonl --candidates candidates.txt \
        [--runs 3] [--confirm 3] [--model claude-sonnet-5] [--threshold 2.0]

cases.jsonl      one JSON object per line: {"input": str, "expected": str}
candidates.txt   candidate prompts separated by a line containing only '---'

Scoring defaults to exact-match after normalization. Replace `score()` with
your real metric — the decision is only as good as the metric.
"""

import argparse, json, math, os, re, statistics, sys
from concurrent.futures import ThreadPoolExecutor

try:
    import anthropic
except ImportError:
    sys.exit("pip install anthropic")


def load_cases(path):
    cases = []
    with open(path) as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                sys.exit(f"{path}:{i} is not valid JSON")
            if "input" not in obj or "expected" not in obj:
                sys.exit(f"{path}:{i} needs both 'input' and 'expected'")
            cases.append(obj)
    if len(cases) < 10:
        print(f"WARNING: {len(cases)} cases. Under ~20 the noise floor will "
              f"swamp the signal and this test cannot decide.", file=sys.stderr)
    return cases


def load_candidates(path):
    with open(path) as f:
        chunks = [c.strip() for c in f.read().split("\n---\n")]
    return [c for c in chunks if c]


def normalize(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def score(output, expected):
    """Replace with your real metric. Exact match is a placeholder."""
    return 1.0 if normalize(output) == normalize(expected) else 0.0


def run_case(client, model, system, case):
    """Returns a score, or None if the call failed.

    None is not zero. A rate-limit or a network blip is missing data, and
    scoring it as a wrong answer biases whichever candidate happened to hit
    it — which is exactly the sub-2-point difference this script exists to
    measure. Failed calls are excluded from the mean and reported instead.
    """
    try:
        r = client.messages.create(
            model=model, max_tokens=1024,
            system=system if system else anthropic.NOT_GIVEN,
            messages=[{"role": "user", "content": case["input"]}],
        )
        text = "".join(b.text for b in r.content if b.type == "text")
        return score(text, case["expected"])
    except Exception as e:
        print(f"  case failed: {e}", file=sys.stderr)
        return None


def evaluate(client, model, system, cases, workers=8):
    """Returns (per_case, mean_over_scored, n_failed)."""
    with ThreadPoolExecutor(max_workers=workers) as ex:
        per_case = list(ex.map(lambda c: run_case(client, model, system, c), cases))
    scored = [s for s in per_case if s is not None]
    failed = len(per_case) - len(scored)
    if not scored:
        sys.exit("every call failed — check the API key, model ID, and network")
    return per_case, 100.0 * sum(scored) / len(scored), failed


def repeat(client, model, system, cases, runs, label):
    """Run the same prompt `runs` times. Returns (mean, spread, sd)."""
    means = []
    for i in range(runs):
        _, mean, failed = evaluate(client, model, system, cases)
        means.append(mean)
        note = f"  ({failed} calls failed, excluded)" if failed else ""
        print(f"  {label} run {i+1}: {mean:.1f}{note}")
    spread = (max(means) - min(means)) if len(means) > 1 else 0.0
    sd = statistics.stdev(means) if len(means) > 1 else 0.0
    return statistics.mean(means), spread, sd


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cases", required=True)
    p.add_argument("--candidates", required=True)
    p.add_argument("--model", default="claude-sonnet-5")
    p.add_argument("--runs", type=int, default=3,
                   help="repeats for the baseline and for the confirmation stage")
    p.add_argument("--confirm", type=int, default=3,
                   help="how many top screened candidates get confirmation runs")
    p.add_argument("--threshold", type=float, default=2.0,
                   help="minimum gain in points; overridden by measured noise floor if larger")
    args = p.parse_args()

    if args.runs < 2:
        sys.exit("--runs must be at least 2; a single run has no measurable spread")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("set ANTHROPIC_API_KEY")

    # max_retries handles 429s and 5xxs, so `None` below means a real failure.
    client = anthropic.Anthropic(max_retries=5)
    cases = load_cases(args.cases)
    candidates = load_candidates(args.candidates)
    print(f"{len(cases)} cases, {len(candidates)} candidates, model {args.model}\n")

    # Noise floor: repeat the zero-shot baseline and measure the spread.
    print(f"baseline x{args.runs} (measuring noise floor)")
    baseline, noise, base_sd = repeat(client, args.model, "", cases, args.runs, "baseline")
    print(f"  baseline {baseline:.1f}, spread {noise:.1f} pts, sd {base_sd:.1f}\n")

    # Stage 1 — screen. One run each; enough to rank, not enough to decide.
    print(f"stage 1: screening {len(candidates)} candidates (1 run each)")
    results = []
    for i, cand in enumerate(candidates, 1):
        per_case, mean, failed = evaluate(client, args.model, cand, cases)
        results.append({"i": i, "mean": mean, "per_case": per_case, "prompt": cand})
        note = f"  [{failed} failed]" if failed else ""
        print(f"  {i:>2}: {mean:5.1f}  ({mean - baseline:+.1f}){note}  {cand[:52]}...")

    results.sort(key=lambda r: -r["mean"])

    # Stage 2 — confirm. The screen's winner is the luckiest run as much as
    # the best prompt, and on a noisy case set the true winner is often not
    # ranked first. Re-measure the top few on fresh runs; the confirmed score
    # is independent of the screen that selected it, so it is unbiased.
    k = min(args.confirm, len(results))
    print(f"\nstage 2: confirming top {k} on fresh runs (x{args.runs} each)")
    for r in results[:k]:
        r["confirmed"], _, r["sd"] = repeat(
            client, args.model, r["prompt"], cases, args.runs, f"  #{r['i']}")

    confirmed_pool = sorted(results[:k], key=lambda r: -r["confirmed"])
    best = confirmed_pool[0]
    shrink = best["confirmed"] - best["mean"]
    gain = best["confirmed"] - baseline

    # Standard error of the difference between two means of `runs` samples.
    se = math.sqrt(base_sd ** 2 / args.runs + best["sd"] ** 2 / args.runs)
    # Bonferroni over the k candidates that got a confirmation run.
    alpha = 0.05 / k
    z = statistics.NormalDist().inv_cdf(1 - alpha / 2)
    bar = max(args.threshold, z * se)

    print("\n" + "=" * 66)
    print(f"baseline           {baseline:.1f}   (spread {noise:.1f}, sd {base_sd:.1f})")
    print(f"winner             #{best['i']}  screened {best['mean']:.1f}, "
          f"confirmed {best['confirmed']:.1f}  ({shrink:+.1f} on re-measure)")
    if confirmed_pool[0]["i"] != results[0]["i"]:
        print(f"                   screen ranked #{results[0]['i']} first; "
              f"confirmation overturned it")
    print(f"gain               {gain:+.1f} pts")
    print(f"decision bar       {bar:.1f} pts   (max of threshold {args.threshold}, "
          f"{z:.2f} x SE {se:.1f}; Bonferroni over {k})")
    print("=" * 66)

    if gain < bar:
        print("\nFLAT LANDSCAPE. Gain is inside the noise floor.")
        print("No known optimization method reliably helps here. The prompt is")
        print("not your bottleneck. Stop prompt work and look upstream:")
        print("  - is the right model selected?")
        print("  - does the eval set discriminate, or is difficulty dominating?")
        print("  - is the failure in retrieval, tools, or data rather than text?")
        return 1

    print(f"\nHEADROOM FOUND. Candidate #{best['i']} gains {gain:.1f} pts, confirmed.")
    print("Inspect what it does differently — the usual answer is that it")
    print("specifies an output format the model can produce but doesn't default")
    print("to. Target that structure, then proceed to authoring.\n")
    print(best["prompt"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
