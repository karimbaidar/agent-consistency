# False-Success Benchmark Results

Headline: **raw caught 0/6; agent-consistency caught 6/6**.

These numbers describe the deterministic scenarios in this repository. They are not a universal claim about every possible agent workflow.

## Cases

| Case | Category | Raw caught? | agent-consistency caught? | Protected receipt status |
| --- | --- | --- | --- | --- |
| `pending_refund_not_settled` | `outcome_verification` | no | yes | failed |
| `stale_policy_snapshot` | `state_freshness` | no | yes | failed |
| `dropped_handoff_fact` | `handoff_contract` | no | yes | failed |
| `partial_write_claim` | `outcome_verification` | no | yes | failed |
| `wrong_entity_action` | `outcome_verification` | no | yes | failed |
| `swallowed_tool_error` | `outcome_verification` | no | yes | failed |

## Category Catch Rate

| Category | agent-consistency caught |
| --- | --- |
| `handoff_contract` | 1/1 |
| `outcome_verification` | 4/4 |
| `state_freshness` | 1/1 |

## Reproduce

```bash
python -m benchmark.run --write-results benchmark/results.md
```
