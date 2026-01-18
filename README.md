# abs-sync

Audiobookshelf Sync Tool - Synchronizes audiobooks between ABS servers.

## Installation

```bash
uv sync
```

## Configuration

Copy `.env.example` to `.env` and fill in your server details:

```bash
cp .env.example .env
```

## Usage

```bash
# Preview sync (dry run)
abs-sync --dry-run

# Run sync
abs-sync

# Verbose output
abs-sync -v
```
