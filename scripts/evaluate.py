import json
import os
import re
from dateutil import parser

EXTRACTED_FILE = "data/outputs/extraction_outputs_aggregated.json"
GROUND_TRUTH_FILE = "data/clean/qrscanned_cleaned.json"
CLEANED_EXTRACTED_FILE = "data/outputs/extraction_output_cleaned.json"

SUMMARY_FILE = "data/outputs/evaluation_summary.json"
DETAIL_FILE = "data/outputs/evaluation_detail.json"
DLQ_FILE = "data/outputs/dead_letter_queue.json"

def get_group_id(filename):
    if not filename: return ""
    match = re.search(r"^(.*?)[_-]?pdf_page_(\d+)", filename, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip().lower()
    return filename.strip().lower()

def clean_filename(filename):
    if not filename: return ""
    return filename.strip().lower()

def clean_date(date_str):
    if not date_str: return None
    date_str = str(date_str).strip()
    try:
        parsed_date = parser.parse(date_str, dayfirst=True)
        return parsed_date.strftime("%d-%m-%Y")
    except Exception:
        return "unparseable"

def clean_amount(val):
    if val is None: return None
    try:
        if isinstance(val, str):
            val = val.replace(',', '').replace('Rs.', '').replace('₹', '').strip()
        return round(float(val))
    except (ValueError, TypeError):
        return None

def clean_gstin(val):
    if not val: return None
    cleaned = str(val).upper().strip()
    if len(cleaned) != 15:
        return "invalid_format"
    return cleaned

def clean_docno(val):
    if not val: return None
    return str(val).strip()

def clean_record(record):
    return {
        "Filename": record.get("Filename"),
        "SellerGstin": clean_gstin(record.get("SellerGstin")),
        "BuyerGstin": clean_gstin(record.get("BuyerGstin")),
        "DocNo": clean_docno(record.get("DocNo")),
        "DocDt": clean_date(record.get("DocDt")),
        "TotInvVal": clean_amount(record.get("TotInvVal"))
    }

def main():
    # 1. Load data
    with open(EXTRACTED_FILE, 'r') as f:
        extracted_data = json.load(f)
        
    with open(GROUND_TRUTH_FILE, 'r') as f:
        gt_data = json.load(f)
        
    # 2. Clean extracted data and save
    cleaned_extracted = []
    for rec in extracted_data:
        cleaned_rec = clean_record(rec)
        cleaned_extracted.append(cleaned_rec)
        
    with open(CLEANED_EXTRACTED_FILE, 'w') as f:
        json.dump(cleaned_extracted, f, indent=4)
        
    # 3. Join on document group ID
    extracted_dict = {clean_filename(r["Filename"]): r for r in cleaned_extracted if "Filename" in r}
    
    # Deduplicate ground truth to Document Level
    gt_dict = {}
    for gt in gt_data:
        gt_clean = clean_record(gt)
        group_id = get_group_id(gt.get("Filename"))
        if group_id not in gt_dict:
            gt_clean["Filename"] = group_id
            gt_dict[group_id] = gt_clean
            
    gt_unique_docs = list(gt_dict.values())
    
    matched_records = []
    for gt_clean in gt_unique_docs:
        gt_group_id = gt_clean["Filename"]
        if gt_group_id in extracted_dict:
            matched_records.append((extracted_dict[gt_group_id], gt_clean))
            
    print(f"Matched {len(matched_records)} records out of {len(gt_unique_docs)} unique ground truth documents.")
    
    # 4. Compare
    fields_to_compare = ["SellerGstin", "BuyerGstin", "DocNo", "DocDt", "TotInvVal"]
    
    summary = {f: {"correct": 0, "wrong": 0, "not_extracted": 0, "unparseable": 0} for f in fields_to_compare}
    perfect_match_count = 0
    details = []
    dlq = []
    
    for ext, gt_clean in matched_records:
        detail_rec = {"Filename": ext.get("Filename")}
        is_perfect = True
        failures = []
        
        for field in fields_to_compare:
            ext_val = ext.get(field)
            gt_val = gt_clean.get(field)
            
            result = ""
            if ext_val is None or ext_val == "":
                result = "not_extracted"
                summary[field]["not_extracted"] += 1
                is_perfect = False
                failures.append({"field": field, "reason": "not_extracted", "extracted": ext_val, "ground_truth": gt_val})
            elif field == "DocDt" and ext_val == "unparseable":
                result = "unparseable"
                summary[field]["unparseable"] += 1
                is_perfect = False
                failures.append({"field": field, "reason": "unparseable", "extracted": ext_val, "ground_truth": gt_val})
            else:
                if field == "DocNo":
                    match = str(ext_val).lower() == str(gt_val).lower()
                else:
                    match = ext_val == gt_val
                    
                if match:
                    result = "correct"
                    summary[field]["correct"] += 1
                else:
                    result = "wrong"
                    summary[field]["wrong"] += 1
                    is_perfect = False
                    failures.append({"field": field, "reason": "wrong", "extracted": ext_val, "ground_truth": gt_val})
                    
            detail_rec[field] = {
                "extracted": ext_val,
                "ground_truth": gt_val,
                "result": result
            }
            
        detail_rec["perfect_match"] = is_perfect
        details.append(detail_rec)
        if is_perfect: perfect_match_count += 1
            
        if failures:
            dlq.append({
                "Filename": ext.get("Filename"),
                "failures": failures
            })
            
    # 5. Output
    total_gt = len(matched_records)
    print("\nField            | Correct | Wrong | Not Extracted | Total GT | Accuracy")
    print("-----------------|---------|-------|---------------|----------|----------")
    for field in fields_to_compare:
        c = summary[field]["correct"]
        w = summary[field]["wrong"]
        n = summary[field]["not_extracted"]
        u = summary[field].get("unparseable", 0)
        
        # Accuracy = correct / (correct + wrong)
        # Treat unparseable as wrong for accuracy calc if it exists
        den = c + w + u
        acc = (c / den * 100) if den > 0 else 0.0
        
        print(f"{field:<16} | {c:<7} | {w+u:<5} | {n:<13} | {total_gt:<8} | {acc:.1f}%")
        
        summary[field]["Accuracy"] = f"{acc:.1f}%"
        summary[field]["Total GT"] = total_gt
        
    pm_rate = (perfect_match_count / total_gt * 100) if total_gt > 0 else 0.0
    print(f"Perfect Match    | {perfect_match_count:<7} | {'-':<5} | {'-':<13} | {total_gt:<8} | {pm_rate:.1f}%")
    
    summary["Perfect Match"] = {
        "correct": perfect_match_count,
        "Total GT": total_gt,
        "Accuracy": f"{pm_rate:.1f}%"
    }
    
    with open(SUMMARY_FILE, 'w') as f: json.dump(summary, f, indent=4)
    with open(DETAIL_FILE, 'w') as f: json.dump(details, f, indent=4)
    with open(DLQ_FILE, 'w') as f: json.dump(dlq, f, indent=4)

if __name__ == "__main__":
    main()
