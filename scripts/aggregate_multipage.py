import json
import re

INPUT_FILE = "data/outputs/extraction_outputs.json"
OUTPUT_FILE = "data/outputs/extraction_outputs_aggregated.json"

def clean_amount(val):
    if val is None: return None
    try:
        if isinstance(val, str):
            val = val.replace(',', '').replace('Rs.', '').replace('₹', '').strip()
        return round(float(val))
    except (ValueError, TypeError):
        return None

def main():
    with open(INPUT_FILE, 'r') as f:
        extracted_data = json.load(f)
        
    # Group records
    grouped_records = {}
    record_map = {} # to keep original filename mapping
    
    for rec in extracted_data:
        filename = rec.get("Filename", "")
        # Parse base doc group and page
        match = re.search(r"^(.*?)[_-]?pdf_page_(\d+)", filename, flags=re.IGNORECASE)
        if match:
            group_id = match.group(1)
            page_num = int(match.group(2))
        else:
            group_id = filename
            page_num = 1
            
        if group_id not in grouped_records:
            grouped_records[group_id] = []
            
        grouped_records[group_id].append({
            "rec": rec,
            "page": page_num
        })
        record_map[filename] = group_id
        
    # Consolidate
    consolidated_groups = {}
    for group_id, pages in grouped_records.items():
        # Sort by page number to prioritize page 1 for header info
        pages.sort(key=lambda x: x["page"])
        
        seller = None
        buyer = None
        docno = None
        docdt = None
        max_tot = None
        for p in pages:
            rec = p["rec"]
            if not seller and rec.get("SellerGstin"): seller = rec.get("SellerGstin")
            if not buyer and rec.get("BuyerGstin"): buyer = rec.get("BuyerGstin")
            if not docno and rec.get("DocNo"): docno = rec.get("DocNo")
            if not docdt and rec.get("DocDt"): docdt = rec.get("DocDt")
            
        # The pages are sorted by page number, so pages[-1] is the last page.
        # Use the TotInvVal from the last page.
        raw_tot = pages[-1]["rec"].get("TotInvVal")
            
        consolidated_groups[group_id] = {
            "SellerGstin": seller,
            "BuyerGstin": buyer,
            "DocNo": docno,
            "DocDt": docdt,
            "TotInvVal": raw_tot
        }
        
    # Output consolidated groups
    aggregated_output = []
    for group_id, master in consolidated_groups.items():
        new_rec = {
            "Filename": group_id,
            "SellerGstin": master.get("SellerGstin"),
            "BuyerGstin": master.get("BuyerGstin"),
            "DocNo": master.get("DocNo"),
            "DocDt": master.get("DocDt"),
            "TotInvVal": master.get("TotInvVal")
        }
        aggregated_output.append(new_rec)
        
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(aggregated_output, f, indent=4)
        
    print(f"Aggregated {len(extracted_data)} records into {len(aggregated_output)} document groups.")
    print(f"Saved aggregated results to {OUTPUT_FILE}.")

if __name__ == "__main__":
    main()
