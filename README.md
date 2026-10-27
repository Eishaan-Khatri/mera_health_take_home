# Lab report extraction: make it better, and prove it

**Setup changes from the kit:**
- `python extract.py <file>` still prints schema-valid JSON.
- The default model is now **`gemini-3.1-flash-lite`**, the cheapest Gemini with a published price. The kit's `gemini-3.8-flash` returned HTTP 503 "high demand" or hung during setup. `GEMINI_MODEL` still overrides it.
- Requirements: Python 3.10+, Poppler (`pdftoppm`) and `GEMINI_API_KEY`. No Python packages, except Pillow for `experiments/` only.
- **On failure** it prints `{"tests": [], "error": "..."}` and exits 1, so a failure never looks like a report with no tests.

```bash
python extract.py reports/report_01.pdf
python eval.py run --extractor extract.py --tag NAME     # 8 tuning reports x 3 repeats, scores, cost, latency
python eval.py score runs/baseline                       # re-score saved outputs, no API calls
python eval.py diff runs/baseline runs/fix7_timeouts_error_json
python test_eval.py                                      # 67 tests of the eval itself
```

Saved scores: [`runs/baseline/score.md`](runs/baseline/score.md) (baseline) and [`runs/fix7_timeouts_error_json/score.md`](runs/fix7_timeouts_error_json/score.md) (final).

## Results (8 tuning reports, 138 label rows, 3 repeats; all repeats byte-identical)

| | Correct rows | Critical errors | On abnormal rows | $ / report | Median latency |
|---|---|---|---|---|---|
| Baseline (kit `extract.py`, same model) | 71.7% | 10 | 2 | $0.00161 | 5.8 s |
| **Final** | **100%** | **0** | **0** | **$0.00153** | 10.8 s |
| Final, held-out 04/07/10/12 (28 rows, run once) | 100% | 0 | 0 | $0.00087 | 3.9 s |
| Final, degraded copies (5 kinds) | 98.6–100% | 0–2 | 0–1 | ≈ $0.0017 | ≈ 9 s |
| Baseline, same degraded copies | 68.8–72.5% | 7–10 | 1–2 | | |

**About latency:** it tracked Google's load, not our changes. Output tokens didn't grow, and there were no thinking tokens. But 503 errors went from 1 per run to 14–25 per run while time per output token rose 2–5×. Treat the latency numbers as noisy.

**At 10,000 reports a day:** about **$15 a day** at list price. The free tier allows 500 requests a day, so this needs the paid tier.

## 2. Eval: what counts as correct ([`eval.py`](eval.py))

**Pairing:** rows are paired by **test name, never by value**, using a synonym table and unit groups in [`eval_vocab.json`](eval_vocab.json). Blood and urine tests are never paired with each other.

**Comparing:** each pair is checked on value, unit and range, and the result goes into one of three tiers:
- 🔴 **Critical:** wrong value, wrong unit (including a scale change like `lakh` vs `/cumm`), wrong range, invented range, or invented row.
- ⚠️ **Miss:** dropped row, or a value, unit or range left empty.
- **Review:** anything ambiguous. It's flagged, never guessed, and never counted as correct.

**Cosmetic, not counted:** spacing, `2,29,000` vs `229000`, unit spelling within the same group, and a unit printed inside the range cell.

**Headline numbers:** correct-row rate plus critical errors, with critical errors on abnormal rows (value outside the printed range) reported separately. A crash, invalid JSON or an empty list counts as a failed report. Retries are reported separately from accuracy.

**Testing the eval:** the eval has its own tests. They break the labels one way at a time and check that exactly the right counter moves. Deliberately breaking each rule in `eval.py` makes at least one test fail.

**Labels** ([`labels/NOTES.md`](labels/NOTES.md)): `gold/` is untouched. `labels/` is a copy with one correction I made after reading the page (report_01 Platelets `304000` → `340000`). It also has my hand labels for the 4 unlabelled reports, drafted with the agent from high-resolution renders and checked row by row by me. Those 4 were **held out**: no model ran on them until a single final run.

**Baseline number:** 62.3% with my first eval, then **71.7%** after fixing the eval's name matching. That fix came before any extractor change (decision 1).

## 3. Diagnosis: the three failure categories that matter most for a patient

| # | Example (report / row) | Symptom | Root cause in the baseline |
|---|---|---|---|
| 1 | 06 / Sugar `Present (+)` → `1.0`; CRP `< 0.5` → `0.5`; `2-3` → `2.5` | Wrong numbers that look precise | Prompt rule `value must be a number.` and the example `"value": 0.0`. Then `to_number()` turned remaining text (`Dark Yellow`) into null. The schema allows strings. |
| 2 | 03 / Glycated Hb `6.0 %`, no range printed → range `4.0 - 5.6`, status `high` | A range the lab never printed, read as the lab's | Prompt rule `If a reference range is missing…, fill in the standard reference range` |
| 3 | 11 / Urea `42` (high), all 24 rows on page 2 | Rows missing | `pdftoppm -f 1 -l 1 -singlefile` sends page 1 only |

**Ranking:** by harm, a wrong number a doctor trusts comes first. But #3 is close to the top because it's **silent**: the output looks complete, so a doctor would assume page-2 tests were never done.

**PLAN.md hypotheses:**
- ✅ Held: page 1 only, numeric coercion, invented ranges, renaming.
- ❌ Didn't hold: 60 DPI misreads, Indian digit grouping (`2,29,000` was read correctly), two-column layouts, the model "correcting" values that don't add up.

## 4. Fixes, one at a time ([`runs/`](runs), each committed with its run)

| Fix | Correct rows | Critical | Rows fixed / broken |
|---|---|---|---|
| Baseline | 71.7% | 10 | |
| 1. Send every page | 83.3% | 12 | 16 / 0. Criticals went up because page-2 urine rows now hit bug #1. |
| 2. Value copied exactly as printed (string) | 95.7% | 3 | 17 / 0 |
| 3. Range copied as printed, or null; never filled in | **100%** | **0** | 6 / 0 |
| 4–5. Status computed in code from value + printed range (intervals too) | 100% | 0 | Status only: 60 guessed statuses → 0 |
| 6–7. Word-range status (`review`), retries inside `extract.py`, loud parse + error JSON, 90 s / 300 s cap | 100% | 0 | Status and robustness only |

**Ablation:** on the final code, I removed one fix at a time (3 repeats each).
- **All pages** off: 82.6% (24 rows broken).
- **Values as printed** off: 87.7% (6 critical).
- **No invented ranges** off: 97.8% (3 critical).
- **Status in code** off: 100% rows, because status isn't scored, but the status check drops from 414 to 390 agreeing (12 guessed, 12 wrong).

**Status rule:** low / normal / high when there's a numeric value and range, with bounds counting as normal. `review` when a word range like `Negative` or `Nil` doesn't match the value. Null otherwise.

**Stress set** ([`experiments/`](experiments)): 5 degraded copies of the tuning reports. Remaining errors are digit misreads on very low-resolution or blurred images. One matters: report_11 Eosinophils `0` (abnormal) was read as `8`.

## 5. What didn't help: 150 DPI

On degraded PDFs, 150 DPI scored **98.98%** vs **99.49%** at 60 DPI, with 3 critical errors vs 2. Input tokens were identical (1,434), because the API resizes images itself. The Eosinophils misread happened at both DPIs. I kept 60 DPI.

## 6. Three short answers

**Would RAG help?** No. Each report is self-contained, and nothing outside it should change what we extract. The one thing retrieval would supply, "standard" reference ranges, is exactly what fix 3 removed: a range the lab didn't print misleads a doctor. Retrieval could help *after* extraction, for example mapping printed names to a test catalogue. It wouldn't help reading the page.

**Would fine-tuning help?** Not now. Every baseline error on the tuning set came from the prompt or the code, and those are now fixed with 0 broken rows. What's left is digit misreads on images that are already damaged, and 12 reports can't train or validate a fix for that. At mera's volume, corrections from production (where users fix a value) could later justify fine-tuning a small model on real Indian lab layouts. It would have to be measured against this eval and the stress set.

**Would a multi-step agent help?** Not on this evidence. One model call plus deterministic code (paging, string values, status, retries) reached 100% on tuning and held-out, at about $0.0015 and 11 s per report. An agent would add cost, latency and nondeterminism to solve problems we no longer see. The one second step worth testing is a targeted re-read of cells on abnormal or `review` rows, which is where the stress misread happened. I'd measure it on `experiments/stress` before adding it.

## Prompt ([`extract.py`](extract.py)): why each rule is shaped this way

- **"value is a string, copied exactly as printed…"** The schema allows strings, and `Negative`, `< 0.5` and `2-3` carry meaning that a number loses.
- **"reference_range is copied as printed… use null. Never fill in a standard range."** A range the lab didn't print gets read as the lab's.
- **No status rule.** Status is computed in code, so it can't be guessed.
- **Kept from the kit:** "standard medical name" and "Be thorough". Removing the naming rule wasn't tested, and the eval tolerates renames.

## What I chose not to do

- No correcting values that don't add up (several reports' values don't add up on purpose).
- No unit conversion.
- No sex-specific ranges.
- No frameworks, RAG or agent.
- No new dependencies in `extract.py`.

## Limitations

- **Small held-out set:** 28 rows. A low error rate, like the 3 misreads in 690 stress row-checks, wouldn't show up in it.
- **Not fully blind:** I saw all 12 reports while auditing labels. No rule refers to a specific report.
- **Synthetic stress set,** and its phone copies may be too mild.
- **Determinism:** the model was deterministic at temperature 0, so the 3 repeats show consistency, not spread.
- **Status isn't scored by the eval;** it's checked separately in `experiments/status_check.py`.
- **report_11 Color and Appearance** went missing under one earlier prompt combination, so output can depend on prompt wording.

## Decision log (where I overruled the agent, and what I checked by hand)

| # | Decision | Why | Verified how |
|---|---|---|---|
| 1 | **Eval name matching fixed before any extractor change** (`872bbd7`). `Full Name (ABBR)` falls back to the abbreviation only if the full name is unknown; `Urine X` pairs only with bare `X`. | The baseline renames tests (as PLAN.md predicted), and each rename scored as a dropped row plus an invented row, so the score measured naming, not extraction. | 10 tests. Re-scored with no API calls: 62.3% → 71.7%, and report_06's real errors are still counted. |
| 2 | **Status bounds inclusive.** | Same rule for every lab. It can disagree with a lab's own flag: report_09 Basophils `2` (range `0 - 2`) is printed H, and we say normal. | Offline cases at both bounds; status check 414/414. |
| 3 | **Eval: `Urine X (ABBR)` never falls back to the abbreviation** (`63a50d2`), found by the ablation. | `Urine Pus Cells (WBC)` had been mapped to blood WBC. | Re-scored all 12 runs: only that ablation changed. |
| 4 | **Kept 60 DPI** (negative result above). | No benefit, same tokens. | `stress_*_dpi150` runs. |
| 5 | **Model `gemini-3.1-flash-lite`**, now also the default (`632ef87`). | Cheapest priced model; 3.8 Flash was overloaded. Graders run without `GEMINI_MODEL`. | Default run on report_08 identical to the final run. |
| 6 | **Label calls were mine, not the agent's.** It called report_01's gold "wrong"; I made it describe differences neutrally and decided myself. I kept `340000`, accepted `3.1` or null for report_07's covered Globulin cell, and verified all 28 held-out rows. | Changing the eval or labels to raise a score is the failure mode to avoid. | `labels/NOTES.md`. Scoring `gold/` against `labels/` differs only on that platelet row (a test). |
| 7 | **Retries moved inside `extract.py`** (the agent had them only in the eval runner). **Failure prints error JSON + exit 1** (the agent first printed nothing). | Graders run `extract.py` directly, and stdout must stay valid JSON. | Offline fake-network tests (503s, 429 with Retry-After, hangs, 401) and fake-clock timing (worst case 785 s → 300 s cap). |
| 8 | **Made the agent check tokens** instead of accepting "API overload" as the reason latency rose 6×. | An unsupported explanation is still unsupported. | Logs: total = input + output exactly, no thinking tokens, output unchanged. |
| 9 | **Trimmed the eval** (vocabulary moved to JSON), and required tests for ambiguous labels, the urine/blood rules and the eval itself. | It had grown to about 700 lines. | 67 tests; each deliberate break fails one. |
| 10 | **PLAN.md was edited once after its first commit** (`e33516f`: diagnose and write-up steps). | I missed them in the first draft. The brief says not to edit it, so I'm stating it here. | `git log PLAN.md` |
| 11 | **Two harness bugs fixed:** Windows pipes turned `µ` into `�` (runner now forces UTF-8; extractor unchanged). Slots that failed on 503 were re-run once, keeping `*.meta.failed.json`. | So data errors aren't scored as model errors. | Test reproduces the `µ` bug; every re-run is logged. |

I also checked by hand: every root-cause line in §3, all gold rows against the page (`labels/NOTES.md`), and each fix's diff before running it.

Agent transcripts: to be added under `transcripts/`, unedited apart from redacting API keys (all keys used are revoked).
