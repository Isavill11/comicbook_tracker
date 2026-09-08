"""
Thin client around the ComicVine API.
"""
import os
import json
import requests



COMICVINE_API_KEY = os.environ.get("COMICVINE_API_KEY")
BASE_URL = "https://comicvine.gamespot.com/api/search"


def search_comicvine(query: str, resources: str = "issue,volume", limit: int = 10) -> dict:
    """
    Query the Comic Vine /search endpoint.

    Args:
        query: Free-text search string, e.g. "Absolute Batman 12 Snyder"
        resources: Comma-separated resource types to filter on
                   (e.g. "issue", "volume", "issue,volume")
        limit: Max results to return (API caps this at 100 for /search... 
               actually caps at 10 by default, so pass it explicitly if you want more)

    Returns:
        Parsed JSON response as a dict
    """

    
    headers = {
        # Comic Vine rejects requests without a real-looking User-Agent
        "User-Agent": "Longbox/0.1 (comic cataloging app; personal project)"
    }
    params = {
        "api_key": COMICVINE_API_KEY,
        "format": "json",
        "query": query,
        "resources": resources,
        "limit": limit,
    }

    response = requests.get(BASE_URL, headers=headers, params=params, timeout=10)
    response.raise_for_status()  # raises on 4xx/5xx
    return response.json()

def find_comicvine_issue(volume_query: str, issue_number: str, resources="volume"):
    data = search_comicvine(volume_query, resources=resources, limit=20)
    candidates = data.get("results", [])

    from rapidfuzz import fuzz
    ranked = sorted(
        candidates,
        key=lambda c: fuzz.token_set_ratio(volume_query, c.get("name", "")),
        reverse=True,
    )
    return ranked



query = "Absolute Batman Snyder 12"


if __name__ == "__main__":
    result = search_comicvine(query, limit=10)
    print(f"status_code: {result.get('status_code')}")
    print(f"total_results: {result.get('number_of_total_results')}")
    for item in result.get("results", []):
        print(json.dumps({
            "resource_type": item.get("resource_type"),
            "name": item.get("name") or item.get("volume", {}).get("name"),
            "issue_number": item.get("issue_number"),
            "id": item.get("id"),
        }, indent=2))