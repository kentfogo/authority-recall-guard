"""Measure fresh loads, cached restarts, first queries and warm local retrieval."""

import argparse
import asyncio
import math
import platform
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from time import perf_counter

from common import credentials, dataset, digest, read, versions, write
from moss import MossClient, QueryOptions


def elapsed(start):
    return 1000 * (perf_counter() - start)


def p95(values):
    return sorted(values)[math.ceil(0.95 * len(values)) - 1]


async def worker(job):
    data, manifest = dataset()
    options = QueryOptions(top_k=job["top_k"], alpha=job["alpha"])
    queries = data["cases"]
    hits = {case["id"]: {"pass": True, "worst_rank": 0} for case in queries}

    async with MossClient(*credentials()) as client:
        start = perf_counter()
        await client.load_index(manifest["index"], cache_path=job["cache"])
        load_ms = elapsed(start)

        async def query(case):
            start = perf_counter()
            result = await client.query(manifest["index"], case["query"], options)
            latency = elapsed(start)
            ids = [doc.id for doc in result.docs]
            record = hits[case["id"]]
            if case["expected"] in ids:
                record["worst_rank"] = max(
                    record["worst_rank"], 1 + ids.index(case["expected"])
                )
            else:
                record.update({"pass": False, "miss_ids": ids})
            return latency

        first_ms = await query(queries[job["trial"] % len(queries)])
        for case in queries:
            await query(
                case
            )  # Prime all fixture queries before measuring warm latency.
        warm_ms = []
        for _ in range(job["rounds"]):
            for case in queries:
                warm_ms.append(await query(case))
    write(
        job["result"],
        {
            "load_ms": load_ms,
            "first_query_ms": first_ms,
            "warm_ms": warm_ms,
            "cases": hits,
        },
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--environment", required=True, help="Stable host or deployment label"
    )
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--top-k", type=int, default=2)
    parser.add_argument("--alpha", type=float, default=0.8)
    args = parser.parse_args()
    if (
        not args.environment.strip()
        or min(args.trials, args.rounds, args.top_k) < 1
        or not 0 <= args.alpha <= 1
    ):
        parser.error(
            "Use a nonempty environment label, positive counts and alpha between 0 and 1."
        )
    if Path(args.output).exists():
        parser.error("Choose a fresh output path to preserve existing results.")
    data, manifest = dataset()
    cfg = {
        "environment": args.environment,
        "machine": platform.machine(),
        "os": platform.system(),
        "index": manifest["index"],
        "documents": manifest["documents"],
        "project": manifest["project"],
        "cases": digest(data["cases"]),
        "embedding_model": manifest["embedding_model"],
        "top_k": args.top_k,
        "alpha": args.alpha,
        "rounds": args.rounds,
        "trials": args.trials,
        "concurrency": 1,
    }
    samples = {"empty": [], "restart": []}
    for trial in range(args.trials):
        with tempfile.TemporaryDirectory(prefix="moss-eval-") as work:
            root = Path(work)
            cache = root / "index-cache"
            cache.mkdir()
            for phase, phase_samples in samples.items():
                result = root / (phase + ".json")
                job = {
                    "trial": trial,
                    "cache": str(cache),
                    "rounds": args.rounds,
                    "top_k": args.top_k,
                    "alpha": args.alpha,
                    "result": str(result),
                }
                write(root / "job.json", job)
                subprocess.run(
                    [sys.executable, __file__, "_worker", str(root / "job.json")],
                    check=True,
                    timeout=300,
                )
                phase_samples.append(read(result))
                if not any(p.is_file() and p.stat().st_size for p in cache.rglob("*")):
                    raise RuntimeError("The SDK did not populate the index cache.")
    groups = samples["empty"] + samples["restart"]
    warm = [ms for group in groups for ms in group["warm_ms"]]
    summary = {
        "empty_load_p50_ms": statistics.median(g["load_ms"] for g in samples["empty"]),
        "restart_load_p50_ms": statistics.median(
            g["load_ms"] for g in samples["restart"]
        ),
        "empty_first_query_p50_ms": statistics.median(
            g["first_query_ms"] for g in samples["empty"]
        ),
        "restart_first_query_p50_ms": statistics.median(
            g["first_query_ms"] for g in samples["restart"]
        ),
        "warm_query_p50_ms": statistics.median(warm),
        "warm_query_p95_ms": p95(warm),
        "warm_queries": len(warm),
    }
    passed = {
        case["id"]: all(g["cases"][case["id"]]["pass"] for g in groups)
        for case in data["cases"]
    }
    report = {
        "schema": 1,
        "config": cfg,
        "versions": versions(),
        "metrics": summary,
        "case_pass": passed,
        "trials": samples,
    }
    write(args.output, report)
    print(
        f"warm p95 {summary['warm_query_p95_ms']:.2f} ms across {len(warm)} queries, "
        f"{sum(passed.values())}/{len(passed)} cases passed"
    )
    return 0 if all(passed.values()) else 1


if __name__ == "__main__":
    if sys.argv[1:2] == ["_worker"]:
        asyncio.run(worker(read(sys.argv[2])))
    else:
        sys.exit(main())
