"""Type definitions for the private journal MCP server."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class JournalEntry:
    """Represents a single journal entry."""

    content: str
    timestamp: datetime
    file_path: Path


@dataclass
class ProcessThoughtsRequest:
    """Request structure for processing thoughts."""

    feelings: Optional[str] = None
    project_notes: Optional[str] = None
    user_context: Optional[str] = None
    technical_insights: Optional[str] = None
    world_knowledge: Optional[str] = None


@dataclass
class EmbeddingData:
    """Data structure for storing embeddings with metadata."""

    embedding: list[float]
    text: str
    sections: list[str]
    timestamp: int
    path: str


@dataclass
class SearchResult:
    """Result from a journal search."""

    path: str
    score: float
    text: str
    sections: list[str]
    timestamp: int
    excerpt: str
    type: str  # 'project' or 'user'


@dataclass
class SearchOptions:
    """Options for searching journal entries."""

    limit: int = 10
    min_score: float = 0.1
    sections: Optional[list[str]] = None
    date_range_start: Optional[datetime] = None
    date_range_end: Optional[datetime] = None
    type: str = "both"  # 'project', 'user', or 'both'
