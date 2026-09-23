import os
import shutil
import uuid
from typing import Optional, List

import cv2
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import Base, engine, get_db
from backend.comics_sqlite import Comic, normalize_publisher
from backend.crop_comics import ComicCropper
import backend.comicvine as comicvine
from backend.ollama_ocr import ensure_ollama_running, query_ollama_vision
import backend.ocr as ocr
from backend.repository import save_comic, delete_comic
import logging


Base.metadata.create_all(bind=engine)

DEFAULT_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", DEFAULT_UPLOAD_DIR)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# cropped images directory
CROP_DIR = os.path.join(UPLOAD_DIR, "crops")
os.makedirs(CROP_DIR, exist_ok=True)

app = FastAPI(title="Comic Tracker")

comic_cropper = ComicCropper(r'backend\ML\runs\obb\train-6\weights\best.pt', confidence_level=0.85)
# needs COMICVINE_API_KEY set in the environment (see README) - used by both

comicvine_client = comicvine.ComicVineClient()
logging.basicConfig(level=logging.INFO)


# ---------- step 1: upload a photo, detect comic book instances and crop necessary images ----------

class DetectedComic(BaseModel):
    crop_id: str
    crop_image_path: str          # relative path frontend can use to display the cropped cover
    series_title: Optional[str]      # None if OCR couldn't read anything usable
    issue_number: Optional[str] = None   # string, not int - ComicVine issue numbers include "1AU", "Annual 1", etc.
    publisher: Optional[str] = None
    creators: Optional[List] = None
    cover_date: Optional[str] = None
    storyline: Optional[str] = None
    characters: Optional[str] = None  # comma separated

    # populated only when Ollama was confident AND ComicVine confirmed a single
    # exact issue - the frontend can prompt "save this?" and POST /comics with
    # comicvine_id directly, no further lookup needed.
    comicvine_id: Optional[int] = None
    volume_name: Optional[str] = None
    cover_image_url: Optional[str] = None

    needs_manual_text: bool      # True -> no confirmed comicvine_id above; frontend needs manual text entry/correction instead of a direct save prompt


class UploadResponse(BaseModel):
    uploaded_image_path: str
    annotated_image_path: Optional[str] = None   # full image w/ bounding boxes drawn - only set when the dev-only save below is enabled
    detected_comics: List[DetectedComic]


@app.post("/upload", response_model=UploadResponse)
def upload_cover(file: UploadFile = File(...), use_ollama: bool = Form(True)):
    ''' Args: file - uploaded image file that contains comics user want to enter to db.
              use_ollama - toggle/checkbox that frontend sends to api (t/f)'''

    # 1. save the raw upload
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_name)

    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 2. run detection/cropping  
    crops, annotated_cv2drawn_image = comic_cropper.crop_comics(saved_path)
    if not crops:
        raise HTTPException(
            400,
            "No comics detected in that image, try a clearer photo with the covers fully visible."
        )

# -------------------------------------------------------------------------------
    ''' THIS PART IS FOR DEVELOPMENT PURPOSES ONLY. UNCOMMENT IT TO SAVE THE ANNOTATED YOLO DETECTIONS TO DIR

    annotated_name = f"{uuid.uuid4().hex}_annotated.jpg"
    annotated_path = os.path.join(UPLOAD_DIR, annotated_name)
    cv2.imwrite(annotated_path, annotated_cv2drawn_image)'''
# -------------------------------------------------------------------------------
    try:
        if use_ollama:
            ensure_ollama_running()
            ollama_running = True
    except RuntimeError:
        print('Ollama is not installed or running, running python OCR instead.')
        ollama_running = False


    detected_comics: List[DetectedComic] = []
    for crop_image in crops:
        crop_id = uuid.uuid4().hex
        crop_filename = f"{crop_id}.jpg"
        crop_path = os.path.join(CROP_DIR, crop_filename)
        cv2.imwrite(crop_path, crop_image)

    # 3. for EACH detected comic: save its crop to disk, then OCR just that crop.

    #    If ollama is enabled, then use llm model to analyze the image. if not, use python ocr. 
        comicvine_id = None
        volume_name = None
        cover_image_url = None
        cover_date = None
        storyline = None
        characters = None

        if use_ollama and ollama_running:

            ollama_result = query_ollama_vision(crop_path)
            series_title = ollama_result.get('series_title')
            issue_number = ollama_result.get('issue_number')
            issue_number = str(issue_number) if issue_number is not None else None  # model sometimes returns a bare JSON number, not a string
            publisher = ollama_result.get('publisher')  # Ollama's own guess - overwritten below if ComicVine confirms a match
            creators = ollama_result.get('creators_visible')
            needs_manual = ollama_result.get('confidence') != 'high' or not series_title

            if not needs_manual and issue_number:
                # confident + has an issue number = try to resolve the exact ComicVine
                # issue now, so the frontend can prompt "save this?" without a second lookup.
                creator_hint = creators[0] if creators else None
                record = comicvine_client.fetch_issue(title=series_title, issue=str(issue_number), creator=creator_hint)

                if record is not None:
                    comicvine_id = record.comicvine_id
                    volume_name = record.volume_name
                    cover_image_url = record.cover_url
                    cover_date = record.cover_date
                    storyline = record.description
                    characters = ", ".join(c.name for c in record.characters) or None
                    creators = [c.name for c in record.creators] or creators

                    # 'volume' nested in the issue record only has id+name - fetch
                    volume_detail = comicvine_client.get_volume(record.volume_id) if record.volume_id else None
                    if volume_detail is not None:
                        publisher = normalize_publisher(volume_detail.publisher)
                else:
                    # ComicVine couldn't confirm it even though Ollama was confident,
                    # fall back to manual/candidate entry instead of a direct save prompt.
                    needs_manual = True
            else:
                # no issue number to resolve against needs manual handling.
                needs_manual = True

        else:
            # plain OCR gives raw cover text only.
            # Always needs the /search fuzzy-candidate step (or manual entry if OCR got nothing).
            series_title = ocr.extract_cover_text(crop_path)
            issue_number = None
            publisher = None
            creators = None
            needs_manual = series_title is None

        detected_comics.append(DetectedComic(
            crop_id=crop_id,
            crop_image_path=os.path.join("crops", crop_filename),
            series_title=series_title, # this one can either be an ollama series title OR a python ocr result.
            issue_number=issue_number,
            publisher=publisher,
            creators=creators,
            cover_date=cover_date,
            storyline=storyline,
            characters=characters,
            comicvine_id=comicvine_id,
            volume_name=volume_name,
            cover_image_url=cover_image_url,
            needs_manual_text=bool(needs_manual),
        ))

    return UploadResponse(
        uploaded_image_path=saved_name,
        # annotated_image_path=annotated_name,
        detected_comics=detected_comics,
    )


# ---------- Step 2: user confirms a candidate (from OCR/Ollama + ComicVine
# /search) or picks one directly by ComicVine id -> save it to the collection ----------

class AddComic(BaseModel):
    comicvine_id: int
    uploaded_image_path: Optional[str] = None


@app.post("/comics", status_code=201)
def add_comic(body: AddComic, db: Session = Depends(get_db)):
    record = comicvine_client.get_issue_detail(body.comicvine_id)
    if record is None:
        raise HTTPException(404, f"ComicVine issue {body.comicvine_id} not found")

    try:
        comic = save_comic(db, comicvine_client, record, uploaded_image_path=body.uploaded_image_path)
    except ValueError as e:
        # save_comic raises this when comicvine_id is already in the collection
        raise HTTPException(409, str(e))

    return _serialize(comic)


@app.delete("/comics/{comic_id}", status_code=204)
def remove_comic(comic_id: int, db: Session = Depends(get_db)):
    if not delete_comic(db, comic_id):
        raise HTTPException(404, "Comic not found")






# also allow adding a comic by hand, for covers OCR/ComicVine can't find
# TODO: not wired to an endpoint yet - needs its own repository.save_manual_comic()
# (no comicvine_id to key off of, so it can't reuse save_comic()'s get-or-create flow as-is).


class ManualComic(BaseModel):
    title: str
    series: Optional[str] = None
    issue_number: Optional[str] = None
    author: Optional[str] = None
    publisher: Optional[str] = None
    cover_date: Optional[str] = None
    storyline: Optional[str] = None
    characters: Optional[str] = None  # comma separated
    cover_image_url: Optional[str] = None


def _serialize(c: Comic):
    return {
        "id": c.id,
        "comicvine_id": c.comicvine_id,
        "collection_order": c.collection_order,
        "name": c.name,
        "issue_number": c.issue_number,
        "cover_date": c.cover_date,
        "store_date": c.store_date,
        "storyline": c.storyline,
        "cover_image_url": c.cover_image_url,
        "uploaded_image_path": c.uploaded_image_path,
        "date_purchased": c.date_purchased.isoformat() if c.date_purchased else None,
        "date_added": c.date_added.isoformat() if c.date_added else None,
        "volume": {
            "id": c.volume.id,
            "name": c.volume.name,
            "publisher": c.volume.publisher,
        } if c.volume else None,
        "creators": c.creator_names,
        "characters": c.character_names,
    }


# ---------- serve the frontend ----------
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
COMICS_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "comics_db")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/comics_db", StaticFiles(directory=COMICS_DB_DIR), name="comics_db")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")