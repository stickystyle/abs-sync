"""Metadata extraction and application services."""

import logging
from typing import Any, Optional

from abs_sync.models import AudioFile, Book, BookMetadata

logger = logging.getLogger("abs_sync")


class MetadataService:
    """Service for extracting and converting metadata."""

    @staticmethod
    def extract_book_from_response(data: dict[str, Any]) -> Book:
        """
        Extract a Book object from an API response.

        Args:
            data: Raw API response for a library item

        Returns:
            Book object with parsed metadata
        """
        media = data.get("media", {})
        metadata_raw = media.get("metadata", {})

        # Parse metadata
        metadata = BookMetadata(
            title=metadata_raw.get("title", "Unknown Title"),
            subtitle=metadata_raw.get("subtitle"),
            authors=metadata_raw.get("authors", []),
            narrators=metadata_raw.get("narrators", []),
            series=metadata_raw.get("series", []),
            description=metadata_raw.get("description"),
            publisher=metadata_raw.get("publisher"),
            published_year=metadata_raw.get("publishedYear"),
            language=metadata_raw.get("language"),
            genres=metadata_raw.get("genres", []),
            explicit=metadata_raw.get("explicit", False),
            asin=metadata_raw.get("asin"),
            isbn=metadata_raw.get("isbn"),
        )

        # Parse audio files
        audio_files = []
        for af in data.get("audioFiles", []):
            file_meta = af.get("metadata", {})
            audio_files.append(AudioFile(
                index=af.get("index", 0),
                ino=af.get("ino", ""),
                filename=file_meta.get("filename", ""),
                path=file_meta.get("path", ""),
                size=file_meta.get("size", 0),
                duration=af.get("duration", 0.0),
                format=af.get("format", ""),
                mime_type=af.get("mimeType", ""),
            ))

        return Book(
            id=data.get("id", ""),
            library_id=data.get("libraryId", ""),
            folder_path=data.get("path", ""),
            rel_path=data.get("relPath", ""),
            metadata=metadata,
            audio_files=audio_files,
            cover_path=media.get("coverPath"),
            duration=media.get("duration", 0.0),
            size=media.get("size", 0),
        )

    @staticmethod
    def metadata_to_api_payload(metadata: BookMetadata) -> dict[str, Any]:
        """
        Convert BookMetadata to API payload format for updating.

        Args:
            metadata: BookMetadata object

        Returns:
            Dictionary suitable for PATCH /api/items/{id}/media
        """
        payload: dict[str, Any] = {
            "metadata": {
                "title": metadata.title,
            }
        }

        meta = payload["metadata"]

        if metadata.subtitle:
            meta["subtitle"] = metadata.subtitle

        if metadata.authors:
            meta["authors"] = metadata.authors

        if metadata.narrators:
            meta["narrators"] = metadata.narrators

        if metadata.series:
            meta["series"] = metadata.series

        if metadata.description:
            meta["description"] = metadata.description

        if metadata.publisher:
            meta["publisher"] = metadata.publisher

        if metadata.published_year:
            meta["publishedYear"] = metadata.published_year

        if metadata.language:
            meta["language"] = metadata.language

        if metadata.genres:
            meta["genres"] = metadata.genres

        meta["explicit"] = metadata.explicit

        if metadata.asin:
            meta["asin"] = metadata.asin

        if metadata.isbn:
            meta["isbn"] = metadata.isbn

        return payload

    @staticmethod
    def find_book_by_folder(books: list[Book], folder_name: str) -> Optional[Book]:
        """
        Find a book by its folder name.

        Args:
            books: List of books to search
            folder_name: The folder name to match (e.g., "Author/Title")

        Returns:
            Matching Book or None
        """
        for book in books:
            if book.rel_path.endswith(folder_name) or folder_name in book.rel_path:
                return book
        return None
