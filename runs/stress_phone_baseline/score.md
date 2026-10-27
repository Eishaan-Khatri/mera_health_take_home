# Score: stress_phone_baseline (labels: labels/, 3 repeats)

## Per report (mean over repeats)

| report | rate | rows | correct | critical | wrong_value | wrong_unit | wrong_range | invented_range | invented_row | unpaired | duplicate | miss_rows | dropped_row | null_value | missing_unit | missing_range | review | out_of_order | abnormal_rows | abnormal_critical | failed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | 100.0% | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0/3 |
| 02 | 87.5% | 16 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 2 | 0 | 6 | 0 | 0/3 |
| 03 | 62.5% | 8 | 5 | 3 | 0 | 0 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/3 |
| 05 | 100.0% | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0/3 |
| 06 | 8.3% | 12 | 1 | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 5 | 0 | 0 | 2 | 0 | 3 | 1 | 0/3 |
| 08 | 83.3% | 6 | 5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0/3 |
| 09 | 100.0% | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0/3 |
| 11 | 51.9% | 54 | 28 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 | 24 | 0 | 0 | 0 | 2 | 0 | 9 | 0 | 0/3 |

## Headline (per repeat: mean, min, max)

- **Correct-row rate (pooled):** 0.6884 (min 0.6884, max 0.6884)
- **Critical errors:** 7 (min 7, max 7)
- Critical errors on abnormal rows: 1 (min 1, max 1) (of 29 abnormal rows)
- Correct-row rate (mean of reports): 0.7419 (min 0.7419, max 0.7419)
- Miss rows: 29 (min 29, max 29) | Review rows: 7 (min 7, max 7) | Failed reports: 0 (min 0, max 0)
  - wrong_value: 4 (min 4, max 4)
  - wrong_unit: 0 (min 0, max 0)
  - wrong_range: 0 (min 0, max 0)
  - invented_range: 3 (min 3, max 3)
  - invented_row: 0 (min 0, max 0)
  - dropped_row: 24 (min 24, max 24)
  - null_value: 5 (min 5, max 5)
  - missing_unit: 0 (min 0, max 0)
  - missing_range: 0 (min 0, max 0)

## Reliability (separate from accuracy)

- Report runs: 24 | runner attempts: 24 | runner retries: 0 | failed report runs: 0
- Errors seen by the runner: none
- Retries inside the extractor: 0 

## Cost and latency (per report)

- **$ per report:** mean $0.001685, max $0.003161 (24/24 runs with usage)
- $ per 10k reports/day: $16.85
- Tokens per report: prompt 1235 (min 1214, max 1242), output 917.2 (min 376, max 1900), thinking n/a
- Latency of successful call: median 6.2s, max 13.4s; including retries: max 13.4s

## Needs review (repeat 1)

- report_02: ['review_unit_added'] label='TC/HDL Ratio' pred='TC/HDL Ratio'
- report_02: ['review_unit_added'] label='Albumin/Globulin Ratio' pred='Albumin/Globulin Ratio'
- report_06: ['review_unit_added'] label='pH' pred='Urine pH'
- report_06: ['review_unit_added'] label='Specific Gravity' pred='Urine Specific Gravity'
- report_08: ['review_unit_added'] label='Chol/HDL' pred='Cholesterol/HDL Ratio'
- report_11: ['review_unit_added'] label='TC/HDL Ratio' pred='TC/HDL Ratio'
- report_11: ['review_unit_added'] label='Albumin/Globulin Ratio' pred='Albumin/Globulin Ratio'
