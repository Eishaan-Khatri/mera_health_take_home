# Labels: provenance

`labels/` is the single label set the eval uses, covering all 12 reports. `gold/` is kept untouched as the original reference.

- **01, 02, 03, 05, 06, 08, 09, 11**: copied from `gold/`. Any correction is made here only and listed under "Gold corrections" below. Every file except `report_01.json` is byte-identical to its `gold/` original.
- **04, 07, 10, 12**: the held-out set, labelled by hand (see below).

Held-out set for reports without gold (04, 07, 10, 12). Same format as `gold/`. **No extraction model has been run on these four reports.** Keep it that way until the final evaluation.

**Who made them:** drafted by Claude (the coding agent) reading high-resolution renders, then checked row by row by the author against the reports. Status: ☑ human-verified (all 28 rows).

**Conventions (copied from `gold/`):**
- Values are strings, exactly as printed (`"1.00"`, not `1`).
- Rows are listed in reading order: left table, then right table, within each section.
- When a report prints the unit inside the range cell (`80 - 200 ng/dL`), the unit goes in `unit` and the range keeps only `80 - 200`. This is the same split `gold/report_06.json` uses.
- `unit` is `null` when none is printed (ratios). `reference_range` is `null` when none is printed.
- No cell is left ambiguous. The one partly covered cell (report_07 Serum Globulin) was settled by the author; see below.

| Report | Source | How it was checked | Rows | Notes |
|---|---|---|---|---|
| 04 | Digital PDF | PDF text layer (`pdftotext -table`), cross-checked against a 220 DPI render | 9 | Clean. The FLAG column is empty on every row. |
| 07 | Scanned PDF | 220 DPI render, table cropped and zoomed 1.6× | 10 | **Serum Globulin = `3.1`, decided by the author.** A hand-drawn ellipse crosses the value cell. `3.` is legible and the ellipse stroke runs through the second digit, which reads as `1`. The draft marked it ambiguous; the author read the report and confirmed `3.1`. Its unit `g/dL` is partly covered and was taken from the visible `/dL` plus the column. Do **not** use arithmetic to settle it: A/G 1.2 suggests about 3.7, total minus albumin gives 3.3, and this report's values are internally inconsistent anyway (total bilirubin 0.16 < direct 0.23). The handwritten note ("Repeat LFT after 6 wks / Avoid alcohol. Review.") is not a result row, so it has no label. Bold values (0.16, 2, 55, 26) are lab flags and aren't part of the schema. |
| 10 | Phone photo (shadow + fold) | Original JPG, each table cropped and upscaled about 2× | 9 | Everything is legible despite the shadow over the left third and the blur. Units come from the range cells. The empty row under TSH is not a result. |
| 12 | Phone photo | Full image | 0 | A doctor's prescription, not a lab report. It has vitals (BP, pulse, weight, temperature), medicines and "Investigations advised" (tests ordered, with no results). None of these is a lab result, so the expected output is `{"tests": []}`. |

## Gold corrections (author-decided)

| File | Change | Decided by | Evidence |
|---|---|---|---|
| `labels/report_01.json` | Platelet Count `304000` → `340000`. Everything else unchanged from `gold/report_01.json` | Author, after reading the report | PDF text layer and render both show `340000` |

**Decided (author):** `gold/report_06.json` stays as is. In the eval, a unit printed inside the range cell and a unit in its own field count as the same, a cosmetic difference: unit and range are joined before comparing. A different unit is still an error. Range whitespace (`1-6` vs `1 - 6`) is ignored.

The eval reads only `labels/`. For transparency it can also score the 8 originally labelled reports against the untouched `gold/`, and report both numbers.

## Gold audit (gold/ unchanged)

| Report / row | Gold says | Page shows | How checked |
|---|---|---|---|
| 01 / Platelet Count | value `304000` | `340000` | PDF text layer (`pdftotext -table`) and a 110 DPI render both read `340000` |
| 06 / Leucocytes, Erythrocytes, Squamous Epithelial Cells, CRP, E.S.R. | unit `/hpf`, `mg/L`, `mm/hr`; range without unit (`0 - 5`, `Nil`, `< 5.0`, `0 - 15`) | No unit column. The unit is printed inside the range cell (`0 - 5 /hpf`, `Nil /hpf`, `< 5.0 mg/L`, `0 - 15 mm/hr`) | 220 DPI render |
| 01, 11 / ranges `1 - 6`, `0 - 2`, `0 - 5` | spaced (`1 - 6`) | Text layer has `1-6` / `0-2` / `0-5`. The render shows them spaced (01) | Text layer vs render. Whitespace only |

Every other gold row matched on all four fields (name, value, unit, range):
- 01, 02, 03 and 11: checked programmatically against the PDF text layer.
- 05, 06, 08 and 09: checked by eye against 220 DPI renders or the original JPG crops.
- No result rows on any page are missing from gold, and no gold row is absent from its page.
