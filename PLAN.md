# Invoice Data Extraction Plan

We will use **Gemini 3.5 Flash** for extracting the invoice data. 

Below is an example `curl` command demonstrating how to make the API request:

```bash
curl "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent" \
  -H "x-goog-api-key: $GEMINI_API_KEY" \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{
    "contents": [
      {
        "parts": [
          {
            "text": "Explain how AI works in a few words"
          }
        ]
      }
    ]
  }'
```


# Invoice Header Extraction POC Plan

## Objective

Build a proof-of-concept invoice extraction pipeline using Gemini 3.1 Flash Lite Vision capabilities.

The goal is to extract the following fields from scanned invoice PNG images:

* SellerGstin
* BuyerGstin
* DocNo
* DocDt
* TotInvVal

The system should process invoices one image at a time and return structured JSON output.

---

# Dataset

Input:

* Approximately 480 invoice images
* PNG format
* Scanned invoices
* Variable invoice layouts

Output format:

[
{
"Filename": "...",
"SellerGstin": "...",
"BuyerGstin": "...",
"DocNo": "...",
"DocDt": "...",
"TotInvVal": 0.0
}
]

---

# API Constraints

Gemini 3.1 Flash Lite

Limits:

* 15 requests per minute
* 500 requests per day

Processing strategy:

* One invoice image per request
* Enforce rate limiting
* Target throughput must remain safely below 15 RPM
* Entire dataset should fit within daily quota

---

# Development Strategy

## Phase 1 – Environment Setup

Tasks:

* Configure Gemini API access
* Verify image upload capability
* Verify image-to-text extraction works
* Confirm model can return structured responses

Success Criteria:

* Single invoice image successfully processed
* Valid response returned from Gemini

---

## Phase 2 – Prompt Engineering

Design a highly constrained extraction prompt.

Requirements:

* Extract only the five required fields
* Return JSON only
* No explanations
* No markdown
* No additional fields

Model should understand:

SellerGstin:

* GSTIN belonging to the seller/vendor/supplier

BuyerGstin:

* GSTIN belonging to the buyer/customer/recipient

DocNo:

* Invoice number/document number

DocDt:

* Invoice date

TotInvVal:

* Grand total invoice value

Prompt must instruct model to return:

* null if field cannot be identified
* numeric value for TotInvVal

Success Criteria:

* Consistent JSON responses
* No malformed outputs

---

## Phase 3 – Small Batch Validation

Process only 4–5 invoices initially.

Tasks:

* Select representative invoices
* Run extraction
* Save outputs
* Compare against actual invoice contents manually

Evaluation:

For each invoice verify:

* Seller GSTIN correct
* Buyer GSTIN correct
* Invoice number correct
* Invoice date correct
* Total invoice value correct

Document common failures.

Examples:

* Buyer/Seller GSTIN swapped
* Incorrect total selected
* Tax amount extracted instead of invoice amount
* Date format issues
* Missing values

Success Criteria:

* Extraction quality acceptable for majority of fields

---

## Phase 4 – Prompt Refinement

Based on Phase 3 findings:

Refine extraction instructions.

Focus on:

* GSTIN disambiguation
* Multiple GSTIN handling
* Selecting final invoice amount
* Handling invoices with multiple totals
* Handling invoices with multiple dates

Repeat testing on another small sample.

Continue until output quality stabilizes.

---

## Phase 5 – Full Dataset Processing

After prompt validation:

Process all invoices.

Workflow:

Invoice Image
↓
Gemini API
↓
JSON Extraction
↓
Append Result
↓
Save Output

Requirements:

* Respect rate limits
* Log failures
* Continue processing after errors
* Maintain filename association

Output should contain one JSON object per invoice.

---

## Phase 6 – Error Logging

Maintain separate logs for:

API Failures:

* Request failures
* Timeout issues
* Quota issues

Extraction Failures:

* Invalid JSON
* Missing required fields
* Empty responses

Store original model response whenever parsing fails.

Purpose:

* Support prompt refinement later

---

## Phase 7 – Result Storage

Generate:

results.json

Containing:

[
{
"Filename": "...",
"SellerGstin": "...",
"BuyerGstin": "...",
"DocNo": "...",
"DocDt": "...",
"TotInvVal": 0.0
}
]

Optional:

* CSV export for review
* Accuracy evaluation sheet

---



# Evaluation Script Plan — Invoice Extraction

## Context
We have two JSON files:
- `extracted.json` — 492 invoices extracted via Gemini Flash VLM
- `ground_truth.json` — 78 invoices with ground truth values from QR decode

Both files have the same structure per record:
```json
{
    "Filename": "DSINV2023241697-pdf_page_2_png.rf.8WPSANMRuTVuAOvIImPt.png",
    "SellerGstin": "27AABCT1029L1ZC",
    "BuyerGstin": "19AAJCA1167G1ZO",
    "DocNo": "2714004902",
    "DocDt": "07/05/2023",
    "TotInvVal": 2127699.99
}
```

Goal is to join on Filename, clean both sides, compare field by field, and output accuracy metrics.

---

## Cleaning Rules (apply to BOTH sides before comparison)

### 1. Filename (join key)
- Case insensitive match
- Strip whitespace
- This is the only join key — if filename doesn't match, record is skipped

### 2. DocDt (date)
- Normalize both sides to `DD-MM-YYYY`
- Handle all these formats on extracted side:
  - `21-Feb-23`, `3-Dec-22`, `10-May-23`, `01-JUN-2023` — month name, 2 digit year
  - `27.05.2021`, `17.04.2023` — dot separated
  - `05-03-2018`, `28/03/2023`, `25/10/2017`, `13/10/2022` — dash or slash separated, always DD-MM-YYYY order
- Ground truth is always `DD/MM/YYYY` — convert to `DD-MM-YYYY`
- All dates are Indian format — always DD first, never MM first
- If date cannot be parsed after all attempts → tag as `unparseable`

### 3. TotInvVal (amount)
- Convert both sides to float
- Round both to nearest integer before comparing
- Handle integers on ground truth side (`1474788` → `1474788`)

### 4. SellerGstin / BuyerGstin (GSTIN)
- Uppercase both sides
- Strip all whitespace
- Valid GSTIN is exactly 15 characters — if length != 15 after cleaning, tag as `invalid_format`

### 5. DocNo
- Strip whitespace
- Case insensitive exact match
- Do not normalize format — DocNo formats are intentionally varied

---

## Null Handling
Nulls in extracted output must NOT be counted as wrong.
Track three categories per field per record:
- `correct` — extracted matches ground truth after cleaning
- `wrong` — extracted value present but does not match ground truth
- `not_extracted` — extracted value is null
- `unparseable` — value present but could not be cleaned/parsed (dates only)

---

## Output Required

### 1. Per-field accuracy summary (print to console and save as `evaluation_summary.json`)
```
Field            | Correct | Wrong | Not Extracted | Total GT | Accuracy
-----------------|---------|-------|---------------|----------|----------
SellerGstin      |   65    |   8   |      5        |    78    |  83.3%
BuyerGstin       |   70    |   4   |      4        |    78    |  89.7%
DocNo            |   60    |  12   |      6        |    78    |  76.9%
DocDt            |   55    |  15   |      8        |    78    |  70.5%
TotInvVal        |   72    |   3   |      3        |    78    |  92.3%
Perfect Match    |   45    |   -   |      -        |    78    |  57.7%
```
Accuracy = correct / (correct + wrong) — exclude not_extracted from denominator

### 2. Per-record detail (save as `evaluation_detail.json`)
One record per matched invoice showing:
```json
{
    "Filename": "...",
    "SellerGstin": { "extracted": "27AABCT1029L1ZC", "ground_truth": "27AABCT1029L1ZC", "result": "correct" },
    "BuyerGstin":  { "extracted": null, "ground_truth": "19AAJCA1167G1ZO", "result": "not_extracted" },
    "DocNo":       { "extracted": "2714004902", "ground_truth": "2714004902", "result": "correct" },
    "DocDt":       { "extracted": "17-04-2023", "ground_truth": "17-04-2023", "result": "correct" },
    "TotInvVal":   { "extracted": 750720.37, "ground_truth": 750720.37, "result": "correct" },
    "perfect_match": false
}
```

### 3. Dead letter queue (save as `dead_letter_queue.json`)
All records where any field is `wrong` or `not_extracted`, with failure reasons:
```json
{
    "Filename": "...",
    "failures": [
        { "field": "SellerGstin", "reason": "wrong", "extracted": "27AABCT1029L1ZB", "ground_truth": "27AABCT1029L1ZC" },
        { "field": "DocDt", "reason": "not_extracted", "extracted": null, "ground_truth": "07-05-2023" }
    ]
}
```

---

## Agent Prompt

Use this prompt verbatim with your coding agent:

---

> Write a Python script called `evaluate.py` that evaluates extracted invoice data against ground truth.
>
> **Inputs:**
> - `extracted.json` — list of extracted invoice records
> - `ground_truth.json` — list of ground truth invoice records
>
> Each record has fields: `Filename`, `SellerGstin`, `BuyerGstin`, `DocNo`, `DocDt`, `TotInvVal`
>
> **Step 1 — Join:**
> Parse the base document ID from the `Filename` (e.g., `DSINV2023241704-pdf_page_1` -> `DSINV2023241704`). Deduplicate the ground truth records by this ID. Match the extracted document groups to the unique ground truth documents.
>
> **Step 2 — Clean both sides before comparison using these exact rules:**
>
> - `DocDt`: normalize to `DD-MM-YYYY`. Dates are always Indian format (DD first). Handle: dot-separated, slash-separated, dash-separated, month names (Jan/Feb/JAN/FEB etc), 2-digit years (assume 20XX). If unparseable after all attempts, tag as `unparseable`.
> - `TotInvVal`: convert to float, round to nearest integer.
> - `SellerGstin` / `BuyerGstin`: uppercase, strip whitespace.
> - `DocNo`: strip whitespace, compare case-insensitively.
>
> **Step 3 — Compare each field and tag as one of:** `correct`, `wrong`, `not_extracted` (if extracted value is null), `unparseable` (dates only).
>
> **Step 4 — Output three files:**
>
> 1. `evaluation_summary.json` — per field counts of correct/wrong/not_extracted and accuracy (correct / correct+wrong). Also include perfect_match rate (all 5 fields correct).
> 2. `evaluation_detail.json` — per record breakdown showing extracted vs ground truth vs result for each field, and a `perfect_match` boolean.
> 3. `dead_letter_queue.json` — only records with at least one wrong or not_extracted field, listing each failure with field name, reason, extracted value, and ground truth value.
>
> **Step 5 — Print a clean summary table to console** showing per-field accuracy and perfect match rate.
>
> Use only Python standard library plus `dateutil` for date parsing. No other dependencies.

---

## Multipage Aggregation Step (`aggregate_multipage.py`)

**Context:** The extraction process treated each individual image as a separate invoice. For multipage documents (e.g., `DSINV2023241704-pdf_page_1_png` and `page_2`), the VLM successfully extracts header data from Page 1, but naturally fails to find the total value until the final page. 

**Solution:** A Map-Reduce aggregation script runs *before* evaluation to consolidate document data.

**Aggregation Rules:**
1. Parse base document ID and page number from the filename using regex `^(.*?)[_-]?pdf_page_(\d+)`.
2. Group all extracted records by document ID.
3. Consolidate a master record for each group:
   - Header fields (`SellerGstin`, `BuyerGstin`, `DocNo`, `DocDt`): Take the first valid value found across the pages (naturally biased towards page 1).
   - `TotInvVal`: Always fetch from the **last page** in the group to ensure the grand total is captured instead of intermediate sub-totals.
4. Output the consolidated list of unique documents.
5. Save as `extraction_outputs_aggregated.json` to be consumed by `evaluate.py`.

---

## Files Expected After Running Evaluation

```
outputs/
├── extraction_output_cleaned.json
├── extraction_outputs_aggregated.json
├── evaluation_summary.json
├── evaluation_detail.json
└── dead_letter_queue.json
```

---

## Notes for the Team
- Run this script after every new batch of extractions to track improvement
- Dead letter queue is the input to the manual correction process
- Do not manually edit extracted.json or ground_truth.json — cleaning happens inside the script only
- If matched record count is significantly below 78, check filename casing differences between the two files

# Future Extensions (Not Part of Current Scope)

Do NOT implement yet.

Potential future work:

* Confidence scoring
* Active learning workflow
* Human correction interface
* Continuous retraining pipeline
* Invoice anomaly detection
* Duplicate invoice detection
* GST validation rules
* Benchmarking against open-source extraction systems

Current objective is ONLY:

Reliable extraction of the five required header fields from invoice images using Gemini 3.1 Flash Lite.

