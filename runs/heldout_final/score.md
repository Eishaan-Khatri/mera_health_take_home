# Score: heldout_final (labels: labels/, 3 repeats)

## Per report (mean over repeats)

| report | rate | rows | correct | critical | wrong_value | wrong_unit | wrong_range | invented_range | invented_row | unpaired | duplicate | miss_rows | dropped_row | null_value | missing_unit | missing_range | review | out_of_order | abnormal_rows | abnormal_critical | failed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 04 | 100.0% | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/3 |
| 07 | 100.0% | 10 | 10 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 4 | 0 | 0/3 |
| 10 | 100.0% | 9 | 9 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0/3 |
| 12 | n/a | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/3 |

## Headline (per repeat: mean, min, max)

- **Correct-row rate (pooled):** 1 (min 1, max 1)
- **Critical errors:** 0 (min 0, max 0)
- Critical errors on abnormal rows: 0 (min 0, max 0) (of 7 abnormal rows)
- Correct-row rate (mean of reports): 1 (min 1, max 1)
- Miss rows: 0 (min 0, max 0) | Review rows: 0 (min 0, max 0) | Failed reports: 0 (min 0, max 0)
  - wrong_value: 0 (min 0, max 0)
  - wrong_unit: 0 (min 0, max 0)
  - wrong_range: 0 (min 0, max 0)
  - invented_range: 0 (min 0, max 0)
  - invented_row: 0 (min 0, max 0)
  - dropped_row: 0 (min 0, max 0)
  - null_value: 0 (min 0, max 0)
  - missing_unit: 0 (min 0, max 0)
  - missing_range: 0 (min 0, max 0)

## Reliability (separate from accuracy)

- Report runs: 12 | runner attempts: 12 | runner retries: 0 | failed report runs: 0
- Errors seen by the runner: none
- Retries inside the extractor: 0 

## Cost and latency (per report)

- **$ per report:** mean $0.000874, max $0.001167 (12/12 runs with usage)
- $ per 10k reports/day: $8.74
- Tokens per report: prompt 1259 (min 1259, max 1259), output 372.5 (min 5, max 568), thinking n/a
- Latency of successful call: median 3.9s, max 8.1s; including retries: max 9.1s
