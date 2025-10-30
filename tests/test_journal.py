"""Tests for journal manager functionality."""

import pytest
from datetime import datetime
from pathlib import Path

from private_journal_mcp.journal import JournalManager
from private_journal_mcp.types import ProcessThoughtsRequest


@pytest.mark.asyncio
async def test_write_entry(tmp_path):
    """Test writing a simple journal entry."""
    manager = JournalManager(tmp_path)

    content = "Test entry content"
    await manager.write_entry(content)

    # Check that a file was created
    date_str = datetime.now().strftime("%Y-%m-%d")
    day_dir = tmp_path / date_str
    assert day_dir.exists()

    md_files = list(day_dir.glob("*.md"))
    assert len(md_files) == 1

    # Check content
    with open(md_files[0], "r") as f:
        file_content = f.read()
        assert content in file_content
        assert "---" in file_content  # YAML frontmatter


@pytest.mark.asyncio
async def test_write_thoughts(tmp_path):
    """Test writing categorized thoughts."""
    project_path = tmp_path / "project"
    user_path = tmp_path / "user"

    manager = JournalManager(project_path, user_path)

    thoughts = ProcessThoughtsRequest(
        feelings="Feeling good about this test",
        project_notes="This is a project note",
    )

    await manager.write_thoughts(thoughts)

    # Check that files were created in both directories
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Project notes should be in project directory
    project_day_dir = project_path / date_str
    assert project_day_dir.exists()
    project_files = list(project_day_dir.glob("*.md"))
    assert len(project_files) == 1

    with open(project_files[0], "r") as f:
        content = f.read()
        assert "Project Notes" in content
        assert "This is a project note" in content

    # User thoughts should be in user directory
    user_day_dir = user_path / date_str
    assert user_day_dir.exists()
    user_files = list(user_day_dir.glob("*.md"))
    assert len(user_files) == 1

    with open(user_files[0], "r") as f:
        content = f.read()
        assert "Feelings" in content
        assert "Feeling good about this test" in content


@pytest.mark.asyncio
async def test_format_date():
    """Test date formatting."""
    manager = JournalManager(Path("/tmp"))
    date = datetime(2025, 1, 15, 14, 30, 45)
    formatted = manager._format_date(date)
    assert formatted == "2025-01-15"


@pytest.mark.asyncio
async def test_format_timestamp():
    """Test timestamp formatting."""
    manager = JournalManager(Path("/tmp"))
    date = datetime(2025, 1, 15, 14, 30, 45)
    formatted = manager._format_timestamp(date)
    # Should match HH-MM-SS-μμμμμμ pattern
    parts = formatted.split("-")
    assert len(parts) == 4
    assert parts[0] == "14"  # hours
    assert parts[1] == "30"  # minutes
    assert parts[2] == "45"  # seconds
    assert len(parts[3]) == 6  # microseconds
