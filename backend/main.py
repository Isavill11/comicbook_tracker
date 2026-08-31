import os
import shutil
import uuid
from typing import Optional, List

import cv2
from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import Base, engine, get_db
# from backend.db_models import Comic
from backend.comics_sqlite import Comic
import backend.comicvine as comicvine
import backend.ocr as ocr
from backend.crop_comics import ComicCropper


Base.metadata.create_all(bind=engine)

DEFAULT_UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "uploads")
UPLOAD_DIR = os.environ.get("UPLOAD_DIR", DEFAULT_UPLOAD_DIR)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# crops get their own subfolder so they don't clutter/collide with raw uploads
CROP_DIR = os.path.join(UPLOAD_DIR, "crops")
os.makedirs(CROP_DIR, exist_ok=True)


app = FastAPI(title="Comic Tracker")

comic_cropper = ComicCropper(r'backend\ML\runs\obb\train-6\weights\best.pt', confidence_level=0.85)


# ---------- step 1: upload a photo, detect comic book instances and crop necessary images ----------

class DetectedComic(BaseModel):
    crop_id: str
    crop_image_path: str          # relative path frontend can use to display the cropped cover
    ocr_query: Optional[str]      # None if OCR couldn't read anything usable
    needs_manual_text: bool       # True -> frontend should let user type/correct the title text


class UploadResponse(BaseModel):
    uploaded_image_path: str
    annotated_image_path: str     # full image w/ bounding boxes drawn, useful for the user to sanity check detection
    detected_comics: List[DetectedComic]


@app.post("/upload", response_model=UploadResponse)
def upload_cover(file: UploadFile = File(...)):
    # 1. save the raw upload
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_name)

    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # 2. run detection/cropping -> assumes crops is a list of cv2 (numpy) images,
    #    one per detected comic, and annotated_cv2drawn_image is the full image w/ boxes drawn.
    #    If crop_comics instead returns file paths or PIL images, only this block needs to change.
    crops, annotated_cv2drawn_image = comic_cropper.crop_comics(saved_path)

    if not crops:
        raise HTTPException(
            400,
            "No comics detected in that image — try a clearer photo with the covers fully visible."
        )

    annotated_name = f"{uuid.uuid4().hex}_annotated.jpg"
    annotated_path = os.path.join(UPLOAD_DIR, annotated_name)
    cv2.imwrite(annotated_path, annotated_cv2drawn_image)

    # 3. for EACH detected comic: save its crop to disk, then OCR just that crop
    detected_comics: List[DetectedComic] = []
    for crop_image in crops:
        crop_id = uuid.uuid4().hex
        crop_filename = f"{crop_id}.jpg"
        crop_path = os.path.join(CROP_DIR, crop_filename)
        cv2.imwrite(crop_path, crop_image)

        # ocr.extract_cover_text takes a path, so we pass the crop's saved path.
        # Returns a joined string of recognized words, or None if nothing usable was found.
        query_text = ocr.extract_cover_text(crop_path)

        detected_comics.append(DetectedComic(
            crop_id=crop_id,
            crop_image_path=os.path.join("crops", crop_filename),
            ocr_query=query_text,
            needs_manual_text=query_text is None,
        ))

    return UploadResponse(
        uploaded_image_path=saved_name,
        annotated_image_path=annotated_name,
        detected_comics=detected_comics,
    )


# ---------- Step 2 (next up): match OCR'd text against known series list, let user confirm,
# then fetch issue number / send to Comic Vine. Not wired up yet -- picking this up after
# the cropping step above is confirmed working end-to-end. ----------

class ConfirmMatch(BaseModel):
    comicvine_id: str
    uploaded_image_path: Optional[str] = None


@app.post("/confirm")
async def confirm_and_save(body: ConfirmMatch, db: Session = Depends(get_db)):
    detail = await comicvine.get_issue_detail(body.comicvine_id)

    next_order = (db.query(func.max(Comic.collection_order)).scalar() or 0) + 1

    comic = Comic(
        collection_order=next_order,
        comicvine_id=detail["comicvine_id"],
        title=detail["title"],
        series=detail["series"],
        issue_number=detail["issue_number"],
        author=detail["author"],
        publisher=detail["publisher"],
        cover_date=detail["cover_date"],
        storyline=detail["storyline"],
        characters=detail["characters"],
        cover_image_url=detail["cover_image_url"],
        uploaded_image_path=body.uploaded_image_path,
    )
    db.add(comic)
    db.commit()
    db.refresh(comic)
    return _serialize(comic)


# also allow adding a comic by hand, for covers OCR/ComicVine can't find
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
        "collection_order": c.collection_order,
        "title": c.title,
        "series": c.series,
        "issue_number": c.issue_number,
        "author": c.author,
        "publisher": c.publisher,
        "cover_date": c.cover_date,
        "storyline": c.storyline,
        "characters": c.character_list(),
        "cover_image_url": c.cover_image_url,
    }


# ---------- serve the frontend ----------
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
COMICS_DB_DIR = os.path.join(os.path.dirname(__file__), "..", "comics_db")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/comics_db", StaticFiles(directory=COMICS_DB_DIR), name="comics_db")
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")