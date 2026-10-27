# Lab report extraction: make it better, and prove it

**Setup changes from the kit:**
- Default model **`gemini-3.1-flash-lite`**, the cheapest priced Gemini (the kit's 3.8 Flash returned 503s). `GEMINI_MODEL` overrides it.
- Requirements: Poppler and `GEMINI_API_KEY` (`eval.py run` also reads it from a local `.env`). Pillow only for `experiments/`.
- On failure, `extract.py` prints `{"tests": [], "error": "..."}` and exits 1.

```bash
python extract.py reports/report_01.pdf
python eval.py run --extractor extract.py --tag NAME   # 8 tuning reports x 3: score, cost, latency
python eval.py diff runs/baseline runs/fix7_timeouts_error_json
python test_eval.py                                    # 67 tests of the eval itself
```

Eval output: [baseline](runs/baseline/score.md) and [final](runs/fix7_timeouts_error_json/score.md).

## Results (8 tuning reports, 138 rows, 3 identical repeats)

| | Correct rows | Critical | $ / report | Median latency |
|---|---|---|---|---|
| Baseline (same model) | 71.7% | 10 | $0.00161 | 5.8 s |
| **Final** | **100%** | **0** | **$0.00153** | 10.8 s |
| Final, held-out 04/07/10/12 (28 rows, one shot) | 100% | 0 | $0.00087 | 3.9 s |
| Final / baseline, 5 degraded copies | 98.6–100% / 68.8–72.5% | 0–2 / 7–10 | | |

**Latency** tracked Google's load: 503s went from 1 to 14–25 per run, while output tokens didn't grow and there were no thinking tokens.

**At 10,000 reports a day:** about $15 at list price, on the paid tier (the free tier allows 500 requests a day).

## 2. Eval ([`eval.py`](eval.py))

**Pairing:** rows are paired by **test name, never by value**, via [`eval_vocab.json`](eval_vocab.json). Blood and urine tests are never paired.

**Tiers:**
- 🔴 **Critical:** wrong value, wrong unit (incl. `lakh` vs `/cumm`), wrong range, invented range, or invented row.
- ⚠️ **Miss:** dropped row or empty field.
- **Review:** ambiguous, so never counted as correct.

**Not counted:** formatting like `2,29,000`, or a unit printed in the range cell.

**Reported:** correct-row rate and critical errors, with abnormal rows and failed reports separately. Retries are reported apart from accuracy.

**Testing the eval:** its tests break labels one way at a time and check that exactly the right counter moves.

**Labels** ([`labels/NOTES.md`](labels/NOTES.md)): `gold/` is untouched. In `labels/` I corrected one row (report_01 Platelets `304000` → `340000`) and hand-labelled the held-out reports.

**Baseline:** 62.3% with my first eval, and **71.7%** once its name matching was fixed. That fix came before any extractor change.

## 3. Diagnosis, ranked by harm

| # | Example | Root cause |
|---|---|---|
| 1 | 06 Sugar `Present (+)` → `1.0`; CRP `< 0.5` → `0.5` | Prompt: `value must be a number.`, plus `to_number()` |
| 2 | 03 Glycated Hb: no range printed → `4.0 - 5.6`, flagged high | Prompt: `fill in the standard reference range` |
| 3 | 11: all 24 page-2 rows missing, incl. Urea `42` (high) | `pdftoppm -f 1 -l 1 -singlefile` |

#3 ranks near the top because it's **silent**: the output looks complete.

**PLAN.md hypotheses:**
- Held: page 1 only, numeric coercion, invented ranges.
- Didn't hold: 60 DPI misreads, Indian digit grouping, two-column layouts, "correcting" values that don't add up.

## 4. Fixes

| Fix (1–5: one commit and run each; 6 and 7 batched) | Correct | Critical | Fixed / broken | $ / report · median s |
|---|---|---|---|---|
| 1. Send every page | 83.3% | 12 (page 2 now hits #1) | 16 / 0 | $0.00182 · 14.9 |
| 2. Value as printed | 95.7% | 3 | 17 / 0 | $0.00183 · 34.8 |
| 3. Range as printed or null | **100%** | **0** | 6 / 0 | $0.00182 · 13.7 |
| 4–6. Status from code: numbers, intervals, then word ranges (`review`) | 100% | 0 | bad statuses per run 8 → 0* | $0.00153 · 10–13 |
| 7. Retries in `extract.py`, error JSON, 90 s / 300 s cap | 100% | 0 | — | $0.00153 · 10.8 |

\* Status is checked against the final rule by `experiments/status_check.py`. Fixes 4–5 alone left some rows null, not guessed.

**Ablation:** on the final code, I removed one fix at a time.
- Pages off: 82.6%.
- Values off: 87.7% (6 critical).
- Range rule off: 97.8% (3 critical).
- Status off: 100% rows, but 8 bad statuses per run.

**Stress set** ([`experiments/`](experiments)): only digit misreads remain, e.g. report_11 Eosinophils `0` (abnormal) read as `8` from a very low-resolution copy.

## 5. What didn't help

**150 DPI:** 98.98% vs **99.49%** at 60 DPI on degraded PDFs, with identical input tokens (the API resizes images). The Eosinophils misread happened at both DPIs.

## 6. Three answers

**Would RAG help? No.** Each report stands on its own: every value comes with its unit and reference range printed on the same page, and nothing in one report should change how another is read. Retrieval would only help if we needed outside reference information. The main thing it would bring in, "standard" reference ranges, is exactly what fix 3 removed, because a doctor would read them as the lab's.

**Would fine-tuning help? No.** There is no fixed set of report formats to train on: layouts vary as widely as the labs that produce them. Fine-tuning on a narrow subset risks overfitting to those layouts and doing worse on labs it hasn't seen. It would also cost far more than prompting (labelled data, training, and retraining as formats change), while every improvement we needed came from the prompt and code: 71.7% → 100% on the tuning set, and 100% on the held-out set.

**Would a multi-step agent help? No.** The task can be done simply and cheaply. One model call plus deterministic code reached 100% on the tuning and held-out sets at $0.0015 per report. More steps or agents would add cost, latency and more places for errors to creep in, with no remaining failure for them to fix.

## Prompt, scope, limits

**Prompt:**
- Values are kept as printed strings, because `Negative`, `< 0.5` and `2-3` carry meaning.
- Ranges are printed or null, because an invented range is read as the lab's.
- No status rule: code computes it (bounds count as normal; a word-range mismatch gives `review`).
- The kit's naming and "thorough" rules are kept but untested.

**Not done:** correcting values that don't add up, unit conversion, sex-specific ranges, frameworks.

**Limits:**
- The held-out set is only 28 rows, and I'd seen all 12 reports while auditing.
- The stress set is synthetic.
- Repeats show consistency, not spread.
- Status isn't scored by the eval (it's checked by `experiments/status_check.py`).
- report_11 Color and Appearance went missing under one earlier prompt version, so output can be sensitive to prompt wording.

## How I worked

1. **Planned first:** `PLAN.md` with predictions, before any code. I added two missed steps 16 minutes later, against the brief's rule.
2. **Labels before the eval:** I audited every gold row against its page, hand-labelled 04/07/10/12, and held them out.
3. **I set the eval rules:** tiers, review over guessing, abnormal rows, order not scored. Name matching was fixed before any extractor change.
4. **Baseline before fixes:** 3 repeats, then a diagnosis ranked by harm before anything was fixed.
5. **Fixes in batches I requested:** fixes 1–5 each in their own commit and run, with fixed/broken rows checked and a stop for my review after each batch. Only general rules.
6. **Proof last:** ablation and stress tests, then I froze `extract.py` and ran the held-out set once, with file hashes checked before and after.

## Decision log (one line each; detail in commits)

1. **Fixed eval name matching before any extractor change:** renames scored as a dropped row plus an invented row.
2. **I made the label calls**, not the agent: report_01 = `340000`, report_07's covered Globulin accepts `3.1` or null, and I verified all 28 held-out rows.
3. **Moved retries into `extract.py`:** the agent had them only in the runner, but graders run `extract.py` directly.
4. **Failure prints error JSON and exits 1:** the agent's first version printed nothing.
5. **Made the agent check token counts** before blaming "API overload" for the latency.
6. **Status bounds are inclusive**, even though report_09's lab flags Basophils `2` (range `0 - 2`) as H.
7. **Kept 60 DPI** (§5).
8. **Eval fix found by the ablation** (`63a50d2`): `Urine Pus Cells (WBC)` had been mapped to blood WBC. Re-scoring changed nothing else.
9. **Harness fixes:** UTF-8 for `µ` on Windows; slots that failed on 503 were re-run once, with the failure logged.
10. **Default model set** (`632ef87`) after the held-out run. That run used the same model through `GEMINI_MODEL`.
11. **Trimmed the eval** (vocabulary moved to JSON) and required tests for it.
12. **A unit printed in the range cell counts as correct** (report_06): gold moved those units into the unit field, so the eval joins unit and range before comparing. Either placement passes; a different unit still fails.

I also checked by hand every root-cause line, every gold row against its page, and each fix's diff before it ran.

**Transcripts:** to be added under `transcripts/`, unedited apart from redacted API keys.
