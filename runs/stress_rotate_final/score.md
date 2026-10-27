# Score: stress_rotate_final (labels: labels/, 3 repeats)

## Per report (mean over repeats)

| report | rate | rows | correct | critical | wrong_value | wrong_unit | wrong_range | invented_range | invented_row | unpaired | duplicate | miss_rows | dropped_row | null_value | missing_unit | missing_range | review | out_of_order | abnormal_rows | abnormal_critical | failed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | 100.0% | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0/3 |
| 02 | 100.0% | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0/3 |
| 03 | 100.0% | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/3 |
| 05 | 100.0% | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0/3 |
| 06 | 100.0% | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0/3 |
| 08 | 100.0% | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/3 |
| 09 | 100.0% | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0/3 |
| 11 | 98.1% | 54 | 53 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 9 | 0 | 0/3 |

## Headline (per repeat: mean, min, max)

- **Correct-row rate (pooled):** 0.9928 (min 0.9928, max 0.9928)
- **Critical errors:** 0 (min 0, max 0)
- Critical errors on abnormal rows: 0 (min 0, max 0) (of 29 abnormal rows)
- Correct-row rate (mean of reports): 0.9977 (min 0.9977, max 0.9977)
- Miss rows: 0 (min 0, max 0) | Review rows: 1 (min 1, max 1) | Failed reports: 0 (min 0, max 0)
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

- Report runs: 24 | runner attempts: 24 | runner retries: 0 | failed report runs: 0
- Errors seen by the runner: none
- Retries inside the extractor: 0 

## Cost and latency (per report)

- **$ per report:** mean $0.001613, max $0.003965 (24/24 runs with usage)
- $ per 10k reports/day: $16.13
- Tokens per report: prompt 1374 (min 1231, max 2295), output 846.8 (min 317, max 2261), thinking n/a
- Latency of successful call: median 7.7s, max 24.6s; including retries: max 24.6s

## Needs review (repeat 1)

- report_11: ['review_fuzzy'] label='Cyanocobalamin (B12)' pred='Cynocobalamin (B12)'
