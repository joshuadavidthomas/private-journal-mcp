"""Tests for path resolution utilities."""

from pathlib import Path
from unittest.mock import patch

import pytest

from private_journal_mcp.paths import (
    resolve_project_journal_path,
    resolve_user_journal_path,
)


def test_resolve_user_journal_path():
    """Test user journal path resolution uses platformdirs."""
    path = resolve_user_journal_path()
    # Should return a valid path (exact location is platform-specific)
    assert isinstance(path, Path)
    assert "private-journal-mcp" in str(path)


def test_resolve_project_journal_path(tmp_path, monkeypatch):
    """Test project journal path resolution uses cwd."""
    monkeypatch.chdir(tmp_path)
    path = resolve_project_journal_path()
    assert path == tmp_path / ".private-journal"


def test_resolve_project_journal_path_system_dir(monkeypatch):
    """Test project journal path falls back when cwd is a system directory."""
    # Mock cwd to return a system directory
    with patch("private_journal_mcp.paths.Path.cwd", return_value=Path("/")):
        path = resolve_project_journal_path()
        # Should fall back to user data directory
        assert isinstance(path, Path)
        assert "private-journal-mcp" in str(path)


def test_resolve_project_journal_path_cwd_error(monkeypatch):
    """Test project journal path falls back when cwd fails."""
    # Mock cwd to raise an exception
    with patch("private_journal_mcp.paths.Path.cwd", side_effect=OSError("No cwd")):
        path = resolve_project_journal_path()
        # Should fall back to user data directory
        assert isinstance(path, Path)
        assert "private-journal-mcp" in str(path)
