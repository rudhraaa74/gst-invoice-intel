# Project History & Milestones

This document logs the step-by-step progress, decisions, and outcomes made throughout the invoice extraction project.

## 1. Project Initialization & Structure Enforcement
- Enforced strict project structure (`/notebooks`, `/scripts`, `/data/raw`, `/data/clean`, `/data/outputs`).
- Established behavioral guidelines in `GEMINI.md` and `INSTRUCTIONS.md` to ensure minimum surgical code changes, simplicity, and strict adherence to rules.

## 2. API Setup & Small Batch Testing
- Evaluated and integrated the `gemini-3.1-flash-lite-preview` model for Vision-Language Model (VLM) extraction tasks.
- Tested extraction on a small subset of invoices to ensure the prompt accurately pulled the 5 required fields: `SellerGstin`, `BuyerGstin`, `DocNo`, `DocDt`, and `TotInvVal`.
- Implemented rate limiting (~8 requests per minute) to respect free-tier quotas and prevent 503 Resource Exhausted errors.

## 3. Full Dataset Extraction (Phase 1)
- Wrote `extract_all_invoices.py` to loop through the image directory.
- Added dynamic MIME type detection to support both `.png` and `.jpg`/`.jpeg` files.
- **Quota Hit:** Successfully extracted 492 out of 543 invoices. The process stopped exactly at 492 due to hitting the daily 500 requests per project quota on the free tier.
- Saved initial raw extractions to `data/outputs/extraction_outputs.json`.

## 4. Security & GitHub Sync
- Scrubbed all hardcoded API keys from scripts (`extract_all_invoices.py`, `batch_test_classes.py`, `test_gemini.py`) and documentation (`PLAN.md`), replacing them with standard environment variable calls (`os.getenv("GEMINI_API_KEY")`).
- Committed and pushed the 492 extracted invoices to the remote GitHub repository for safekeeping.

## 5. Evaluation Script Development (`evaluate.py`)
- Built an evaluation pipeline comparing the 492 extracted JSONs against 78 clean ground truth records (`qrscanned_cleaned.json`).
- Implemented robust data cleaning rules before comparison:
  - Date normalization parsing (standardized to `DD-MM-YYYY`, accounting for Indian format `dayfirst=True`).
  - GSTIN sanitization (stripping whitespace, enforcing uppercase, and validating 15-character length).
  - Number float conversion and rounding.
- Outputted three artifacts: `evaluation_summary.json` (metrics), `evaluation_detail.json` (per-record diff), and `dead_letter_queue.json` (only failed records).
- **Initial Metrics:** Highlighted near 100% accuracy on Dates and GSTINs, but only 60.8% accuracy on `TotInvVal`, with an overall Perfect Match rate of 30.8%.

## 6. Multipage Document Aggregation (`aggregate_multipage.py`)
- Identified that the 60% `TotInvVal` accuracy was due to invoices spanning multiple image pages, where the total only physically appeared on the final page, but earlier pages were being independently evaluated.
- Built a post-extraction Map-Reduce aggregation script.
- **Logic:** Grouped images by base Document ID parsing via regex (`^(.*?)[_-]?pdf_page_(\d+)`). Consolidated header information (GSTIN, DocNo, Date) from the first page, and strictly pulled the `TotInvVal` from the **last page** in the document group.
- Broadcasted the consolidated master record back to all original filenames to map correctly with the ground truth evaluations.
- **Improved Metrics:** Re-running the evaluation script with the aggregated data yielded massive improvements:
  - `TotInvVal` Accuracy: Jumped from 60.8% to **84.0%**.
  - Perfect Match Rate: Jumped from 30.8% to **66.7%**.

## 7. Evaluation Pipeline Hardening
- **Document-Level Evaluation:** Discovered the 78 ground truth page records actually mapped to only 47 unique invoices. Modified the evaluation pipeline to group and deduplicate both datasets by Document ID before comparison, preventing multipage invoices from artificially inflating success/failure rates.
- **Integer Rounding:** Adjusted the `clean_amount` function across both the aggregation and evaluation scripts to round `TotInvVal` to the nearest integer. This resolved false-negatives caused by sub-rupee decimal variations (e.g., `.96` vs `.0`).
- **Final Optimized Metrics:** Evaluating purely at the document level with rounded integers pushed the `TotInvVal` extraction accuracy to **89.1%**, and increased the overall Perfect Match Rate to **70.2%** (33 out of 47 documents extracted flawlessly across all 5 fields).

## 8. Next Steps & Pending Items
- **Quota Reset:** Run `extract_all_invoices.py` on the remaining ~50 files once the Gemini API free-tier quota resets.
- **Manual Corrections:** Use the generated `dead_letter_queue.json` to populate `data/clean/manual_entry.xlsx` for unextracted or failed invoices.
