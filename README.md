# Lab report extraction: make it better, and prove it

**Setup changes from the kit:**
- Default model **`gemini-3.1-flash-lite`**, the cheapest priced Gemini (the kit's 3.8 Flash returned 503s). `GEMINI_MODEL` overrides it.
- Requirements: Poppler and `GEMINI_API_KEY`. Pillow only for `experiments/`.
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

| Fix (1–5: one commit and run each; 6 and 7 batched) | Correct | Critical | Fixed / broken |
|---|---|---|---|
| 1. Send every page | 83.3% | 12 (page 2 now hits #1) | 16 / 0 |
| 2. Value as printed | 95.7% | 3 | 17 / 0 |
| 3. Range as printed or null | **100%** | **0** | 6 / 0 |
| 4–6. Status from code: numbers, intervals, then word ranges (`review`) | 100% | 0 | bad statuses per run 8 → 0* |
| 7. Retries in `extract.py`, error JSON, 90 s / 300 s cap | 100% | 0 | — |

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

**RAG: no.** Each report is self-contained. What retrieval would add, "standard" ranges, is what fix 3 removed.

**Fine-tuning: not now.** The baseline errors were prompt and code faults, now fixed. Damaged-image misreads would need far more than 12 reports to train or validate; production corrections could justify it later.

**Agent: not earned.** One call plus deterministic code reached 100% at $0.0015 per report. Re-reading abnormal or `review` cells is the only second step worth testing, on the stress set first.

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

I also checked by hand every root-cause line, every gold row against its page, and each fix's diff before it ran.

**Transcripts:** to be added under `transcripts/`, unedited apart from redacted API keys.
