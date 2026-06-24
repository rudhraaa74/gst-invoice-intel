import os
import sys
import json
import base64
import requests

API_KEY = "YOUR_API_KEY_HERE"
URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite-preview:generateContent?key={API_KEY}"

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def test_extraction(image_path):
    print(f"Testing extraction on {image_path}...")
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

    import time
    max_retries = 5
    for attempt in range(max_retries):
        response = requests.post(URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            print("Success! Response:")
            try:
                resp_json = response.json()
                text_response = resp_json['candidates'][0]['content']['parts'][0]['text']
                # Attempt to parse the text as JSON to verify it is valid JSON
                extracted_data = json.loads(text_response)
                print(json.dumps(extracted_data, indent=2))
            except Exception as e:
                print("Failed to parse response as JSON.", e)
                print("Raw response:")
                print(response.text)
            return
        elif response.status_code == 503:
            wait_time = 2 ** attempt
            print(f"API 503 Unavailable. Retrying in {wait_time} seconds (Attempt {attempt+1}/{max_retries})...")
            time.sleep(wait_time)
        else:
            print(f"API Request Failed with status code {response.status_code}")
            print(response.text)
            return
            
    print("Failed after maximum retries.")

if __name__ == "__main__":
    test_image = "data/raw/2002023-pdf_page_1_png.rf.0Nd3y7fbHCEutm9jkN4q.png"
    if os.path.exists(test_image):
        test_extraction(test_image)
    else:
        print(f"Test image not found at {test_image}")
