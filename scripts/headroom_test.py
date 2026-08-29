#!/usr/bin/env python3
"""
Headroom test: does prompt optimization have anything to find here?

Runs N candidate prompts plus a zero-shot baseline against a held-out case
set, reports the best gain against the measured noise floor, and returns a
go/no-go. If the best candidate's gain is inside the noise floor, no known
optimization method reliably helps and prompt work should stop.

Usage:
    python headroom_test.py --cases cases.jsonl --candidates candidates.txt \
        [--baseline-runs 3] [--model claude-sonnet-4-6] [--threshold 2.0]

cases.jsonl      one JSON object per line: {"input": str, "expected": str}
candidates.txt   candidate prompts separated by a line containing only '---'

Scoring defaults to exact-match after normalization. Replace `score()` with
your real metric — the decision is only as good as the metric.
"""

import argparse, json, os, re, statistics, sys
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
        return 0.0


def evaluate(client, model, system, cases, workers=8):
    with ThreadPoolExecutor(max_workers=workers) as ex:
        per_case = list(ex.map(lambda c: run_case(client, model, system, c), cases))
    return per_case, 100.0 * sum(per_case) / len(per_case)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cases", required=True)
    p.add_argument("--candidates", required=True)
    p.add_argument("--model", default="claude-sonnet-4-6")
    p.add_argument("--baseline-runs", type=int, default=3)
    p.add_argument("--threshold", type=float, default=2.0,
                   help="minimum gain in points; overridden by measured noise floor if larger")
    args = p.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("set ANTHROPIC_API_KEY")

    client = anthropic.Anthropic()
    cases = load_cases(args.cases)
    candidates = load_candidates(args.candidates)
    print(f"{len(cases)} cases, {len(candidates)} candidates, model {args.model}\n")

    # Noise floor: repeat the zero-shot baseline and measure the spread.
    print(f"baseline x{args.baseline_runs} (measuring noise floor)")
    baselines = []
    for i in range(args.baseline_runs):
        _, mean = evaluate(client, args.model, "", cases)
        baselines.append(mean)
        print(f"  run {i+1}: {mean:.1f}")
    baseline = statistics.mean(baselines)
    noise = (max(baselines) - min(baselines)) if len(baselines) > 1 else 0.0
    print(f"  baseline {baseline:.1f}, noise floor {noise:.1f} pts\n")

    print("candidates")
    results = []
    for i, cand in enumerate(candidates, 1):
        per_case, mean = evaluate(client, args.model, cand, cases)
        results.append({"i": i, "mean": mean, "per_case": per_case, "prompt": cand})
        print(f"  {i:>2}: {mean:5.1f}  ({mean - baseline:+.1f})  {cand[:58]}...")

    results.sort(key=lambda r: -r["mean"])
    best = results[0]
    gain = best["mean"] - baseline
    bar = max(args.threshold, noise)

    print("\n" + "=" * 62)
    print(f"baseline        {baseline:.1f}")
    print(f"best candidate  {best['mean']:.1f}  (#{best['i']})")
    print(f"gain            {gain:+.1f} pts")
    print(f"decision bar    {bar:.1f} pts  (max of threshold {args.threshold}, noise {noise:.1f})")
    print("=" * 62)

    if gain < bar:
        print("\nFLAT LANDSCAPE. Gain is inside the noise floor.")
        print("No known optimization method reliably helps here. The prompt is")
        print("not your bottleneck. Stop prompt work and look upstream:")
        print("  - is the right model selected?")
        print("  - does the eval set discriminate, or is difficulty dominating?")
        print("  - is the failure in retrieval, tools, or data rather than text?")
        return 1

    print(f"\nHEADROOM FOUND. Candidate #{best['i']} gains {gain:.1f} pts.")
    print("Inspect what it does differently — the usual answer is that it")
    print("specifies an output format the model can produce but doesn't default")
    print("to. Target that structure, then proceed to authoring.\n")
    print(best["prompt"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
