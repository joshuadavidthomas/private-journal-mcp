"""Path resolution utilities for journal storage locations.

Uses platformdirs for cross-platform user data directory resolution.
"""

from pathlib import Path

from platformdirs import user_data_dir


def resolve_user_journal_path() -> Path:
    """Resolve user data directory for personal journal storage.

    Uses platformdirs to find the appropriate user data directory
    for the current platform (e.g., ~/.local/share on Linux,
    ~/Library/Application Support on macOS, %LOCALAPPDATA% on Windows).

    Returns:
        Path to user's private journal directory
    """
    return Path(user_data_dir("private-journal-mcp", appauthor=False))


def resolve_project_journal_path() -> Path:
    """Resolve project directory for project-specific journal storage.

    Uses the current working directory if it's not a system directory,
    otherwise falls back to user data directory.

    Returns:
        Path to project's private journal directory
    """
    try:
        cwd = Path.cwd()
        # Don't use root directories or other system directories
        system_dirs = {Path("/"), Path("C:\\"), Path("/System"), Path("/usr")}
        if cwd not in system_dirs:
            return cwd / ".private-journal"
    except (OSError, RuntimeError):
        # If we can't get cwd, fall back to user data directory
        pass

    # Fallback to user data directory
    return resolve_user_journal_path()
