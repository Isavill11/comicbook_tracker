import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship

from backend.database import Base


def parse_issue_number(raw: Optional[str]) -> Optional[float]:
    """Pull the first numeric token out of a ComicVine issue_number string so
    issues sort correctly ('2' before '10'). '1AU' -> 1.0, 'Annual 1' -> 1.0,
    '1/2' or '½' -> None (no plain digit run to anchor on)."""
    if not raw:
        return None
    match = re.search(r'-?\d+(\.\d+)?', raw.strip())
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


# ---------- association tables ----------

comic_creators = Table(
    "comic_creators",
    Base.metadata,
    Column("comic_id", Integer, ForeignKey("comics.id"), primary_key=True),
    Column("creator_id", Integer, ForeignKey("creators.id"), primary_key=True),
    # ComicVine's person_credits role string, e.g. "writer, penciler" - kept
    # per (comic, creator) since the same person can have different roles
    # across issues.
    Column("role", String, nullable=True),
)

comic_characters = Table(
    "comic_characters",
    Base.metadata,
    Column("comic_id", Integer, ForeignKey("comics.id"), primary_key=True),
    Column("character_id", Integer, ForeignKey("characters.id"), primary_key=True),
)


class Volume(Base):
    """One row per comic series (ComicVine 'volume'), e.g. 'Absolute Batman'.
    Every owned issue in that series points at the same Volume row, which is
    what makes the DC-Infinite-style 'group by series' view a plain
    GROUP BY volume_id instead of fuzzy string matching on a series name."""

    __tablename__ = "volumes"

    id = Column(Integer, primary_key=True)
    comicvine_volume_id = Column(Integer, unique=True, index=True, nullable=True)
    name = Column(String, index=True, nullable=False)
    publisher = Column(String, nullable=True)
    start_year = Column(String, nullable=True)
    # ComicVine's own volume artwork (not any one issue's cover) - used as the
    # tile image on a "browse by volume" grid. Requires a separate /volume/{id}
    # call to populate since /issue's nested volume object only gives id+name.
    image_url = Column(String, nullable=True)

    comics = relationship("Comic", back_populates="volume")


class Creator(Base):
    __tablename__ = "creators"

    id = Column(Integer, primary_key=True)
    comicvine_id = Column(Integer, unique=True, index=True, nullable=True)
    name = Column(String, unique=True, index=True, nullable=False)

    comics = relationship("Comic", secondary=comic_creators, back_populates="creators")


class Character(Base):
    __tablename__ = "characters"

    id = Column(Integer, primary_key=True)
    comicvine_id = Column(Integer, unique=True, index=True, nullable=True)
    name = Column(String, unique=True, index=True, nullable=False)
    image_url = Column(String, nullable=True)

    comics = relationship("Comic", secondary=comic_characters, back_populates="characters")


class Comic(Base):
    __tablename__ = "comics"

    id = Column(Integer, primary_key=True, index=True)

    comicvine_id = Column(Integer, unique=True, index=True, nullable=True)
    volume_id = Column(Integer, ForeignKey("volumes.id"), index=True, nullable=True)

    name = Column(String, nullable=True)                # issue's own title, often blank
    issue_number = Column(String, nullable=True)          # kept as ComicVine's raw string
    issue_number_sort = Column(Float, nullable=True, index=True)  # derived, for ORDER BY

    cover_date = Column(String, index=True, nullable=True)   # printed cover date (YYYY-MM-DD)
    store_date = Column(String, index=True, nullable=True)   # actual on-sale date
    storyline = Column(Text, nullable=True)                  # description/deck

    cover_image_url = Column(String, nullable=True)
    uploaded_image_path = Column(String, nullable=True)

    # legacy manual-order tiebreaker ("order I got them" when date_purchased ties)
    collection_order = Column(Integer, index=True)
    date_purchased = Column(DateTime, index=True, default=lambda: datetime.now(timezone.utc))
    date_added = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    volume = relationship("Volume", back_populates="comics")
    creators = relationship("Creator", secondary=comic_creators, back_populates="comics")
    characters = relationship("Character", secondary=comic_characters, back_populates="comics")

    @property
    def creator_names(self) -> list[str]:
        return [c.name for c in self.creators]

    @property
    def character_names(self) -> list[str]:
        return [c.name for c in self.characters]
