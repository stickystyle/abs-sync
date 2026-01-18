from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AudioFile:
    """Represents an audio file in a book."""

    index: int
    ino: str
    filename: str
    path: str
    size: int
    duration: float
    format: str
    mime_type: str


@dataclass
class BookMetadata:
    """Metadata for an audiobook."""

    title: str
    subtitle: Optional[str] = None
    authors: list[dict] = field(default_factory=list)  # [{id, name}]
    narrators: list[str] = field(default_factory=list)
    series: list[dict] = field(default_factory=list)  # [{id, name, sequence}]
    description: Optional[str] = None
    publisher: Optional[str] = None
    published_year: Optional[str] = None
    language: Optional[str] = None
    genres: list[str] = field(default_factory=list)
    explicit: bool = False
    asin: Optional[str] = None
    isbn: Optional[str] = None


@dataclass
class Book:
    """Represents an audiobook from the server."""

    id: str
    library_id: str
    folder_path: str
    rel_path: str
    metadata: BookMetadata
    audio_files: list[AudioFile] = field(default_factory=list)
    cover_path: Optional[str] = None
    duration: float = 0.0
    size: int = 0


@dataclass
class Collection:
    """Represents a collection on the server."""

    id: str
    library_id: str
    name: str
    description: Optional[str] = None
    books: list[Book] = field(default_factory=list)


@dataclass
class SyncResult:
    """Result of a sync operation."""

    total_books: int = 0
    downloaded: int = 0
    skipped: int = 0
    failed: int = 0
    metadata_applied: int = 0
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Return True if at least one book was processed successfully."""
        return self.downloaded > 0 or self.skipped > 0
