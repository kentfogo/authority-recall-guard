# Moss Inference eval kit

Open **testing.html** in your browser for setup, commands, pass conditions and troubleshooting. Run commands from this folder. Start with `python inference.py --plain --output first-stream.json` once your project and SDK are configured. Python 3.10 or later is required. The Python scripts use the Moss SDK pinned in requirements.txt.

- `fixture.json` contains six fictional documents, four labeled retrieval queries and two answer cases.
- `seed.py` creates one uniquely named index in your test project.
- `evaluate.py` measures empty-cache and populated-cache loads in fresh processes, first queries and warm retrieval. It produces a JSON report with per-case results.
- `compare.py` compares two retrieval reports and returns a nonzero exit status on a regression or invalid comparison.
- `inference.py` checks a plain stream with `--plain`, or grounded answers against the fixture. Both report time to first text and total latency.

The sample commands run against your Moss project and may incur usage. Use a staging project. The index remains available for comparisons until you remove it in your project. The kit removes only its temporary benchmark directories.

For the engineering release procedure and scope of validation see **RELEASE.md**.


[Moss Inference overview](https://docs.moss.dev/docs/inference/overview)
