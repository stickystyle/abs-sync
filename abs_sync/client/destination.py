"""Destination server client for main library operations."""

import logging
import time
from typing import Optional

from abs_sync.client.abs_client import ABSClient
from abs_sync.models import Book
from abs_sync.services.metadata import MetadataService

logger = logging.getLogger("abs_sync")


class DestinationClient(ABSClient):
    """Client for destination (main) Audiobookshelf server."""

    SCAN_POLL_INTERVAL = 5  # seconds
    SCAN_MAX_WAIT = 300  # 5 minutes

    def __init__(self, server_url: str, api_key: str, library_id: str):
        """
        Initialize the destination client.

        Args:
            server_url: Base URL of the ABS server
            api_key: API key for authentication
            library_id: Target library ID
        """
        super().__init__(server_url, api_key)
        self.library_id = library_id

    def get_library_items(self) -> list[Book]:
        """
        Get all items in the library.

        Returns:
            List of Book objects
        """
        data = self._get(f"/api/libraries/{self.library_id}/items")
        if not data:
            return []

        books = []
        for item in data.get("results", []):
            books.append(MetadataService.extract_book_from_response(item))
        return books

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

    def trigger_scan(self) -> bool:
        """
        Trigger a library scan.

        Returns:
            True if scan was triggered successfully
        """
        logger.info("Triggering library scan...")
        result = self._post(f"/api/libraries/{self.library_id}/scan")
        return result is not None

    def is_scanning(self) -> bool:
        """
        Check if the library is currently scanning.

        Returns:
            True if a scan is in progress
        """
        data = self._get(f"/api/libraries/{self.library_id}")
        if data:
            # Check various scan status indicators
            return data.get("scanning", False)
        return False

    def wait_for_scan(self) -> bool:
        """
        Wait for any ongoing scan to complete.

        Returns:
            True if scan completed, False if timed out
        """
        start_time = time.time()

        while time.time() - start_time < self.SCAN_MAX_WAIT:
            if not self.is_scanning():
                logger.info("Library scan complete")
                return True

            logger.debug("Waiting for scan to complete...")
            time.sleep(self.SCAN_POLL_INTERVAL)

        logger.warning("Timed out waiting for scan to complete")
        return False

    def scan_and_wait(self) -> bool:
        """
        Trigger a scan and wait for completion.

        Returns:
            True if scan completed successfully
        """
        if not self.trigger_scan():
            return False

        # Give scan a moment to start
        time.sleep(2)

        return self.wait_for_scan()

    def update_metadata(self, item_id: str, payload: dict) -> bool:
        """
        Update an item's metadata.

        Args:
            item_id: The library item ID
            payload: Metadata payload from MetadataService.metadata_to_api_payload()

        Returns:
            True if successful
        """
        logger.debug(f"Updating metadata for item {item_id}")
        result = self._patch(f"/api/items/{item_id}/media", data=payload)
        if result is None:
            logger.debug(f"Metadata update failed for {item_id}")
        return result is not None

    def find_book_by_path(self, rel_path: str) -> Optional[Book]:
        """
        Find a book by its relative path.

        Args:
            rel_path: Relative path (e.g., "Author/Title")

        Returns:
            Book if found, None otherwise
        """
        books = self.get_library_items()
        for book in books:
            # Check if path matches (handle different path separators)
            if book.rel_path == rel_path or book.rel_path.replace("\\", "/") == rel_path:
                return book
            # Also check if the path ends with our rel_path
            if book.rel_path.endswith(rel_path):
                return book
        return None
