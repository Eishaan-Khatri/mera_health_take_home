# Starter kit analysis (for discussion, not the plan)

Written before any code or model call. Everything below comes from reading the files and looking at every report (rendered at 110 DPI, and at the baseline's 60 DPI). Nothing here has been checked against real model output yet.

## 1. What the brief actually grades

| Area | What it means for us |
|---|---|
| Deliverables | `PLAN.md` committed **before any code** and never edited. Eval runnable with one command, with baseline and final output. README of 2 pages at most covering tasks 2–6 and a decision log. Prompts, each with a one-line rationale. Transcripts (optional, encouraged). Real git history, not squashed. |
| Hard constraint | `python extract.py <file>` must still print schema-valid JSON. It will be run on **6 unseen reports**. |
| Rejection triggers | Work we can't explain. A better number without evidence. **Sample-specific fixes presented as general.** **Changing the eval until the score goes up.** Ignoring cost. Over-engineering (150 → 1,500 lines). |
| Scoring | 50% process (decomposition, directing the agent, verification), 50% outcome (eval a doctor would care about, better vs merely different with n=8, cost at 10k/day, what we chose not to do). |
| Timebox | 4–6 hours. |
| Required answers | Three failure categories with a specific report, row and root cause. One thing that didn't help, with numbers. Short paragraphs on RAG, fine-tuning and agents. |

## 2. Baseline `extract.py`: problems found by reading it

| # | Where | Problem | Expected impact |
|---|---|---|---|
| B1 | `load_image`: `-f 1 -l 1 -singlefile` | **Only page 1 of a PDF is sent.** | report_11 is 2 pages, so 24 of its 54 gold rows (17% of all 138 gold rows) can't be extracted. |
| B2 | `DPI = 60` | PDFs are rendered at 60 DPI, which is too small to read. | Scanned reports 05, 06 and 07 at 60 DPI are barely legible: decimals, µ and the occluded cells in report_07. Likely digit misreads. JPGs are sent at full 1999×1464, so the two input paths behave differently. |
| B3 | Prompt: "If a reference range is missing… fill in the standard reference range" | **The model is told to make up ranges.** | report_03: T3, T4 and Glycated Hb have blank ranges (gold = `null`), so the baseline will invent them. A doctor would see a range the lab never printed. |
| B4 | Prompt: "value must be a number" + `to_number()` | Qualitative values are lost: they become `null` or are forced to a number. | report_06: 9 of 12 rows are non-numeric (`Dark Yellow`, `Negative`, `Present (+)`, `2-3`, `< 0.5`). report_11: 10 urinalysis rows (`Nil`, `8-10`…). `< 0.5` for CRP loses its meaning. The schema **allows strings**, so the baseline throws away information for nothing. |
| B5 | Prompt: "Use the standard medical name" | Printed names get renamed (`TG` → `Triglycerides`). | Breaks traceability to the printed row, and the eval then has to match aliases. It also invites merging or splitting rows. The schema says "one entry per result row on the report, in the order printed". |
| B6 | Prompt: "Be thorough. Do not miss any tests." | Pushes the model to over-extract. | report_12 is a **prescription, not a lab report**. The right output is `{"tests": []}`. The baseline may turn vitals (BP, pulse, weight) or "Investigations advised" into made-up rows. |
| B7 | Prompt asks for `status` | Extra field the model computes itself. The printed lab flags (`H`/`L` column, bold) are ignored. | Not a schema violation (`additionalProperties: true`). It costs tokens and can disagree with the lab, for example on sex-specific ranges. |
| B8 | `parse()` | Greedy `\{.*\}` regex. **Any failure silently returns `[]`**, with no retry. JSON mode / `responseSchema` isn't used. | A failed or truncated call looks the same as "no tests found", which hides failures in the eval. |
| B9 | `call_model` | No retry or backoff on 429/5xx. No `thinkingConfig`. `usageMetadata` (tokens) and latency aren't recorded. | We can't report cost or latency without adding instrumentation. Free-tier 429s will show up as crashes. |
| B10 | `MEDIA_TYPES` | Only jpg/jpeg/png. Anything else raises `KeyError` with a traceback, not a clean error. No EXIF rotation, deskew or crop. | Risk on the unseen 6 (webp, heic, PNG scans). Photos 08–10 are tilted with a brown background, which is wasted pixels and tokens. |
| B11 | Overall | No validation layer: no unit or range sanity checks, no check of rows against the page. | Nothing catches a hallucinated row. |

## 3. Reports: what each one tests

| Report | Format | Gold? | Rows | What makes it hard |
|---|---|---|---|---|
| 01 | Digital PDF, CBC | ✅ | 14 | Clean. **Gold differs from the page on one row, see §4.** Differential adds up to 115%. |
| 02 | Digital PDF, lipid + LFT | ✅ | 16 | Two sections. Rows with no unit (ratios). `<`/`>` ranges. The values themselves are internally inconsistent (see §5). |
| 03 | Digital PDF, thyroid/vitamin/diabetes | ✅ | 8 | **Value and unit in one cell** (`179 ng/dL`). **3 blank ranges**, which tests B3. |
| 04 | Digital PDF, renal + glycaemic (monospace) | ❌ | 9 | Empty FLAG column. Clean, and we can label it from the text layer plus a look at the page (cheap). |
| 05 | Scanned PDF (no text layer), CBC | ✅ | 14 | Skewed scan. **Platelets in `lakh/cumm` (3.03)**, which is a unit-scale trap. Differential adds up to 61%. |
| 06 | Scanned PDF, urine + inflammatory | ✅ | 12 | **Two-column layout**, with two tables side by side. **Unit printed inside the range cell** (`0 - 5 /hpf`, `< 5.0 mg/L`). Mostly qualitative values. "Albumin" here means urine albumin, not serum albumin. |
| 07 | Scanned PDF, LFT | ❌ | 10 | **A hand-drawn ellipse covers Serum Globulin** (value `3.1`, partly obscured; confirmed by the author). **Handwritten note** ("Repeat LFT after 6 wks…") must not become a row. Bold flags. Total bilirubin 0.16 < direct 0.23. |
| 08 | Phone photo (tilted), lipid | ✅ | 6 | Perspective tilt. Value and unit fused (`155 mg/dL`). Ratio row with no unit. |
| 09 | Phone photo, CBC (monospace) | ✅ | 14 | Tilt. **Indian digit grouping** `2,29,000` / `1,50,000 - 4,10,000`. FLAG column (H/L). Basophils `2` flagged **H** with range `0 - 2` (the lab's flag disagrees with its own range). |
| 10 | Phone photo, **shadow + fold**, thyroid + KFT | ❌ | 9 | Strong shadow band over the left third. Two-column layout. Units inside the range column. An empty table row. |
| 11 | Digital PDF, **2 pages**, full panel | ✅ | 54 | **Page 2 is dropped by B1.** It has every row type: qualitative, `Nil`, Indian grouping, µ units. It's the single biggest report, so it dominates any pooled metric. |
| 12 | Phone photo, **prescription** | ❌ | 0 | Not a lab report. Tests whether we refuse to extract (negative control). |

Total gold: **138 rows over 8 reports**. report_11 alone is 39% of them, so we should report both per-report (macro) and pooled (micro) numbers.

## 4. Gold label problems ("made in a hurry")

| # | Report / row | Issue | Proposal |
|---|---|---|---|
| G1 | **01 / Platelet Count** | Gold says `304000`. The page (image **and** text layer) says **`340000`**. **Resolved:** the author read the report and kept `340000`. | `gold/` is untouched. The correction is in `labels/report_01.json` and documented in `labels/NOTES.md` before any baseline was scored. Scores can be reported against both. |
| G2 | 06 / Leucocytes, Erythrocytes, Squamous, CRP, ESR | The labeler moved units out of the range cell (`0 - 5 /hpf` → unit `/hpf`, range `0 - 5`; `Nil /hpf` → range `Nil`). | A convention, not an error. The eval must accept either placement, or normalize unit+range before comparing. |
| G3 | 03 / T3, T4, Glycated Hb | Range is `null`, which is **correct** (blank on the page). | Use these as the hallucinated-range test cases. |
| G4 | All | Values are strings as printed (`"1.020"`, `"2,29,000"`, `"3.03"`). Ranges have spacing differences (`1-6` on the page vs `1 - 6` in gold, report_01). | The eval needs normalization: strip Indian/Western grouping, compare numerically while keeping significant trailing zeros where they matter (specific gravity `1.020`), and normalize whitespace, dashes and µ/u. |
| G5 | 05 / Platelet `3.03 lakh/cumm` vs 01 `340000 /cumm` | Same test, different scale. Gold keeps it **as printed**. | Decide: is "correct" the value as printed, or a normalized value? I recommend as printed (that is the schema), with unit conversion as an optional downstream step and not part of extraction. |

I checked every gold value for 01, 02, 03 and 11 against the PDF text automatically, and checked 05, 06, 08 and 09 by eye. G1 is the only value disagreement I found.

## 5. Data traps that are not label errors

- **Values that don't add up on purpose** (synthetic data). The extractor has to **transcribe, not correct**:
  - 02: indirect bilirubin 0.44 ≠ 1.06−0.20. Globulin 2.5 ≠ 7.1−4.9. A/G 2.3 ≠ 4.9/2.5.
  - 11: indirect 0.41 ≠ 1.31−0.07. Globulin 3.7 ≠ 7.2−4.9.
  - 05: MCH 28.3 but Hb/RBC gives about 20.4. Differential adds up to 61%. 01's adds up to 115%.
  - 07: total bilirubin 0.16 < direct 0.23.
  - So plausibility checks can only **flag** values, never auto-fix them. A model that "helpfully" corrects them scores worse.
- **Implausible but printed** values: ALT/AST `2 U/L` (02, 07, 11), HbA1c 3.6% (11). Same rule: keep them as printed.
- **Sex-specific ranges**: female patients printed with male Hb ranges (01, 09, 11). Names don't match sex either (Lakshmi = M, Vikram = F). Never infer anything from the name, and take ranges from the page only.
- **The lab's own flags disagree with ranges** (09 Basophils `2` H vs `0 - 2`). This is another reason not to compute `status` in the extractor.
- **PDF text layers: extraction mode matters.** `pdftotext -layout` seemed to put values one row away from their names in 01, 03, 04 and 11. That was an artifact of the extraction mode. `pdftotext -table` lines every row up correctly, so the text layers themselves are fine. *(Corrected; the earlier version of this note called it a trap in the PDFs.)*
- **Local env note**: this machine's `pdftoppm` comes from MiKTeX and warns `No display font for 'Symbol'/'ArialUnicode'`. The renders looked fine, but µ glyphs should be double-checked. A standalone Poppler would be safer.

## 6. Open questions to decide together

1. **What is "correct" for a row?** Proposed: a row matches by normalized name (alias-tolerant) plus order. Then each field is scored separately: **value** (most important clinically), **unit**, **range**. A value that's wrong because of a unit/scale mix-up counts as a value error.
2. **Clinical weighting**: should a wrong value or a hallucinated row cost more than a name-format difference? (I'd say yes, and a name-format difference should cost nothing.)
3. **Gold errata (G1)**: *resolved.* Corrected in `labels/`; `gold/` untouched.
4. **The 4 unlabeled reports**: *resolved.* Hand-labelled as a held-out set in `labels/` (28 rows: 9 + 10 + 9 + 0), checked by the author.
5. **Noise**: run the baseline 2–3 times to measure run-to-run variance before claiming any improvement. With n=8, a per-row bootstrap or paired comparison is needed.
6. **Model/provider**: Gemini free tier (`gemini-3.8-flash`) as given, or substitute? Either way, the baseline has to be measured on the same setup first.
7. **Cost/latency**: log `usageMetadata` tokens and wall time per report from the first run.
8. **Fix candidates (keep general, not sample-specific)**: all pages, higher DPI, a prompt that says "transcribe as printed, null if absent, strings allowed", JSON mode / `responseSchema`, no `status`, retry on bad JSON, a "not a lab report → empty" rule, and unit/range normalization in post-processing. Each one is tested separately so we can say what moved the number.
