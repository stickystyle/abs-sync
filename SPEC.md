# Audiobookshelf Sync (abs-sync) Specification

## Overview

A Python script that syncs audiobooks from a "triage" Audiobookshelf (ABS) server to a main ABS server. The script downloads books from a designated collection on the source server directly to the destination library folder, triggers a library scan, and applies metadata via the API.

### Purpose

Enable a workflow where a triage ABS server is used to curate and prepare audiobooks before they are promoted to the main ABS library.

---

## Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SYNC WORKFLOW                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Connect to SOURCE (triage) ABS server                           │
│                         │                                            │
│                         ▼                                            │
│  2. Fetch books from "Download" collection                          │
│                         │                                            │
│                         ▼                                            │
│  3. For each book:                                                   │
│     ├─► Check if folder exists at DOWNLOAD_PATH/Author/Title/       │
│     │   └─► If exists: Skip download, mark as synced                │
│     │                                                                │
│     ├─► Download all audio files (preserve multi-file structure)    │
│     ├─► Download cover image (if exists)                            │
│     └─► Save to: DOWNLOAD_PATH/Author/Book Title/                   │
│                         │                                            │
│                         ▼                                            │
│  4. Trigger library scan on DESTINATION ABS server                  │
│                         │                                            │
│                         ▼                                            │
│  5. Poll scan status until complete                                 │
│                         │                                            │
│                         ▼                                            │
│  6. Match newly scanned books by folder path                        │
│                         │                                            │
│                         ▼                                            │
│  7. Apply preserved metadata from source to destination via API     │
│                         │                                            │
│                         ▼                                            │
│  8. Move book from "Download" to "Synced" collection on SOURCE      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Configuration

All configuration via environment variables. Use `python-dotenv` to support `.env` files.

### Required Variables

| Variable | Description |
|----------|-------------|
| `SOURCE_ABS_URL` | Triage/source ABS server URL (e.g., `http://triage.local:13378`) |
| `SOURCE_ABS_API_KEY` | API key for source server |
| `DEST_ABS_URL` | Main/destination ABS server URL (e.g., `http://main.local:13378`) |
| `DEST_ABS_API_KEY` | API key for destination server |
| `DEST_LIBRARY_ID` | Target library ID on destination server |
| `DOWNLOAD_PATH` | Absolute path to the destination library folder on filesystem |

### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SOURCE_COLLECTION_NAME` | `Download` | Collection name to sync books from |
| `SYNCED_COLLECTION_NAME` | `Synced` | Collection name to move completed books to |
| `LOG_PATH` | `./logs` | Directory for log files |

### Example `.env` File

```env
# Source (Triage) Server
SOURCE_ABS_URL=http://192.168.1.100:13378
SOURCE_ABS_API_KEY=your-source-api-key-here

# Destination (Main) Server
DEST_ABS_URL=http://192.168.1.101:13378
DEST_ABS_API_KEY=your-dest-api-key-here
DEST_LIBRARY_ID=lib_abc123xyz

# Paths
DOWNLOAD_PATH=/audiobooks

# Optional - Collection Names (defaults shown)
# SOURCE_COLLECTION_NAME=Download
# SYNCED_COLLECTION_NAME=Synced

# Optional - Logging
# LOG_PATH=./logs
```

---

## File Handling

### Folder Structure

Books are downloaded to:
```
{DOWNLOAD_PATH}/{Author}/{Book Title}/
```

Example:
```
/audiobooks/Brandon Sanderson/The Final Empire/
├── cover.jpg
├── The Final Empire - Part 1.mp3
├── The Final Empire - Part 2.mp3
└── The Final Empire - Part 3.mp3
```

### File Preservation

- **Preserve original file structure**: Multi-file audiobooks remain as multiple files (no concatenation)
- **Download all audio files**: All audio files associated with the book are downloaded
- **Cover images**: Download cover image if one exists on the source server

### Filename Sanitization

Replace or remove characters that are invalid in filesystem paths:
- `:` → `-`
- `/` → `-`
- `\` → `-`
- `?` → (removed)
- `*` → (removed)
- `"` → `'`
- `<` → (removed)
- `>` → (removed)
- `|` → `-`

Trim leading/trailing whitespace and periods from folder names.

---

## Metadata Transfer

The following metadata fields are transferred from source to destination via the ABS API after the library scan completes:

### Book Metadata
- Title
- Subtitle
- Author(s)
- Narrator(s)
- Series name
- Series sequence number
- Description/summary
- Publisher
- Publish year
- Language
- Genres/tags
- Explicit flag
- ASIN
- ISBN

### Media
- Cover image (downloaded as file, also set via API if needed)

---

## API Operations

### Source Server Operations

1. **Get collection by name** - Find the "Download" collection
2. **Get books in collection** - List all books in the collection
3. **Get book details** - Fetch full metadata for each book
4. **Download book files** - Download audio files via `/api/items/{id}/download`
5. **Get cover image** - Download cover via `/api/items/{id}/cover`
6. **Get/create collection** - Find or create "Synced" collection
7. **Update book collection** - Move book from "Download" to "Synced"

### Destination Server Operations

1. **Trigger library scan** - Start a scan of the target library
2. **Poll scan status** - Check if scan is complete
3. **Find book by folder path** - Match newly scanned book to apply metadata
4. **Update book metadata** - Apply all metadata fields from source

---

## Duplicate Detection

Before downloading a book, check if the folder already exists:

```python
target_path = f"{DOWNLOAD_PATH}/{sanitize(author)}/{sanitize(title)}"
if os.path.exists(target_path):
    # Skip download, but still move to "Synced" collection on source
```

If a book is skipped due to already existing, it is still considered "synced" and moved to the "Synced" collection.

---

## Error Handling

### Strategy
- **Skip and continue**: If a book fails to sync, log the error and continue with remaining books
- **Don't leave partial state**: If download fails, clean up any partially downloaded files

### Error Scenarios

| Scenario | Behavior |
|----------|----------|
| Book download fails | Log error, skip book, continue with next |
| Metadata application fails | Log error, skip book, continue with next |
| Collection move fails | Log error, skip book, continue with next |
| Source server unreachable | Exit with error code 1 |
| Destination server unreachable | Exit with error code 1 |
| Empty/missing source collection | Exit gracefully with code 0 |
| Book missing author or title | Log warning, skip book, continue |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Success (including "nothing to sync") |
| `1` | One or more errors occurred |

---

## Logging

### Console Output

Simple, informative messages:
```
Starting abs-sync...
Found 3 books in "Download" collection
[1/3] Downloading: The Final Empire by Brandon Sanderson
[1/3] Download complete
[2/3] Skipping (already exists): Mistborn by Brandon Sanderson
[3/3] Downloading: Elantris by Brandon Sanderson
[3/3] Download complete
Triggering library scan...
Scan complete
Applying metadata to 2 new books...
Moving 3 books to "Synced" collection...
Sync complete: 2 downloaded, 1 skipped, 0 failed
```

### Log File

- **Location**: `{LOG_PATH}/sync_YYYY-MM-DD_HHMMSS.log`
- **Format**: Timestamped entries with full details
- **Content**: All operations, errors with stack traces, API responses for failures

Example log filename: `logs/sync_2024-01-15_143022.log`

---

## CLI Interface

### Usage

```bash
# Normal run
python -m abs_sync

# Or via entry point
abs-sync

# Dry run (preview only)
abs-sync --dry-run
```

### Arguments

| Argument | Description |
|----------|-------------|
| `--dry-run` | Show what would be synced without making changes |

### Dry Run Output

```
[DRY RUN] Starting abs-sync...
[DRY RUN] Found 3 books in "Download" collection
[DRY RUN] Would download: The Final Empire by Brandon Sanderson
[DRY RUN] Would skip (already exists): Mistborn by Brandon Sanderson
[DRY RUN] Would download: Elantris by Brandon Sanderson
[DRY RUN] Would trigger library scan
[DRY RUN] Would move 3 books to "Synced" collection
[DRY RUN] Summary: 2 to download, 1 to skip
```

---

## Project Structure

```
abs-sync/
├── pyproject.toml          # Project config and dependencies (uv)
├── .env.example            # Example environment variables
├── README.md               # Usage documentation
├── logs/                   # Log file directory (created at runtime)
│   └── .gitkeep
└── abs_sync/
    ├── __init__.py
    ├── __main__.py         # Entry point (python -m abs_sync)
    ├── cli.py              # CLI argument parsing
    ├── config.py           # Environment variable loading
    ├── sync.py             # Main sync orchestration logic
    ├── models.py           # Data classes for books, metadata, etc.
    ├── client/
    │   ├── __init__.py
    │   ├── abs_client.py   # Base ABS API client
    │   ├── source.py       # Source server operations
    │   └── destination.py  # Destination server operations
    ├── services/
    │   ├── __init__.py
    │   ├── downloader.py   # File download logic
    │   ├── metadata.py     # Metadata extraction and application
    │   └── sanitizer.py    # Filename sanitization
    └── utils/
        ├── __init__.py
        └── logging.py      # Logging configuration
```

---

## Technical Requirements

### Runtime
- Python 3.11+

### Dependencies
- `requests` - HTTP client for API calls
- `python-dotenv` - Environment variable loading from .env files

### Package Management
- `uv` with `pyproject.toml`

### Example `pyproject.toml`

```toml
[project]
name = "abs-sync"
version = "0.1.0"
description = "Sync audiobooks between Audiobookshelf servers"
requires-python = ">=3.11"
dependencies = [
    "requests>=2.31.0",
    "python-dotenv>=1.0.0",
]

[project.scripts]
abs-sync = "abs_sync.cli:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

---

## Scope

### In Scope
- Audiobooks only
- Single source collection → single destination library
- Sequential processing (one book at a time)
- Manual and scheduled execution

### Out of Scope
- Ebooks and podcasts
- Bidirectional sync
- Concurrent/parallel downloads
- Web UI
- Unit tests (future enhancement)
- Notifications (rely on exit codes for external alerting)

