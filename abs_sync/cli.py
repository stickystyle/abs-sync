"""Command-line interface for abs-sync."""

import argparse
import logging
import sys

from abs_sync import __version__
from abs_sync.config import Config
from abs_sync.sync import SyncOrchestrator
from abs_sync.utils.logging import setup_logging


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="abs-sync",
        description="Sync audiobooks from triage to main Audiobookshelf server",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview sync without downloading or modifying anything",
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose output (DEBUG level)",
    )

    parser.add_argument(
        "--env-file",
        type=str,
        help="Path to .env file (default: .env in current directory)",
    )

    return parser.parse_args()


def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Load configuration
    try:
        from pathlib import Path
        env_file = Path(args.env_file) if args.env_file else None
        config = Config.from_env(env_file)
    except ValueError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logger = setup_logging(config.log_path, log_level)

    logger.info(f"abs-sync v{__version__}")

    if args.dry_run:
        logger.info("DRY RUN MODE - no changes will be made")

    # Run sync
    orchestrator = SyncOrchestrator(config, dry_run=args.dry_run)

    try:
        result = orchestrator.run()
    except KeyboardInterrupt:
        logger.info("\nSync interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1

    # Print summary
    logger.info("\n--- SYNC COMPLETE ---")
    logger.info(f"Total books:      {result.total_books}")
    logger.info(f"Downloaded:       {result.downloaded}")
    logger.info(f"Skipped:          {result.skipped}")
    logger.info(f"Failed:           {result.failed}")
    logger.info(f"Metadata applied: {result.metadata_applied}")

    if result.errors:
        logger.info("\nErrors:")
        for error in result.errors:
            logger.info(f"  - {error}")

    # Exit code: 1 if ALL books failed, 0 otherwise
    if result.total_books > 0 and result.failed == result.total_books:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
