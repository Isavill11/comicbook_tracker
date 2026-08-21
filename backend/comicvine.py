"""
Thin client around the ComicVine API.
"""
import os
import httpx

API_KEY = os.environ.get("COMICVINE_API_KEY", "1cf3770cb2a330297ae7b1e8ec88340818fbfac2")
BASE_URL = "https://comicvine.gamespot.com/api"
HEADERS = {"User-Agent": "comic-tracker-personal-app/1.0"}


async def search_issues(query: str, limit: int = 8):
    """Text search against ComicVine issues. Returns a list of candidate dicts
    the frontend can render as picker thumbnails."""
    if not API_KEY:
        raise RuntimeError("COMICVINE_API_KEY is not set")

    params = {
        "api_key": API_KEY,
        "format": "json",
        "query": query,
        "resources": "issue",
        "limit": limit,
    }
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        resp = await client.get(f"{BASE_URL}/search/", params=params)
        resp.raise_for_status()
        data = resp.json()

    candidates = []
    for r in data.get("results", []):
        volume = r.get("volume") or {}
        candidates.append({
            "comicvine_id": str(r.get("id")),
            "title": volume.get("name") or r.get("name") or "Unknown",
            "series": volume.get("name"),
            "issue_number": r.get("issue_number"),
            "cover_date": r.get("cover_date"),
            "cover_image_url": (r.get("image") or {}).get("medium_url"),
            "detail_url": r.get("api_detail_url"),
        })
    return candidates


async def get_issue_detail(comicvine_id: str):
    """Fetch full detail for one issue: writer credits, characters, storyline."""
    if not API_KEY:
        raise RuntimeError("COMICVINE_API_KEY is not set")

    params = {
        "api_key": API_KEY,
        "format": "json",
        "field_list": "name,issue_number,cover_date,image,person_credits,"
                       "character_credits,volume,story_arc_credits,publisher",
    }
    async with httpx.AsyncClient(headers=HEADERS, timeout=15) as client:
        resp = await client.get(f"{BASE_URL}/issue/4000-{comicvine_id}/", params=params)
        resp.raise_for_status()
        data = resp.json().get("results", {})

    writers = [p["name"] for p in data.get("person_credits", []) if "writer" in (p.get("role") or "").lower()]
    characters = [c["name"] for c in data.get("character_credits", [])]
    story_arcs = [s["name"] for s in data.get("story_arc_credits", [])]
    volume = data.get("volume") or {}

    return {
        "comicvine_id": comicvine_id,
        "title": volume.get("name") or data.get("name") or "Unknown",
        "series": volume.get("name"),
        "issue_number": data.get("issue_number"),
        "cover_date": data.get("cover_date"),
        "cover_image_url": (data.get("image") or {}).get("medium_url"),
        "author": ", ".join(writers),
        "characters": ", ".join(characters),
        "storyline": ", ".join(story_arcs),
        "publisher": (data.get("volume") or {}).get("publisher", {}).get("name")
                     if isinstance(data.get("volume", {}).get("publisher"), dict) else None,
    }
