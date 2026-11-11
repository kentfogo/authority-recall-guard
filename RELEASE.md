# Engineering release handoff

This is the proposed maintenance procedure for the customer kit. The release owner should attach evidence from a live staging run before marking an SDK version supported.

| Item | Initial package |
| --- | --- |
| Retrieval client | Python moss 1.23.0 |
| Native core | inferedge-moss-core 0.36.0 |
| API reviewed | Moss Inference Responses, model moss/fastlane-1 |
| Scope | Local Python retrieval, streamed hosted inference, manual LiveKit and Pipecat call checks |
| Live staging status | Requires a customer or engineering test project |

Local verification used the pinned SDK, simulated retrieval and a mocked HTTP stream. It exercised the benchmark worker lifecycle, expected document misses, latency regressions, and wrong or incomplete inference responses. Live project and voice call acceptance remains an engineering release step.

1. Run the current release against a fixed fixture and keep the passing report. Record the host, worker image, Python runtime, framework versions, index revision and load. Store the dependency lock and the report alongside the release.
2. Install the candidate Moss SDK and matching native core in a separate environment. Update pins and snippets together. Verify the documented signatures for create_index, load_index, query and responses.create.
3. Reuse the manifest and index on the same host. Run both release environments against the same cases, query settings, cache protocol and concurrency. Run compare.py with the team's thresholds and inspect individual misses. A return code of 1 flags a regression. A return code of 2 indicates an invalid comparison.
4. Run inference.py --plain on each release before seeding an index, then run inference.py against the seeded fixture. Inspect the supported answer, the unsupported answer, stream termination, and per-case timing. Use representative prompts and more samples for latency targets.
5. Rehearse the customer's deployed voice integration, including a follow-up, interruption, timeout and second room. Save the framework and plug-in versions, traces, first-audio measurements and observed behavior.
6. Record the released versions, test date, environment, report paths, reviewer and known limitations in the changelog. Keep historical baselines when accepting an intentional change. Publish the kit and update its link from the onboarding guide once engineering has reviewed the staging results.

## Release record

| SDK and core | Framework and plug-in | Date and environment | Baseline and candidate reports | Reviewer and outcome |
| --- | --- | --- | --- | --- |
| Fill at release | Fill at release | Fill at release | Attach JSON and voice traces | Record pass or known limitation |


API behavior and model routing are described in the [Moss Inference overview](https://docs.moss.dev/docs/inference/overview).
