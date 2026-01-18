"""Source server client for triage operations."""

import logging
from typing import Optional

from abs_sync.client.abs_client import ABSClient
from abs_sync.models import Book, Collection
from abs_sync.services.metadata import MetadataService

logger = logging.getLogger("abs_sync")


class SourceClient(ABSClient):
    """Client for source (triage) Audiobookshelf server."""

    def get_item(self, item_id: str) -> Optional[Book]:
        """
        Get a library item by ID.

        Args:
            item_id: The library item ID

        Returns:
            Book object or None
        """
        data = self._get(f"/api/items/{item_id}")
        if data:
            return MetadataService.extract_book_from_response(data)
        return None

    def get_collections(self, library_id: str) -> list[Collection]:
        """
        Get all collections for a library.

        Args:
            library_id: The library ID

        Returns:
            List of Collection objects
        """
        data = self._get(f"/api/libraries/{library_id}/collections")
        if not data:
            return []

        collections = []
        for col in data.get("results", []):
            collections.append(Collection(
                id=col.get("id", ""),
                library_id=col.get("libraryId", ""),
                name=col.get("name", ""),
                description=col.get("description"),
            ))
        return collections

    def get_collection(
        self, collection_id: str, library_id: Optional[str] = None
    ) -> Optional[Collection]:
        """
        Get a collection with its books.

        Args:
            collection_id: The collection ID
            library_id: Optional library ID to use as fallback if not in response

        Returns:
            Collection with books or None
        """
        data = self._get(f"/api/collections/{collection_id}")
        if not data:
            return None

        books = []
        for book_data in data.get("books", []):
            # Collection endpoint may return collapsed book data without full metadata.
            # Fetch each book individually to ensure we have complete metadata.
            book_id = book_data.get("id")
            if book_id:
                logger.debug(f"Fetching full metadata for book {book_id}")
                full_book = self.get_item(book_id)
                if full_book:
                    logger.debug(
                        f"Got metadata: title={full_book.metadata.title}, "
                        f"authors={full_book.metadata.authors}, "
                        f"narrators={full_book.metadata.narrators}"
                    )
                    books.append(full_book)
                else:
                    # Fall back to parsing the collection data if individual fetch fails
                    logger.debug(f"Failed to fetch book {book_id}, using collection data")
                    books.append(MetadataService.extract_book_from_response(book_data))
            else:
                books.append(MetadataService.extract_book_from_response(book_data))

        # Use libraryId from response, falling back to provided library_id
        resolved_library_id = data.get("libraryId") or library_id or ""

        return Collection(
            id=data.get("id", ""),
            library_id=resolved_library_id,
            name=data.get("name", ""),
            description=data.get("description"),
            books=books,
        )

    def find_collection_by_name(
        self, library_id: str, name: str
    ) -> Optional[Collection]:
        """
        Find a collection by name.

        Args:
            library_id: The library ID to search in
            name: Collection name to find

        Returns:
            Collection if found, None otherwise
        """
        collections = self.get_collections(library_id)
        for col in collections:
            if col.name.lower() == name.lower():
                return self.get_collection(col.id, library_id)
        return None

    def add_book_to_collection(self, collection_id: str, book_id: str) -> bool:
        """
        Add a book to a collection.

        Args:
            collection_id: The collection ID
            book_id: The book ID to add

        Returns:
            True if successful
        """
        result = self._post(
            f"/api/collections/{collection_id}/book",
            data={"id": book_id}
        )
        return result is not None

    def remove_book_from_collection(self, collection_id: str, book_id: str) -> bool:
        """
        Remove a book from a collection.

        Args:
            collection_id: The collection ID
            book_id: The book ID to remove

        Returns:
            True if successful
        """
        return self._delete(f"/api/collections/{collection_id}/book/{book_id}")

    def create_collection(
        self,
        library_id: str,
        name: str,
        description: str = "",
        book_ids: Optional[list[str]] = None,
    ) -> Optional[Collection]:
        """
        Create a new collection.

        Args:
            library_id: The library ID
            name: Collection name
            description: Optional description
            book_ids: List of book IDs to include (API requires at least one)

        Returns:
            Created Collection or None
        """
        payload = {
            "libraryId": library_id,
            "name": name,
            "description": description,
            "books": book_ids or [],
        }
        data = self._post("/api/collections", data=payload)
        if data:
            return Collection(
                id=data.get("id", ""),
                library_id=data.get("libraryId", library_id),
                name=data.get("name", name),
                description=data.get("description"),
            )
        return None

    def get_or_create_collection(
        self, library_id: str, name: str, book_ids: Optional[list[str]] = None
    ) -> tuple[Optional[Collection], bool]:
        """
        Get a collection by name, creating it if it doesn't exist.

        Args:
            library_id: The library ID
            name: Collection name
            book_ids: Book IDs to include when creating (API requires at least one)

        Returns:
            Tuple of (Collection or None, was_created bool)
        """
        collection = self.find_collection_by_name(library_id, name)
        if collection:
            return collection, False

        if not book_ids:
            logger.error(f"Cannot create collection '{name}': at least one book required")
            return None, False

        logger.info(f"Creating collection: {name}")
        created = self.create_collection(library_id, name, book_ids=book_ids)
        return created, created is not None
