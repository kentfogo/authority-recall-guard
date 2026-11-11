"""Test hosted inference alone or with a fixture index, and time the streamed reply."""

import argparse
import asyncio
import sys
from pathlib import Path
from time import perf_counter

from common import credentials, dataset, versions, write
from moss import MossInference
from moss.inference import InferenceError


def normalize(s):
    return " ".join(s.casefold().split()).strip().rstrip(".!?")


async def run(output, plain, model):
    if plain:
        index = None
        answer_cases = [
            {
                "id": "plain",
                "query": "Reply with the single word Ready.",
                "exact": "Ready",
            }
        ]
        instructions = "Follow the user's instructions precisely."
    else:
        data, manifest = dataset()
        index = manifest["index"]
        answer_cases = data["answer_cases"]
        instructions = "Answer using the supplied knowledge. If the answer is absent, reply only Unknown."
    client = MossInference(*credentials(), timeout=60, idle_timeout=20, max_retries=0)
    cases = []
    try:
        for case in answer_cases:
            start = perf_counter()
            first = None
            text = ""
            terminal = None
            row = {"id": case["id"], "pass": False}
            try:
                stream = await client.responses.create(
                    model=model,
                    indexes=[index] if index else None,
                    input=case["query"],
                    instructions=instructions,
                    cache=False,
                    stream=True,
                )
                async with stream:
                    async for event in stream:
                        if event.type == "response.output_text.delta" and event.delta:
                            if first is None:
                                first = 1000 * (perf_counter() - start)
                            text += event.delta
                        if event.type in (
                            "response.completed",
                            "response.failed",
                            "response.incomplete",
                        ):
                            terminal = event.type
                matched = (
                    normalize(text) == normalize(case["exact"])
                    if "exact" in case
                    else normalize(case["must_contain"]) in normalize(text)
                )
                row["pass"] = (
                    first is not None and terminal == "response.completed" and matched
                )
            except InferenceError as err:
                row["error_type"] = type(err).__name__
                for name in ("status", "code", "request_id"):
                    value = getattr(err, name, None)
                    if value is not None:
                        row[name] = value
            row.update(
                {
                    "ttft_ms": first,
                    "total_ms": 1000 * (perf_counter() - start),
                    "terminal_event": terminal,
                    "text": text,
                }
            )
            cases.append(row)
            print(case["id"], "PASS" if row["pass"] else "FAIL")
    finally:
        await client.close()
    if not cases:
        raise ValueError("Provide at least one answer case.")
    write(
        output,
        {
            "schema": 1,
            "model": model,
            "index": index,
            "mode": "plain" if plain else "grounded",
            "versions": versions(),
            "cases": cases,
        },
    )
    return 0 if all(c["pass"] for c in cases) else 1


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", required=True)
    p.add_argument(
        "--plain",
        action="store_true",
        help="Run one inference request without seeding or searching an index.",
    )
    p.add_argument(
        "--model",
        default="moss/fastlane-1",
        help="Model ID enabled for your Moss project",
    )
    args = p.parse_args()
    if Path(args.output).exists():
        p.error("Choose a fresh output path.")
    sys.exit(asyncio.run(run(args.output, args.plain, args.model)))
