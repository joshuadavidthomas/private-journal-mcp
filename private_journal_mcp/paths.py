"""Path resolution utilities for journal storage locations.

Provides cross-platform fallback logic for finding suitable directories.
"""

import os
from pathlib import Path


def resolve_journal_path(
    subdirectory: str = ".private-journal",
    include_current_directory: bool = True,
) -> Path:
    """Resolve the best available directory for journal storage.

    Args:
        subdirectory: Subdirectory name (e.g., '.private-journal')
        include_current_directory: Whether to consider current working directory

    Returns:
        Path to journal directory
    """
    possible_paths = []

    # Try current working directory only if requested and it's reasonable
    if include_current_directory:
        try:
            cwd = Path.cwd()
            # Don't use root directories or other system directories
            system_dirs = {Path("/"), Path("C:\\"), Path("/System"), Path("/usr")}
            if cwd not in system_dirs:
                possible_paths.append(cwd / subdirectory)
        except (OSError, RuntimeError):
            # Ignore errors getting cwd
            pass

    # Try home directories (cross-platform)
    if home := os.environ.get("HOME"):
        possible_paths.append(Path(home) / subdirectory)
    if userprofile := os.environ.get("USERPROFILE"):
        possible_paths.append(Path(userprofile) / subdirectory)

    # Try temp directories as last resort
    possible_paths.append(Path("/tmp") / subdirectory)
    if temp := os.environ.get("TEMP"):
        possible_paths.append(Path(temp) / subdirectory)
    if tmp := os.environ.get("TMP"):
        possible_paths.append(Path(tmp) / subdirectory)

    # Return first valid path (all paths are technically valid)
    return possible_paths[0] if possible_paths else Path("/tmp") / subdirectory


def resolve_user_journal_path() -> Path:
    """Resolve user home directory for personal journal storage.

    Returns:
        Path to user's private journal directory
    """
    return resolve_journal_path(".private-journal", include_current_directory=False)


def resolve_project_journal_path() -> Path:
    """Resolve project directory for project-specific journal storage.

    Returns:
        Path to project's private journal directory
    """
    return resolve_journal_path(".private-journal", include_current_directory=True)
