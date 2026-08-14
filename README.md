# Longbox — personal comic collection tracker

## What's here (working MVP)
- `POST /api/upload` — take a cover photo, OCR the text, search ComicVine, return candidate thumbnails
- `POST /api/comics` — confirm a candidate, save it (auto-assigns the next `collection_order`, so the homepage default sort is "in the order I got them")
- `POST /api/comics/manual` — add a comic by hand if OCR/ComicVine can't find it
- `GET /api/comics?character=&series=&author=&storyline=&date_from=&date_to=` — homepage listing + filters
- `GET /api/characters` — distinct characters across your collection, for the avatar rail
- Static frontend (`frontend/`) implementing the homepage grid, the character avatar rail, and filter dropdowns, styled to a "longbox" comic look

## 1. Run it locally first (fastest way to test)

```bash
cd comic-tracker/backend
pip install -r requirements.txt
# tesseract must also be installed on your machine:
#   Ubuntu/Debian: sudo apt install tesseract-ocr
#   macOS: brew install tesseract
export COMICVINE_API_KEY=your_key_here
export DB_PATH=./comics.db
export UPLOAD_DIR=./uploads
uvicorn main:app --reload
```
Visit `http://localhost:8000`.

## 2. Get a ComicVine API key
Sign in at https://comicvine.gamespot.com/api/ and copy your key. Free, generous rate limits for personal use.

## 3. Deploy to your ZimaOS box (so it's reachable from your phone)

Since you've already got Cloudflare Tunnel + CasaOS running for Immich/WebDAV, this slots in the same way:

```bash
# on the ZimaOS box
git clone <your repo, or scp the folder over>
cd comic-tracker
echo "COMICVINE_API_KEY=your_key_here" > .env
docker compose up -d --build
```

This exposes it on port `8010`. Two ways to reach it from your phone:
- **Cloudflare Tunnel** (recommended, matches your existing setup): add a route for something like `comics.isaserver.online` → `http://localhost:8010`, same pattern as `photos.isaserver.online`.
- **Tailscale**: since Tailscale + MagicDNS is already running, you can hit `http://zimahome.tail303d7f.ts.net:8010` directly with zero extra config.

Either way, add it to your phone's home screen as a bookmark ("Add to Home Screen") and it behaves like an app icon.

## Known rough edges to improve next (left for you, as requested)
- **OCR matching is text-based, not pixel-based.** It works well for clean, well-lit photos of the cover logo/title but will sometimes surface no or wrong candidates for busy covers. A real next step: precompute perceptual hashes (`imagehash` library) for candidate cover images and rank them by visual similarity to the upload, instead of relying purely on OCR text.
- **Character avatars** currently reuse a random cover from that character's comics as the thumbnail (there's no character-portrait endpoint wired up yet). ComicVine's `/character/` endpoint has real character portraits if you want to swap that in.
- **No auth** — fine for a personal homelab app behind your own tunnel, but don't expose it to the open internet as-is.
- **Manual edit/delete of a saved comic** isn't built yet — only add.
