import requests
import time
import json
import os



'''This is the script to scrape the dcuniverseinfinite comic collections to correct any misspellings in OCR process.'''

STUDIOS = ['DC', 'Marvel']

'''FIRST STEP: DC'''


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
    per_page = 100

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
        resp.raise_for_status()  # fail loudly instead of silently parsing bad JSON
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
    # placeholder until Marvel scraping is implemented
    return []


def main():
    dc_all_series = scrape_dc()
    marvel_all_series = scrape_marvel()

    all_series_raw = {
        "DC": dc_all_series,
        "Marvel": marvel_all_series,
    }

    out_dir = "backend/preprocess"
    os.makedirs(out_dir, exist_ok=True)  


    with open(os.path.join(out_dir, "all_comic_series_raw.json"), "w") as f:
        json.dump(all_series_raw, f, indent=2)


    
    series_names = {
        "DC": sorted({s["title"] for s in dc_all_series if "title" in s}),
        "Marvel": sorted({s["title"] for s in marvel_all_series if "title" in s}),
    }

    print(f"\nDC unique series: {len(series_names['DC'])}")
    print(f"Marvel unique series: {len(series_names['Marvel'])}")

    with open(os.path.join(out_dir, "all_comic_series_names.json"), "w") as f:
        json.dump(series_names, f, indent=2)


if __name__ == "__main__":
    main()