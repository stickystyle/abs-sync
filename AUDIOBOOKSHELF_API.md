# Audiobookshelf API Documentation

This document describes the Audiobookshelf server API endpoints used for client development. These endpoints have been tested and validated against Audiobookshelf server implementations.

## Table of Contents

- [Authentication](#authentication)
- [Base URL Configuration](#base-url-configuration)
- [API Endpoints](#api-endpoints)
  - [Get Item Details](#get-item-details)
  - [Download Audio File](#download-audio-file)
  - [Update Chapters](#update-chapters)
- [Data Structures](#data-structures)
- [Error Handling](#error-handling)
- [Implementation Examples](#implementation-examples)

---

## Authentication

Audiobookshelf uses **API Key** authentication. The API key can be obtained from the Audiobookshelf web interface under **Settings > Users > [Your User] > API Token**.

### Authentication Methods

| Method | Usage | Example |
|--------|-------|---------|
| Bearer Token Header | Most API calls | `Authorization: Bearer {api_key}` |
| Query Parameter | Download endpoints | `?token={api_key}` |

### Header Example

```http
GET /api/items/{item_id} HTTP/1.1
Host: your-abs-server.com
Authorization: Bearer your_api_key_here
```

---

## Base URL Configuration

The server URL should be stored **without** a trailing slash:

```
https://your-audiobookshelf-server.com
```

Full endpoint URLs are constructed as:

```
{server_url}/api/items/{item_id}
```

---

## API Endpoints

### Get Item Details

Retrieves detailed information about a library item, including metadata, audio files, and chapters.

#### Request

```http
GET /api/items/{item_id}
```

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `item_id` | string | Path | Yes | The unique identifier of the library item |

#### Headers

| Header | Value | Required |
|--------|-------|----------|
| `Authorization` | `Bearer {api_key}` | Yes |

#### Response

**Status Code:** `200 OK`

```json
{
  "id": "li_abc123def456",
  "ino": "12345678",
  "libraryId": "lib_xyz789",
  "folderId": "fol_abc123",
  "path": "/audiobooks/Author Name/Book Title",
  "relPath": "Author Name/Book Title",
  "isFile": false,
  "mtimeMs": 1704067200000,
  "ctimeMs": 1704067200000,
  "birthtimeMs": 1704067200000,
  "addedAt": 1704067200000,
  "updatedAt": 1704153600000,
  "isMissing": false,
  "isInvalid": false,
  "mediaType": "book",
  "media": {
    "metadata": {
      "title": "Book Title",
      "subtitle": null,
      "authors": [
        {
          "id": "auth_123",
          "name": "Author Name"
        }
      ],
      "narrators": ["Narrator Name"],
      "series": [],
      "genres": ["Fiction", "Mystery"],
      "publishedYear": "2023",
      "publishedDate": null,
      "publisher": "Publisher Name",
      "description": "Book description text...",
      "isbn": "978-1234567890",
      "asin": "B0ABC123DE",
      "language": "English",
      "explicit": false
    },
    "coverPath": "/audiobooks/Author Name/Book Title/cover.jpg",
    "chapters": [
      {
        "id": 0,
        "start": 0,
        "end": 1234.567,
        "title": "Chapter 1"
      },
      {
        "id": 1,
        "start": 1234.567,
        "end": 2468.123,
        "title": "Chapter 2"
      }
    ],
    "duration": 36000.5,
    "size": 576000000
  },
  "audioFiles": [
    {
      "index": 0,
      "ino": "87654321",
      "metadata": {
        "filename": "book.m4b",
        "ext": ".m4b",
        "path": "/audiobooks/Author Name/Book Title/book.m4b",
        "relPath": "book.m4b",
        "size": 576000000,
        "mtimeMs": 1704067200000,
        "ctimeMs": 1704067200000,
        "birthtimeMs": 1704067200000
      },
      "addedAt": 1704067200000,
      "updatedAt": 1704067200000,
      "format": "M4B",
      "duration": 36000.5,
      "bitRate": 128000,
      "codec": "aac",
      "channels": 2,
      "mimeType": "audio/mp4"
    }
  ]
}
```

#### Key Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique library item identifier (prefixed with `li_`) |
| `mediaType` | string | Type of media: `"book"` or `"podcast"` |
| `media.chapters` | array | Array of chapter objects |
| `media.chapters[].id` | integer | Chapter index/identifier |
| `media.chapters[].start` | float | Start time in seconds |
| `media.chapters[].end` | float | End time in seconds |
| `media.chapters[].title` | string | Chapter title |
| `audioFiles` | array | Array of audio file objects |
| `audioFiles[].ino` | string | Inode number (unique file identifier) |

---

### Download Audio File

Downloads the complete audio content for an item. Returns either a single audio file or a ZIP archive containing multiple files.

#### Request

```http
GET /api/items/{item_id}/download?token={api_key}
```

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `item_id` | string | Path | Yes | The unique identifier of the library item |
| `token` | string | Query | Yes | API key for authentication |

> **Note:** This endpoint uses query parameter authentication instead of the Authorization header.

#### Response Headers

| Header | Description |
|--------|-------------|
| `Content-Type` | File MIME type (see below) |
| `Content-Length` | File size in bytes (may be absent) |
| `Content-Disposition` | Suggested filename |

#### Content Types

| Content-Type | Description | Handling |
|--------------|-------------|----------|
| `audio/mpeg` | MP3 audio file | Save directly |
| `audio/mp4` | M4B/M4A audio file | Save directly |
| `audio/ogg` | OGG audio file | Save directly |
| `audio/wav` | WAV audio file | Save directly |
| `audio/flac` | FLAC audio file | Save directly |
| `audio/opus` | Opus audio file | Save directly |
| `application/zip` | ZIP archive with multiple files | Extract and process |

#### ZIP Archive Handling

When a ZIP file is returned:

1. Extract to a temporary directory
2. Search for audio files with extensions: `.mp3`, `.m4a`, `.m4b`, `.ogg`, `.wav`, `.flac`, `.opus`
3. If single audio file: use directly
4. If multiple audio files: concatenate in alphabetical order using ffmpeg
5. Clean up temporary files after processing

#### Example Request (Python)

```python
import requests

response = requests.get(
    f"{server_url}/api/items/{item_id}/download",
    params={"token": api_key},
    stream=True,
    timeout=30
)

# Handle streaming download
with open(output_path, 'wb') as f:
    for chunk in response.iter_content(chunk_size=8192):
        f.write(chunk)
```

---

### Update Chapters

Updates chapter information for a library item. This replaces all chapters with the provided list.

#### Request

```http
POST /api/items/{item_id}/chapters
```

| Parameter | Type | Location | Required | Description |
|-----------|------|----------|----------|-------------|
| `item_id` | string | Path | Yes | The unique identifier of the library item |

#### Headers

| Header | Value | Required |
|--------|-------|----------|
| `Authorization` | `Bearer {api_key}` | Yes |
| `Content-Type` | `application/json` | Yes |

#### Request Body

```json
{
  "chapters": [
    {
      "id": 0,
      "start": 0,
      "end": 1234.567,
      "title": "Chapter 1"
    },
    {
      "id": 1,
      "start": 1234.567,
      "end": 2468.123,
      "title": "Chapter 2"
    },
    {
      "id": 2,
      "start": 2468.123,
      "end": 3600.0,
      "title": "Chapter 3"
    }
  ]
}
```

#### Chapter Object Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | integer | Yes | Chapter identifier (typically sequential starting from 0) |
| `start` | float | Yes | Start time in seconds |
| `end` | float | Yes | End time in seconds |
| `title` | string | Yes | Chapter title |

#### Important Notes

1. **Complete Replacement**: The chapters array replaces ALL existing chapters
2. **End Time Calculation**: Each chapter's `end` should equal the next chapter's `start`
3. **Sorting**: Chapters should be sorted by `start` time
4. **Last Chapter**: The last chapter's `end` time should equal the total audio duration

#### Response

**Status Code:** `200 OK`

```json
{
  "success": true,
  "libraryItem": {
    // Full library item object with updated chapters
  }
}
```

#### Example Request (Python)

```python
import requests

payload = {
    "chapters": [
        {"id": 0, "start": 0, "end": 1234.567, "title": "Chapter 1"},
        {"id": 1, "start": 1234.567, "end": 2468.123, "title": "Chapter 2"},
        {"id": 2, "start": 2468.123, "end": 3600.0, "title": "Chapter 3"}
    ]
}

response = requests.post(
    f"{server_url}/api/items/{item_id}/chapters",
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    },
    json=payload,
    timeout=30
)
```

---

## Data Structures

### Library Item

```typescript
interface LibraryItem {
  id: string;              // Prefixed with "li_"
  ino: string;             // Inode number
  libraryId: string;       // Parent library ID
  folderId: string;        // Folder ID
  path: string;            // Absolute path on server
  relPath: string;         // Relative path in library
  isFile: boolean;         // Is single file
  mediaType: "book" | "podcast";
  media: BookMedia | PodcastMedia;
  audioFiles: AudioFile[];
  addedAt: number;         // Unix timestamp (ms)
  updatedAt: number;       // Unix timestamp (ms)
}
```

### Book Media

```typescript
interface BookMedia {
  metadata: BookMetadata;
  coverPath: string | null;
  chapters: Chapter[];
  duration: number;        // Total duration in seconds
  size: number;            // Total size in bytes
}
```

### Chapter

```typescript
interface Chapter {
  id: number;              // Sequential chapter index
  start: number;           // Start time in seconds
  end: number;             // End time in seconds
  title: string;           // Chapter title
}
```

### Audio File

```typescript
interface AudioFile {
  index: number;           // File index
  ino: string;             // Inode number
  metadata: FileMetadata;
  addedAt: number;
  updatedAt: number;
  format: string;          // e.g., "M4B", "MP3"
  duration: number;        // Duration in seconds
  bitRate: number;         // Bits per second
  codec: string;           // Audio codec
  channels: number;        // Number of audio channels
  mimeType: string;        // MIME type
}
```

---

## Error Handling

### HTTP Status Codes

| Status Code | Description | Action |
|-------------|-------------|--------|
| `200` | Success | Process response |
| `400` | Bad Request | Check request format |
| `401` | Unauthorized | Verify API key |
| `403` | Forbidden | Check user permissions |
| `404` | Not Found | Item doesn't exist |
| `500` | Server Error | Retry or report issue |

### Recommended Error Handling

```python
import requests
from requests.exceptions import HTTPError, ConnectionError, Timeout

try:
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()

except HTTPError as e:
    # Handle HTTP errors (4xx, 5xx)
    logger.error(f"HTTP error: {e.response.status_code}")
    return None

except ConnectionError:
    # Handle connection failures
    logger.error("Connection failed")
    return None

except Timeout:
    # Handle timeouts
    logger.error("Request timed out")
    return None
```

### Timeout Recommendations

| Operation | Recommended Timeout |
|-----------|---------------------|
| Get item details | 30 seconds |
| Download audio (small) | 60 seconds |
| Download audio (large) | 300-600 seconds |
| Update chapters | 30 seconds |

---

## Implementation Examples

### Complete Client Class (Python)

```python
import requests
from typing import Dict, List, Optional

class AudiobookshelfClient:
    def __init__(self, server_url: str, api_key: str, timeout: int = 30):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    def _get_auth_headers(self) -> Dict[str, str]:
        return {"Authorization": f"Bearer {self.api_key}"}

    def get_item_details(self, item_id: str) -> Optional[Dict]:
        """Fetch complete item details including chapters."""
        try:
            response = requests.get(
                f"{self.server_url}/api/items/{item_id}",
                headers=self._get_auth_headers(),
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Error fetching item: {e}")
            return None

    def get_chapters(self, item_id: str) -> List[Dict]:
        """Fetch chapters for an item."""
        details = self.get_item_details(item_id)
        if details:
            return details.get("media", {}).get("chapters", [])
        return []

    def download_audio(self, item_id: str, output_path: str) -> bool:
        """Download audio file for an item."""
        try:
            response = requests.get(
                f"{self.server_url}/api/items/{item_id}/download",
                params={"token": self.api_key},
                stream=True,
                timeout=self.timeout
            )
            response.raise_for_status()

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        except requests.RequestException as e:
            print(f"Error downloading audio: {e}")
            return False

    def update_chapters(self, item_id: str, chapters: List[Dict]) -> bool:
        """Update chapters for an item."""
        try:
            response = requests.post(
                f"{self.server_url}/api/items/{item_id}/chapters",
                headers={
                    **self._get_auth_headers(),
                    "Content-Type": "application/json"
                },
                json={"chapters": chapters},
                timeout=self.timeout
            )
            response.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"Error updating chapters: {e}")
            return False


# Usage
client = AudiobookshelfClient(
    server_url="https://abs.example.com",
    api_key="your_api_key_here"
)

# Get chapters
chapters = client.get_chapters("li_abc123")

# Download audio
client.download_audio("li_abc123", "/tmp/audiobook.m4b")

# Update chapters with new timing
updated_chapters = [
    {"id": 0, "start": 0, "end": 100.5, "title": "Intro"},
    {"id": 1, "start": 100.5, "end": 500.0, "title": "Chapter 1"},
]
client.update_chapters("li_abc123", updated_chapters)
```

---

## Additional Resources

- [Audiobookshelf Official API Docs](https://api.audiobookshelf.org/)
- [Audiobookshelf GitHub Repository](https://github.com/advplyr/audiobookshelf)

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2024-01 | Initial documentation |

---

*This documentation was generated from analysis of the absrefined client implementation.*
