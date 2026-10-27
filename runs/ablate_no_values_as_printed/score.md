# Score: ablate_no_values_as_printed (labels: labels/, 3 repeats)

## Per report (mean over repeats)

| report | rate | rows | correct | critical | wrong_value | wrong_unit | wrong_range | invented_range | invented_row | unpaired | duplicate | miss_rows | dropped_row | null_value | missing_unit | missing_range | review | out_of_order | abnormal_rows | abnormal_critical | failed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | 100.0% | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0/3 |
| 02 | 100.0% | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 0 | 0/3 |
| 03 | 100.0% | 8 | 8 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/3 |
| 05 | 100.0% | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0/3 |
| 06 | 25.0% | 12 | 3 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 5 | 0 | 3 | 1 | 0/3 |
| 08 | 100.0% | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/3 |
| 09 | 100.0% | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0/3 |
| 11 | 85.2% | 54 | 46 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 6 | 6 | 0 | 0 | 0 | 0 | 0 | 9 | 1 | 0/3 |

## Headline (per repeat: mean, min, max)

- **Correct-row rate (pooled):** 0.8768 (min 0.8768, max 0.8768)
- **Critical errors:** 6 (min 6, max 6)
- Critical errors on abnormal rows: 2 (min 2, max 2) (of 29 abnormal rows)
- Correct-row rate (mean of reports): 0.8877 (min 0.8877, max 0.8877)
- Miss rows: 6 (min 6, max 6) | Review rows: 5 (min 5, max 5) | Failed reports: 0 (min 0, max 0)
  - wrong_value: 6 (min 6, max 6)
  - wrong_unit: 0 (min 0, max 0)
  - wrong_range: 0 (min 0, max 0)
  - invented_range: 0 (min 0, max 0)
  - invented_row: 0 (min 0, max 0)
  - dropped_row: 6 (min 6, max 6)
  - null_value: 5 (min 5, max 5)
  - missing_unit: 0 (min 0, max 0)
  - missing_range: 0 (min 0, max 0)

## Reliability (separate from accuracy)

- Report runs: 24 | runner attempts: 24 | runner retries: 0 | failed report runs: 0
- Errors seen by the runner: none
- Retries inside the extractor: 13 {'http_503': 13}

## Cost and latency (per report)

- **$ per report:** mean $0.001614, max $0.003747 (24/24 runs with usage)
- $ per 10k reports/day: $16.14
- Tokens per report: prompt 1360 (min 1223, max 2315), output 849.2 (min 324, max 2112), thinking n/a
- Latency of successful call: median 11.3s, max 87.5s; including retries: max 87.5s

## Needs review (repeat 1)

- report_06: ['null_value', 'review_unit_added'] label='Colour' pred='Urine Colour'
- report_06: ['null_value', 'review_unit_added'] label='Clarity' pred='Urine Clarity'
- report_06: ['null_value', 'review_unit_added'] label='Albumin' pred='Urine Albumin'
- report_06: ['null_value', 'review_unit_added'] label='Sugar' pred='Urine Sugar'
- report_06: ['null_value', 'review_unit_added'] label='Ketones' pred='Urine Ketones'
