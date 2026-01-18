import logging
from datetime import datetime
from pathlib import Path


def setup_logging(log_path: Path = Path("./logs"), level: int = logging.INFO) -> logging.Logger:
    """Configure logging for abs-sync."""
    # Create log directory if needed
    log_path.mkdir(parents=True, exist_ok=True)

    # Create logger
    logger = logging.getLogger("abs_sync")
    logger.setLevel(logging.DEBUG)

    # Console handler - INFO level
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))

    # File handler - DEBUG level
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_handler = logging.FileHandler(log_path / f"sync_{timestamp}.log")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    logger.addHandler(console)
    logger.addHandler(file_handler)

    return logger
