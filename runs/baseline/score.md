# Score: baseline (labels: labels/, 3 repeats)

## Per report (mean over repeats)

| report | rate | rows | correct | critical | wrong_value | wrong_unit | wrong_range | invented_range | invented_row | unpaired | duplicate | miss_rows | dropped_row | null_value | missing_unit | missing_range | review | out_of_order | abnormal_rows | abnormal_critical | failed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 01 | 78.6% | 14 | 11 | 3 | 0 | 0 | 0 | 0 | 3 | 3 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0/3 |
| 02 | 81.2% | 16 | 13 | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 2 | 0 | 6 | 0 | 0/3 |
| 03 | 37.5% | 8 | 3 | 5 | 0 | 0 | 0 | 3 | 2 | 2 | 0 | 2 | 2 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0/3 |
| 05 | 78.6% | 14 | 11 | 3 | 0 | 0 | 0 | 0 | 3 | 3 | 0 | 3 | 3 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0/3 |
| 06 | 0.0% | 12 | 0 | 7 | 2 | 0 | 0 | 0 | 5 | 5 | 0 | 5 | 5 | 1 | 0 | 0 | 5 | 0 | 3 | 1 | 0/3 |
| 08 | 66.7% | 6 | 4 | 1 | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 1 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 0 | 0/3 |
| 09 | 100.0% | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 3 | 0 | 0/3 |
| 11 | 55.6% | 54 | 30 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 24 | 24 | 0 | 0 | 0 | 0 | 0 | 9 | 0 | 0/3 |

## Headline (per repeat: mean, min, max)

- **Correct-row rate (pooled):** 0.6232 (min 0.6232, max 0.6232)
- **Critical errors:** 20 (min 20, max 20)
- Critical errors on abnormal rows: 1 (min 1, max 1) (of 29 abnormal rows)
- Correct-row rate (mean of reports): 0.6226 (min 0.6226, max 0.6226)
- Miss rows: 39 (min 39, max 39) | Review rows: 8 (min 8, max 8) | Failed reports: 0 (min 0, max 0)
  - wrong_value: 2 (min 2, max 2)
  - wrong_unit: 0 (min 0, max 0)
  - wrong_range: 0 (min 0, max 0)
  - invented_range: 3 (min 3, max 3)
  - invented_row: 15 (min 15, max 15)
  - dropped_row: 39 (min 39, max 39)
  - null_value: 1 (min 1, max 1)
  - missing_unit: 0 (min 0, max 0)
  - missing_range: 0 (min 0, max 0)

## Reliability (separate from accuracy)

- Report runs: 24 | API attempts: 25 | retries: 1 | failed report runs: 0
- Errors by type: {'http_5xx': 1}

## Cost and latency (per report)

- **$ per report:** mean $0.001613, max $0.002529 (24/24 runs with usage)
- $ per 10k reports/day: $16.12
- Tokens per report: prompt 1242 (min 1242, max 1242), output 868 (min 376, max 1479), thinking n/a
- Latency of successful call: median 5.8s, max 72.5s; including retries: max 72.5s

## Needs review (repeat 1)

- report_02: ['review_fuzzy'] label='Aspartate Aminotransferase' pred='Aspartate Aminotransferase (AST)'
- report_02: ['review_fuzzy'] label='Alanine Aminotransferase' pred='Alanine Aminotransferase (ALT)'
- report_06: ['null_value', 'review_unit_added'] label='Colour' pred='Urine Colour'
- report_06: ['review_unit_added'] label='pH' pred='Urine pH'
- report_06: ['review_fuzzy', 'review_unit_added'] label='Specific Gravity' pred='Urine Specific Gravity'
- report_06: ['review_fuzzy', 'wrong_value', 'review_range_format'] label='Erythrocytes' pred='Urine Erythrocytes'
- report_06: ['review_fuzzy', 'wrong_value'] label='Squamous Epithelial Cells' pred='Urine Squamous Epithelial Cells'
- report_08: ['review_unit_added'] label='Chol/HDL' pred='Cholesterol/HDL Ratio'
