# False-Success Benchmark Leaderboard

Run the deterministic benchmark on your framework or adapter and submit results
with the schema below.

Current reference result:

| Runner | Mode | Cases | Raw caught | Protected caught | Command |
| --- | --- | ---: | ---: | ---: | --- |
| agent-consistency | local deterministic | 6 | 0 | 6 | `python -m benchmark.run --write-results benchmark/results.md` |

## Submission Schema

Add one row with:

- runner or framework name
- execution mode, such as local deterministic or hosted fake-provider
- number of benchmark cases run
- raw false-success cases caught
- protected false-success cases caught
- command used to reproduce
- link to generated results

Submissions must be deterministic and must not require live provider calls.

