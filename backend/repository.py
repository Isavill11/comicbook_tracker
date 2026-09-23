"""
Turns normalized ComicVine data (backend/comicvine.py's dataclasses) into
saved rows in the schema (backend/comics_sqlite.py), wiring up the
Volume/Creator/Character relationships along the way.

This is the only place that should construct/attach Volume, Creator, or
Character rows from ComicVine data - main.py's endpoints should just call
save_comic() / delete_comic() and stay ignorant of the get-or-create details.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend import comicvine
from backend.comics_sqlite import Comic, Volume, Creator, Character, parse_issue_number, normalize_publisher


# ---------- get-or-create ----------

def get_or_create_volume(db: Session, client: comicvine.ComicVineClient, record: comicvine.ComicIssueRecord,) -> Optional[Volume]:
    """Get the Volume row for this issue's series, fetching+creating it the
    first time this volume_id is ever seen. Every later issue from the same
    series reuses this same row - this is what makes owned issues from split
    runs (e.g. #1-5 and #16-18) group together under one series."""

    if record.volume_id is None:
        return None

    volume = db.query(Volume).filter_by(comicvine_volume_id=record.volume_id).one_or_none()
    if volume is not None:
        return volume

    # New volume - one extra call to get publisher/start_year/artwork, since
    # the 'volume' stub nested in the issue record only has id+name.
    detail = client.get_volume(record.volume_id)
    volume = Volume(
        comicvine_volume_id=record.volume_id,
        name=(detail.name if detail else record.volume_name) or "Unknown series",
        publisher=normalize_publisher(detail.publisher) if detail else None,
        start_year=detail.start_year if detail else None,
        image_url=detail.image_url if detail else None,
    )
    db.add(volume)
    db.flush()  # populate volume.id before the Comic row references it
    return volume


def get_or_create_creator(db: Session, creator: comicvine.Creator) -> Creator:
    """Match by ComicVine id first (the reliable case); fall back to name
    for anything without one (e.g. a manual entry with no ComicVine id)."""

    row = None
    if creator.comicvine_id is not None:
        row = db.query(Creator).filter_by(comicvine_id=creator.comicvine_id).one_or_none()
    if row is None and creator.name:
        row = db.query(Creator).filter_by(name=creator.name).one_or_none()
    if row is not None:
        return row

    row = Creator(comicvine_id=creator.comicvine_id, name=creator.name)
    db.add(row)
    db.flush()
    return row


def get_or_create_character(db: Session, character: comicvine.Character) -> Character:
    row = None
    if character.comicvine_id is not None:
        row = db.query(Character).filter_by(comicvine_id=character.comicvine_id).one_or_none()
    if row is None and character.name:
        row = db.query(Character).filter_by(name=character.name).one_or_none()
    if row is not None:
        return row

    row = Character(comicvine_id=character.comicvine_id, name=character.name)
    db.add(row)
    db.flush()
    return row


def _dedupe(rows: list) -> list:
    """Defensive: if the same creator/character somehow appears twice in one
    record, get_or_create_* returns the SAME row object both times - without
    this, assigning it into the relationship list twice queues two INSERTs
    for the same (comic_id, x_id) composite key and blows up on the second."""
    seen = set()
    result = []
    for row in rows:
        if row not in seen:
            seen.add(row)
            result.append(row)
    return result


# ---------- comic CRUD ----------

def save_comic( db: Session, client: comicvine.ComicVineClient, record: comicvine.ComicIssueRecord, *, uploaded_image_path: Optional[str] = None,
    date_purchased: Optional[datetime] = None,
) -> Comic:
    """Save one confirmed ComicVine issue as a Comic row, creating/reusing its
    Volume/Creator/Character relationships. Call this with the full record
    from client.get_issue_detail(comicvine_id) - not a bare /search hit,
    which is missing credits/characters."""

    if record.comicvine_id is not None:
        existing = db.query(Comic).filter_by(comicvine_id=record.comicvine_id).one_or_none()
        if existing is not None:
            raise ValueError(
                f"Issue {record.comicvine_id} is already in your collection (comic id {existing.id})"
            )

    volume = get_or_create_volume(db, client, record)
    next_order = (db.query(func.max(Comic.collection_order)).scalar() or 0) + 1

    comic = Comic(
        comicvine_id=record.comicvine_id,
        volume_id=volume.id if volume else None,
        name=record.name,
        issue_number=record.issue_number,
        issue_number_sort=parse_issue_number(record.issue_number),
        cover_date=record.cover_date,
        store_date=record.store_date,
        storyline=record.description,
        cover_image_url=record.cover_url,
        uploaded_image_path=uploaded_image_path,
        collection_order=next_order,
        date_purchased=date_purchased or datetime.now(timezone.utc),
    )

    db.add(comic)
    # comic must already be pending in the session before these relationship
    # assignments - get_or_create_*'s queries trigger autoflush, and SQLAlchemy
    # warns (and won't attach the association) if comic isn't tracked yet.
    comic.creators = _dedupe([get_or_create_creator(db, c) for c in record.creators])
    comic.characters = _dedupe([get_or_create_character(db, c) for c in record.characters])

    db.commit()
    db.refresh(comic)
    return comic


def delete_comic(db: Session, comic_id: int) -> bool:
    """Deletes the Comic row."""

    comic = db.get(Comic, comic_id)
    if comic is None:
        return False
    db.delete(comic)
    db.commit()
    return True
