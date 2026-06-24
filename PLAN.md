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

