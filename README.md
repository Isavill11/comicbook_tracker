# personal comic collection tracker

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

Save that key to your environment variables and name it "COMICVINE_API_KEY"

## 3. Deploy 

## Known bugs
- **OCR matching is text-based, not pixel-based.** It works well for clean, well-lit photos of the cover logo/title but will sometimes surface no or wrong candidates for busy covers. A real next step: precompute perceptual hashes (`imagehash` library) for candidate cover images and rank them by visual similarity to the upload, instead of relying purely on OCR text.
- **Character avatars** currently reuse a random cover from that character's comics as the thumbnail (there's no character-portrait endpoint wired up yet). ComicVine's `/character/` endpoint has real character portraits if you want to swap that in.
- **No auth** — fine for a personal homelab app behind your own tunnel, but don't expose it to the open internet as-is.
- **Manual edit/delete of a saved comic** isn't built yet — only add.
