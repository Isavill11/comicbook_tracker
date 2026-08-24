from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime, timezone
from backend.database import Base


class Comic(Base):
    __tablename__ = "comics"

    id = Column(Integer, primary_key=True, index=True)

    # collection_order is what drives the default homepage sort —
    # it's set to "next integer" at save time, i.e. the order you added them.
    collection_order = Column(Integer, index=True)

    comicvine_id = Column(String, nullable=True)
    title = Column(String, index=True)
    series = Column(String, index=True, nullable=True)
    issue_number = Column(String, nullable=True)
    author = Column(String, index=True, nullable=True)  # writer(s), comma separated
    publisher = Column(String, nullable=True)
    cover_date = Column(String, nullable=True)  # published date, as text (YYYY-MM-DD)
    storyline = Column(String, index=True, nullable=True)

    # comma-separated list of character names, e.g. "Batman,Catwoman"
    characters = Column(Text, nullable=True)

    cover_image_url = Column(String, nullable=True)
    # path to the photo the user actually uploaded, kept for reference
    uploaded_image_path = Column(String, nullable=True)

    date_added = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def character_list(self):
        return [c.strip() for c in (self.characters or "").split(",") if c.strip()]
