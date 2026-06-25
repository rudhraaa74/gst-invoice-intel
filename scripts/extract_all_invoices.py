import os
import json
import base64
import requests
import time
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in environment variables. Please check your .env file.")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={API_KEY}"
RAW_DIR = "data/raw"
OUTPUT_FILE = "data/outputs/extraction_outputs.json"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def extract_invoice(image_path):
    base64_image = encode_image(image_path)
    prompt = """
Extract the following fields from the invoice image and return ONLY a valid JSON object. 
Do not include any markdown formatting, explanations, or additional text.
If a field cannot be identified, return null.

Fields to extract:
- SellerGstin: GSTIN belonging to the seller/vendor/supplier
- BuyerGstin: GSTIN belonging to the buyer/customer/recipient
- DocNo: Invoice number/document number
- DocDt: Invoice date
- TotInvVal: Grand total invoice value (numeric value only)

Expected JSON format:
{
  "SellerGstin": "...",
  "BuyerGstin": "...",
  "DocNo": "...",
  "DocDt": "...",
  "TotInvVal": 0.0
}
"""

    # Determine mimeType
    mime_type = "image/jpeg" if image_path.lower().endswith(('.jpg', '.jpeg')) else "image/png"

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": base64_image
                        }
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json"
        }
    }
    
    headers = {
        "Content-Type": "application/json"
    }

    max_retries = 5
    for attempt in range(max_retries):
        try:
            response = requests.post(URL, headers=headers, json=payload, timeout=30)
            if response.status_code == 200:
                try:
                    resp_json = response.json()
                    text_response = resp_json['candidates'][0]['content']['parts'][0]['text']
                    extracted_data = json.loads(text_response)
                    return extracted_data, None
                except Exception as e:
                    return None, f"Failed to parse JSON: {e} | Raw: {response.text}"
            elif response.status_code == 503:
                wait_time = 2 ** attempt
                print(f"API 503 Unavailable. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                return None, f"Status code {response.status_code} | Raw: {response.text}"
        except Exception as e:
            wait_time = 2 ** attempt
            print(f"Request exception: {e}. Retrying in {wait_time}s...")
            time.sleep(wait_time)
            
    return None, "Failed after maximum retries."

def main():
    # Load existing progress
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, 'r') as f:
                extracted_data = json.load(f)
        except json.JSONDecodeError:
            extracted_data = []
    else:
        extracted_data = []

    # Map of already processed filenames
    processed_files = {item["Filename"] for item in extracted_data if "Filename" in item}
    
    # Get all PNGs and JPGs
    all_files = [f for f in os.listdir(RAW_DIR) if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
    files_to_process = [f for f in all_files if f not in processed_files]
    
    print(f"Total images: {len(all_files)}")
    print(f"Already processed: {len(processed_files)}")
    print(f"Remaining to process: {len(files_to_process)}")
    
    for i, filename in enumerate(files_to_process, 1):
        filepath = os.path.join(RAW_DIR, filename)
        print(f"\n[{i}/{len(files_to_process)}] Processing {filename}...")
        
        result, error = extract_invoice(filepath)
        
        if error:
            print(f"ERROR processing {filename}: {error}")
            # Optionally we could log errors to a separate file as per Phase 6
            # For now, we'll continue and maybe skip writing it so it can be retried later
        else:
            # Add Filename and structure it like the cleaned json
            final_item = {
                "Filename": filename,
                "SellerGstin": result.get("SellerGstin"),
                "BuyerGstin": result.get("BuyerGstin"),
                "DocNo": result.get("DocNo"),
                "DocDt": result.get("DocDt"),
                "TotInvVal": result.get("TotInvVal")
            }
            
            extracted_data.append(final_item)
            
            # Write 'live' to output file
            with open(OUTPUT_FILE, 'w') as f:
                json.dump(extracted_data, f, indent=4)
                
            print(f"Successfully extracted: {final_item}")
            
        # Maintain ~8 RPM (60 / 8 = 7.5 seconds per request)
        print("Sleeping for 7.5 seconds to respect rate limits...")
        time.sleep(7.5)

if __name__ == "__main__":
    main()
