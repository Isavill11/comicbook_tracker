import os
import shutil
import uuid
from typing import Optional, List

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import Base, engine, get_db
from models import Comic
import comicvine
import ocr

Base.metadata.create_all(bind=engine)

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", "/app/data/uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(title="Comic Tracker")


# ---------- Step 1: upload a photo, get back candidate matches ----------

@app.post("/api/upload")
async def upload_cover(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1] or ".jpg"
    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_name)
    with open(saved_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    query_text = ocr.extract_cover_text(saved_path)
    if not query_text:
        raise HTTPException(400, "Couldn't read any text off that cover — try a clearer, straight-on photo.")

    candidates = await comicvine.search_issues(query_text)
    return {
        "uploaded_image_path": saved_name,
        "ocr_query": query_text,
        "candidates": candidates,
    }


# ---------- Step 2: user picks a candidate, we save it to the collection ----------

class ConfirmMatch(BaseModel):
    comicvine_id: str
    uploaded_image_path: Optional[str] = None


@app.post("/api/comics")
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


@app.post("/api/comics/manual")
def add_manual(body: ManualComic, db: Session = Depends(get_db)):
    next_order = (db.query(func.max(Comic.collection_order)).scalar() or 0) + 1
    comic = Comic(collection_order=next_order, **body.model_dump())
    db.add(comic)
    db.commit()
    db.refresh(comic)
    return _serialize(comic)


# ---------- Homepage listing, with filters ----------

@app.get("/api/comics")
def list_comics(
    character: Optional[str] = None,
    series: Optional[str] = None,
    author: Optional[str] = None,
    storyline: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Comic)
    if series:
        q = q.filter(Comic.series == series)
    if author:
        q = q.filter(Comic.author.ilike(f"%{author}%"))
    if storyline:
        q = q.filter(Comic.storyline.ilike(f"%{storyline}%"))
    if date_from:
        q = q.filter(Comic.cover_date >= date_from)
    if date_to:
        q = q.filter(Comic.cover_date <= date_to)
    if character:
        q = q.filter(Comic.characters.ilike(f"%{character}%"))

    comics = q.order_by(Comic.collection_order.asc()).all()
    return [_serialize(c) for c in comics]


# ---------- Character avatar bar ----------

@app.get("/api/characters")
def list_characters(db: Session = Depends(get_db)):
    comics = db.query(Comic).all()
    counts = {}
    covers = {}
    for c in comics:
        for name in c.character_list():
            counts[name] = counts.get(name, 0) + 1
            covers.setdefault(name, c.cover_image_url)
    return [
        {"name": name, "count": counts[name], "image_url": covers[name]}
        for name in sorted(counts, key=lambda n: -counts[n])
    ]


# ---------- distinct filter option lists (series/authors/storylines) ----------

@app.get("/api/filters")
def filter_options(db: Session = Depends(get_db)):
    comics = db.query(Comic).all()
    return {
        "series": sorted({c.series for c in comics if c.series}),
        "authors": sorted({a.strip() for c in comics if c.author for a in c.author.split(",") if a.strip()}),
        "storylines": sorted({c.storyline for c in comics if c.storyline}),
    }


@app.get("/api/uploads/{filename}")
def serve_upload(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(404)
    return FileResponse(path)


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
app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
