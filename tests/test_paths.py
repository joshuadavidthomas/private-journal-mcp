"""Tests for path resolution utilities."""

import os
from pathlib import Path

import pytest

from private_journal_mcp.paths import (
    resolve_journal_path,
    resolve_project_journal_path,
    resolve_user_journal_path,
)


def test_resolve_journal_path_with_cwd(tmp_path, monkeypatch):
    """Test that current directory is used when requested."""
    monkeypatch.chdir(tmp_path)
    path = resolve_journal_path(".private-journal", include_current_directory=True)
    assert path == tmp_path / ".private-journal"


def test_resolve_journal_path_without_cwd(monkeypatch):
    """Test that home directory is used when cwd is not requested."""
    home = "/home/testuser"
    monkeypatch.setenv("HOME", home)
    path = resolve_journal_path(".private-journal", include_current_directory=False)
    assert path == Path(home) / ".private-journal"


def test_resolve_user_journal_path(monkeypatch):
    """Test user journal path resolution."""
    home = "/home/testuser"
    monkeypatch.setenv("HOME", home)
    path = resolve_user_journal_path()
    assert path == Path(home) / ".private-journal"


def test_resolve_project_journal_path(tmp_path, monkeypatch):
    """Test project journal path resolution."""
    monkeypatch.chdir(tmp_path)
    path = resolve_project_journal_path()
    assert path == tmp_path / ".private-journal"


def test_resolve_journal_path_fallback_to_tmp(monkeypatch):
    """Test fallback to /tmp when no other paths are available."""
    # Clear all environment variables
    for var in ["HOME", "USERPROFILE", "TEMP", "TMP"]:
        monkeypatch.delenv(var, raising=False)

    # Mock cwd to raise an exception
    def mock_cwd():
        raise OSError("No cwd available")

    monkeypatch.setattr(Path, "cwd", mock_cwd)

    path = resolve_journal_path(".private-journal", include_current_directory=True)
    assert path == Path("/tmp") / ".private-journal"
