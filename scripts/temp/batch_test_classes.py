import os
import json
import base64
import requests
import time

API_KEY = "YOUR_API_KEY_HERE"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={API_KEY}"

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

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inlineData": {
                            "mimeType": "image/png",
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
        response = requests.post(URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            try:
                resp_json = response.json()
                text_response = resp_json['candidates'][0]['content']['parts'][0]['text']
                extracted_data = json.loads(text_response)
                return extracted_data
            except Exception as e:
                return {"error": "Failed to parse JSON", "raw": response.text}
        elif response.status_code == 503:
            wait_time = 2 ** attempt
            time.sleep(wait_time)
        else:
            return {"error": f"Status code {response.status_code}", "raw": response.text}
            
    return {"error": "Failed after maximum retries."}

if __name__ == "__main__":
    files_to_test = [
        ("Class I", "data/raw/Class I - 1-pdf_page_1_png.rf.LhnoZOQF9lvjYgyGmVDn.png"),
        ("Class II", "data/raw/Class II - 1-pdf_page_1_png.rf.TRDTpSLeBPuoGnhptC4m.png"),
        ("Class III", "data/raw/Class III - 1-pdf_page_1_png.rf.Rsn19RKUF7afJXdLBFpd.png"),
        ("Class IV", "data/raw/Class IV - 1-pdf_page_1_png.rf.L8DN5vqQzsupKlGsHkCh.png"),
        ("Class V", "data/raw/Class V - 1-pdf_page_1_png.rf.YvhE7pcb9VxwPZZs1qc1.png"),
        ("Class VI", "data/raw/Class VI - 1-pdf_page_1_png.rf.1Px6f9j1Wu9RiQ75vz8i.png"),
        ("Class VII", "data/raw/Class VII - 1-pdf_page_1_png.rf.6S7LDL2z2voczVSqIOdW.png")
    ]
    
    results = {}
    for class_name, filepath in files_to_test:
        print(f"Extracting {class_name}...")
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue
            
        result = extract_invoice(filepath)
        results[class_name] = result
        # To avoid rate limits immediately (15 requests per minute -> 1 request every 4 seconds)
        time.sleep(4)
        
    print("\n--- RESULTS ---")
    print(json.dumps(results, indent=2))
