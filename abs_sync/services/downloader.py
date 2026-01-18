"""Book download functionality."""

import logging
import shutil
import zipfile
from pathlib import Path
from typing import Optional

import requests

from abs_sync.models import Book
from abs_sync.services.sanitizer import sanitize_path_component

logger = logging.getLogger("abs_sync")


class BookDownloader:
    """Handles downloading audiobooks from the source server."""

    AUDIO_EXTENSIONS = {".mp3", ".m4a", ".m4b", ".ogg", ".wav", ".flac", ".opus"}
    CHUNK_SIZE = 8192

    def __init__(self, server_url: str, api_key: str, download_path: Path):
        """
        Initialize the downloader.

        Args:
            server_url: Base URL of the source server
            api_key: API key for authentication
            download_path: Base path for downloads
        """
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.download_path = download_path

    def get_book_folder_path(self, book: Book) -> Path:
        """
        Build the target folder path for a book.

        Format: DOWNLOAD_PATH/Author/Title/
        """
        # Get primary author name
        author = "Unknown Author"
        if book.metadata.authors:
            author = book.metadata.authors[0].get("name", "Unknown Author")

        # Sanitize components
        author_folder = sanitize_path_component(author)
        title_folder = sanitize_path_component(book.metadata.title)

        return self.download_path / author_folder / title_folder

    def book_exists(self, book: Book) -> bool:
        """Check if the book folder already exists."""
        folder = self.get_book_folder_path(book)
        return folder.exists()

    def download_book(self, book: Book) -> Optional[Path]:
        """
        Download a book's audio files.

        Downloads to a .partial folder first, then renames on success.

        Args:
            book: The book to download

        Returns:
            Path to the downloaded folder, or None on failure
        """
        target_folder = self.get_book_folder_path(book)
        partial_folder = target_folder.with_name(target_folder.name + ".partial")

        logger.info(f"Downloading: {book.metadata.title}")
        logger.debug(f"Target path: {target_folder}")

        try:
            # Clean up any existing partial download
            if partial_folder.exists():
                shutil.rmtree(partial_folder)

            # Create partial folder
            partial_folder.mkdir(parents=True, exist_ok=True)

            # Download the book files
            download_url = f"{self.server_url}/api/items/{book.id}/download"
            response = requests.get(
                download_url,
                params={"token": self.api_key},
                stream=True,
                timeout=600  # 10 min timeout for large files
            )
            response.raise_for_status()

            # Determine filename from content-disposition or content-type
            content_type = response.headers.get("Content-Type", "")
            filename = self._get_filename_from_response(response, book)

            download_file = partial_folder / filename

            # Stream download
            with open(download_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                    f.write(chunk)

            logger.debug(f"Downloaded file: {download_file}")

            # Handle ZIP files
            if content_type == "application/zip" or filename.endswith(".zip"):
                self._extract_zip(download_file, partial_folder)
                download_file.unlink()  # Remove the zip after extraction

            # Rename partial folder to final
            if target_folder.exists():
                shutil.rmtree(target_folder)
            partial_folder.rename(target_folder)

            logger.info(f"Successfully downloaded: {book.metadata.title}")
            return target_folder

        except requests.RequestException as e:
            logger.error(f"Download failed for {book.metadata.title}: {e}")
            self._cleanup_partial(partial_folder)
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading {book.metadata.title}: {e}")
            self._cleanup_partial(partial_folder)
            return None

    def download_cover(self, book: Book, target_folder: Path) -> Optional[Path]:
        """
        Download the book's cover image.

        Args:
            book: The book
            target_folder: Folder to save the cover in

        Returns:
            Path to the cover file, or None if no cover or download failed
        """
        if not book.cover_path:
            return None

        try:
            cover_url = f"{self.server_url}/api/items/{book.id}/cover"
            response = requests.get(
                cover_url,
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30
            )
            response.raise_for_status()

            # Determine extension from content-type
            content_type = response.headers.get("Content-Type", "image/jpeg")
            ext = ".jpg"
            if "png" in content_type:
                ext = ".png"
            elif "webp" in content_type:
                ext = ".webp"

            cover_path = target_folder / f"cover{ext}"
            with open(cover_path, "wb") as f:
                f.write(response.content)

            logger.debug(f"Downloaded cover: {cover_path}")
            return cover_path

        except requests.RequestException as e:
            logger.warning(f"Failed to download cover for {book.metadata.title}: {e}")
            return None

    def _get_filename_from_response(self, response: requests.Response, book: Book) -> str:
        """Extract filename from response headers or generate one."""
        # Try content-disposition header
        content_disp = response.headers.get("Content-Disposition", "")
        if "filename=" in content_disp:
            # Parse filename from header
            import re
            match = re.search(r'filename[^;=\n]*=(["\']?)([^"\'\n;]+)\1', content_disp)
            if match:
                return match.group(2)

        # Generate filename from content-type
        content_type = response.headers.get("Content-Type", "")
        ext = ".m4b"  # Default extension
        if "zip" in content_type:
            ext = ".zip"
        elif "mpeg" in content_type or "mp3" in content_type:
            ext = ".mp3"
        elif "ogg" in content_type:
            ext = ".ogg"
        elif "flac" in content_type:
            ext = ".flac"

        title = sanitize_path_component(book.metadata.title)
        return f"{title}{ext}"

    def _extract_zip(self, zip_path: Path, target_dir: Path) -> None:
        """Extract ZIP file contents."""
        logger.debug(f"Extracting ZIP: {zip_path}")
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target_dir)

    def _cleanup_partial(self, partial_folder: Path) -> None:
        """Clean up partial download folder on failure."""
        if partial_folder.exists():
            try:
                shutil.rmtree(partial_folder)
            except Exception as e:
                logger.warning(f"Failed to clean up partial folder: {e}")
