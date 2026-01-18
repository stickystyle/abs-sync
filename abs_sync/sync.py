"""Sync orchestration logic."""

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from abs_sync.client.destination import DestinationClient
from abs_sync.client.source import SourceClient
from abs_sync.config import Config
from abs_sync.models import Book, Collection, SyncResult
from abs_sync.services.downloader import BookDownloader
from abs_sync.services.metadata import MetadataService

logger = logging.getLogger("abs_sync")


@dataclass
class DownloadedBook:
    """Tracks a downloaded book for metadata application."""
    source_book: Book
    local_path: Path
    rel_path: str  # Author/Title format


class SyncOrchestrator:
    """Orchestrates the sync workflow between source and destination servers."""

    def __init__(self, config: Config, dry_run: bool = False):
        """
        Initialize the orchestrator.

        Args:
            config: Application configuration
            dry_run: If True, don't actually download/modify anything
        """
        self.config = config
        self.dry_run = dry_run

        # Initialize clients
        self.source = SourceClient(config.source_url, config.source_api_key)
        self.dest = DestinationClient(
            config.dest_url, config.dest_api_key, config.dest_library_id
        )

        # Initialize downloader
        self.downloader = BookDownloader(
            config.source_url, config.source_api_key, config.download_path
        )

    def validate_connections(self) -> bool:
        """
        Validate connections to both servers.

        Returns:
            True if both servers are reachable
        """
        logger.info("Validating server connections...")

        if not self.source.ping():
            logger.error("Failed to connect to source server")
            return False
        logger.info("Source server: OK")

        if not self.dest.ping():
            logger.error("Failed to connect to destination server")
            return False
        logger.info("Destination server: OK")

        return True

    def run(self) -> SyncResult:
        """
        Execute the sync workflow.

        Returns:
            SyncResult with operation statistics
        """
        result = SyncResult()

        # Step 1: Validate connections
        if not self.validate_connections():
            result.errors.append("Failed to connect to servers")
            return result

        # Step 2: Find the Download collection on source
        download_collection = self._find_download_collection()
        if not download_collection:
            result.errors.append(
                f"Collection '{self.config.source_collection_name}' not found"
            )
            return result

        if not download_collection.books:
            logger.info("No books in Download collection - nothing to sync")
            return result

        result.total_books = len(download_collection.books)
        logger.info(f"Found {result.total_books} books to sync")

        if self.dry_run:
            self._dry_run_report(download_collection)
            return result

        # Step 3: Download books
        downloaded: list[DownloadedBook] = []

        for book in download_collection.books:
            download_result = self._download_book(book)
            if download_result:
                if download_result == "skipped":
                    result.skipped += 1
                else:
                    result.downloaded += 1
                    downloaded.append(download_result)
            else:
                result.failed += 1
                result.errors.append(f"Failed to download: {book.metadata.title}")

        if not downloaded and result.skipped == 0:
            logger.error("All downloads failed")
            return result

        # Step 4: Trigger library scan on destination
        if downloaded:
            logger.info("Triggering library scan on destination...")
            if not self.dest.scan_and_wait():
                logger.warning("Scan may not have completed fully")

        # Step 5: Apply metadata
        for dl_book in downloaded:
            if self._apply_metadata(dl_book):
                result.metadata_applied += 1
            else:
                result.errors.append(
                    f"Failed to apply metadata: {dl_book.source_book.metadata.title}"
                )

        # Step 6: Move books to Synced collection
        book_ids = [book.id for book in download_collection.books]
        synced_collection, was_created = self._get_or_create_synced_collection(
            download_collection.library_id, book_ids
        )
        if synced_collection:
            # If collection was just created, books were added during creation
            self._move_to_synced(download_collection, synced_collection, already_added=was_created)

        return result

    def _find_download_collection(self) -> Optional[Collection]:
        """Find the Download collection on the source server."""
        # First we need to find what library the collection is in
        # Try to get the collection from any library

        # Get all libraries from source
        data = self.source._get("/api/libraries")
        if not data:
            return None

        libraries = data.get("libraries", [])

        for lib in libraries:
            lib_id = lib.get("id", "")
            collection = self.source.find_collection_by_name(
                lib_id, self.config.source_collection_name
            )
            if collection:
                return collection

        return None

    def _download_book(self, book: Book) -> Optional[DownloadedBook | str]:
        """
        Download a single book.

        Returns:
            DownloadedBook on success, "skipped" if already exists, None on failure
        """
        # Check if already downloaded
        if self.downloader.book_exists(book):
            logger.info(f"Skipping (already exists): {book.metadata.title}")
            return "skipped"

        # Download the book
        local_path = self.downloader.download_book(book)
        if not local_path:
            return None

        # Download cover
        self.downloader.download_cover(book, local_path)

        # Build rel_path for later matching
        rel_path = str(local_path.relative_to(self.config.download_path))

        return DownloadedBook(
            source_book=book,
            local_path=local_path,
            rel_path=rel_path,
        )

    def _apply_metadata(self, dl_book: DownloadedBook) -> bool:
        """Apply metadata from source book to destination."""
        logger.info(f"Applying metadata: {dl_book.source_book.metadata.title}")

        # Find the book in destination by path
        logger.debug(f"Looking for book in destination with path: {dl_book.rel_path}")
        dest_book = self.dest.find_book_by_path(dl_book.rel_path)
        if not dest_book:
            logger.warning(
                f"Could not find book in destination: {dl_book.rel_path}"
            )
            return False

        logger.debug(f"Found destination book: {dest_book.id}")

        # Build and apply metadata payload
        payload = MetadataService.metadata_to_api_payload(
            dl_book.source_book.metadata
        )
        logger.debug(f"Metadata payload: {payload}")

        success = self.dest.update_metadata(dest_book.id, payload)
        if success:
            logger.debug(f"Successfully applied metadata to {dest_book.id}")
        else:
            logger.warning(f"Failed to apply metadata to {dest_book.id}")
        return success

    def _get_or_create_synced_collection(
        self, library_id: str, book_ids: list[str]
    ) -> tuple[Optional[Collection], bool]:
        """Get or create the Synced collection.

        Returns:
            Tuple of (Collection or None, was_created bool)
        """
        return self.source.get_or_create_collection(
            library_id, self.config.synced_collection_name, book_ids=book_ids
        )

    def _move_to_synced(
        self,
        download_col: Collection,
        synced_col: Collection,
        already_added: bool = False,
    ) -> None:
        """Move all processed books from Download to Synced collection.

        Args:
            download_col: Source collection to move from
            synced_col: Destination collection to move to
            already_added: If True, books were already added when creating synced_col
        """
        logger.info("Moving books to Synced collection...")

        for book in download_col.books:
            # Add to Synced (skip if already added during creation)
            if already_added or self.source.add_book_to_collection(synced_col.id, book.id):
                # Remove from Download
                self.source.remove_book_from_collection(download_col.id, book.id)
                logger.debug(f"Moved to Synced: {book.metadata.title}")
            else:
                logger.warning(f"Failed to move: {book.metadata.title}")

    def _dry_run_report(self, collection: Collection) -> None:
        """Print dry run report."""
        logger.info("\n--- DRY RUN REPORT ---")
        logger.info(f"Would sync {len(collection.books)} books:\n")

        for book in collection.books:
            target_path = self.downloader.get_book_folder_path(book)
            exists = target_path.exists()
            status = "SKIP (exists)" if exists else "DOWNLOAD"

            author = "Unknown"
            if book.metadata.authors:
                author = book.metadata.authors[0].get("name", "Unknown")

            logger.info(f"  [{status}] {author} - {book.metadata.title}")
            logger.info(f"           -> {target_path}")

        logger.info("\n--- END DRY RUN ---")
