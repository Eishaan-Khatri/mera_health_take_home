# Score: stress_low_res_dpi150 (labels: labels/, 3 repeats)

## Per report (mean over repeats)

| report | rate | rows | correct | critical | wrong_value | wrong_unit | wrong_range | invented_range | invented_row | unpaired | duplicate | miss_rows | dropped_row | null_value | missing_unit | missing_range | review | out_of_order | abnormal_rows | abnormal_critical | failed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | 100.0% | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0/3 |
| 02 | 100.0% | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0/3 |
| 03 | 100.0% | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/3 |
| 05 | 100.0% | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0/3 |
| 06 | 100.0% | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0/3 |
| 11 | 94.4% | 54 | 51 | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 9 | 1 | 0/3 |

## Headline (per repeat: mean, min, max)

- **Correct-row rate (pooled):** 0.9746 (min 0.9746, max 0.9746)
- **Critical errors:** 3 (min 3, max 3)
- Critical errors on abnormal rows: 1 (min 1, max 1) (of 26 abnormal rows)
- Correct-row rate (mean of reports): 0.9907 (min 0.9907, max 0.9907)
- Miss rows: 0 (min 0, max 0) | Review rows: 0 (min 0, max 0) | Failed reports: 0 (min 0, max 0)
  - wrong_value: 2 (min 2, max 2)
  - wrong_unit: 0 (min 0, max 0)
  - wrong_range: 1 (min 1, max 1)
  - invented_range: 0 (min 0, max 0)
  - invented_row: 0 (min 0, max 0)
  - dropped_row: 0 (min 0, max 0)
  - null_value: 0 (min 0, max 0)
  - missing_unit: 0 (min 0, max 0)
  - missing_range: 0 (min 0, max 0)

## Reliability (separate from accuracy)

- Report runs: 18 | runner attempts: 18 | runner retries: 0 | failed report runs: 0
- Errors seen by the runner: none
- Retries inside the extractor: 2 {'http_503': 2}

## Cost and latency (per report)

- **$ per report:** mean $0.001720, max $0.003906 (18/18 runs with usage)
- $ per 10k reports/day: $17.20
- Tokens per report: prompt 1441 (min 1259, max 2351), output 906.3 (min 427, max 2212), thinking n/a
- Latency of successful call: median 10.5s, max 56.2s; including retries: max 56.2s
