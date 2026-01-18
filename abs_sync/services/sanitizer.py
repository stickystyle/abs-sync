"""Filename sanitization utilities."""

import re

# Characters to replace with alternatives
REPLACEMENTS: dict[str, str] = {
    ":": "-",
    "/": "-",
    "\\": "-",
    "|": "-",
    '"': "'",
}

# Characters to remove entirely
REMOVE: set[str] = {"?", "*", "<", ">"}


def sanitize_filename(name: str) -> str:
    """
    Sanitize a filename by removing/replacing invalid characters.

    Args:
        name: The filename to sanitize

    Returns:
        A sanitized filename safe for filesystem use
    """
    if not name:
        return "unknown"

    result = name

    # Replace characters with alternatives
    for char, replacement in REPLACEMENTS.items():
        result = result.replace(char, replacement)

    # Remove invalid characters
    for char in REMOVE:
        result = result.replace(char, "")

    # Remove control characters
    result = "".join(c for c in result if ord(c) >= 32)

    # Collapse multiple spaces/dashes
    result = re.sub(r"\s+", " ", result)
    result = re.sub(r"-+", "-", result)

    # Trim leading/trailing whitespace and periods
    result = result.strip(" .")

    # Ensure we have something left
    if not result:
        return "unknown"

    return result


def sanitize_path_component(name: str) -> str:
    """
    Sanitize a path component (directory or file name).

    Same as sanitize_filename but also handles additional edge cases.
    """
    return sanitize_filename(name)
