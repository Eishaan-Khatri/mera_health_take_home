# Score: stress_jpeg_baseline (labels: labels/, 3 repeats)

## Per report (mean over repeats)

| report | rate | rows | correct | critical | wrong_value | wrong_unit | wrong_range | invented_range | invented_row | unpaired | duplicate | miss_rows | dropped_row | null_value | missing_unit | missing_range | review | out_of_order | abnormal_rows | abnormal_critical | failed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | 100.0% | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0/3 |
| 02 | 87.5% | 16 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 6 | 0 | 0/3 |
| 03 | 62.5% | 8 | 5 | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/3 |
| 05 | 100.0% | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0/3 |
| 06 | 8.3% | 12 | 1 | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | 0 | 2 | 0 | 3 | 2 | 0/3 |
| 08 | 83.3% | 6 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0/3 |
| 09 | 100.0% | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0/3 |
| 11 | 55.6% | 54 | 30 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 | 24 | 0 | 0 | 0 | 0 | 0 | 9 | 0 | 0/3 |

## Headline (per repeat: mean, min, max)

- **Correct-row rate (pooled):** 0.7029 (min 0.7029, max 0.7029)
- **Critical errors:** 10 (min 10, max 10)
- Critical errors on abnormal rows: 2 (min 2, max 2) (of 29 abnormal rows)
- Correct-row rate (mean of reports): 0.7465 (min 0.7465, max 0.7465)
- Miss rows: 26 (min 26, max 26) | Review rows: 5 (min 5, max 5) | Failed reports: 0 (min 0, max 0)
  - wrong_value: 7 (min 7, max 7)
  - wrong_unit: 0 (min 0, max 0)
  - wrong_range: 0 (min 0, max 0)
  - invented_range: 3 (min 3, max 3)
  - invented_row: 0 (min 0, max 0)
  - dropped_row: 24 (min 24, max 24)
  - null_value: 2 (min 2, max 2)
  - missing_unit: 0 (min 0, max 0)
  - missing_range: 0 (min 0, max 0)

## Reliability (separate from accuracy)

- Report runs: 24 | runner attempts: 25 | runner retries: 1 | failed report runs: 0
- Errors seen by the runner: {'http_5xx': 1}
- Retries inside the extractor: 0 

## Cost and latency (per report)

- **$ per report:** mean $0.001610, max $0.002529 (24/24 runs with usage)
- $ per 10k reports/day: $16.10
- Tokens per report: prompt 1242 (min 1242, max 1242), output 866.2 (min 376, max 1479), thinking n/a
- Latency of successful call: median 5.9s, max 21.0s; including retries: max 21.0s

## Needs review (repeat 1)

- report_02: ['review_unit_added'] label='TC/HDL Ratio' pred='TC/HDL Ratio'
- report_02: ['review_unit_added'] label='Albumin/Globulin Ratio' pred='Albumin/Globulin Ratio'
- report_06: ['review_unit_added'] label='pH' pred='Urine pH'
- report_06: ['review_unit_added'] label='Specific Gravity' pred='Urine Specific Gravity'
- report_08: ['review_unit_added'] label='Chol/HDL' pred='Cholesterol/HDL Ratio'
