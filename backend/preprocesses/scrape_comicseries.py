import requests
import time
import json



'''This is the script to scrape the dcuniverseinfinite comic collections to correct any mispellings in ocr process.'''


'''FIRST STEP: DC'''

STUDIOS = ['DC', 'Marvel']

def scrape_dc():
    url = "https://www.dcuniverseinfinite.com/api/search_proxy/1/search"
    headers = {
        "content-type": "application/json;charset=UTF-8",
        "x-consumer-key": "DA59dtVXYLxajktV",
        "referer": "https://www.dcuniverseinfinite.com/browse/comics",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "cookie": "PASTE_YOUR_COOKIE_HERE",
    }

    dc_all_series = []
    page = 1
    per_page = 100  # try bumping this up first

    while True:
        payload = {
            "page": page,
            "per_page": per_page,
            "document_types": ["comicseries"],
            "filters": {},
            "apply_transform": True,
            "sort_direction": {"comicseries": "asc"},
            "sort_field": {"comicseries": "title"},
        }

        resp = requests.post(url, json=payload, headers=headers)
        data = resp.json()

        records = data.get("records", {}).get("comicseries", [])
        if not records:
            break  # no more pages

        dc_all_series.extend(records)
        print(f"page {page}: got {len(records)} series (running total: {len(dc_all_series)})")

        page += 1
        time.sleep(0.5)  # dont be a dick

    return dc_all_series



'''SECOND STEP: MARVEL'''

def scrape_marvel():
    pass



dc_all_series = scrape_dc()
marvel_all_series = scrape_marvel()


all_series = zip(STUDIOS, [dc_all_series, marvel_all_series])

# Save raw results
with open("/backend/preprocess/all_comic_series_raw.json", "w") as f:
    json.dump(all_series, f, indent=2)

# # Build your name-only reference dict for OCR matching
# series_names = sorted(set(s["title"] for s in all_series if "title" in s))
# print(f"\nTotal unique series: {len(series_names)}")