"""Journal search functionality with vector similarity and text matching.

Provides unified search across project and user journal entries.
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles

from . import embeddings
from .paths import resolve_project_journal_path, resolve_user_journal_path
from .types import EmbeddingData, SearchOptions, SearchResult


class SearchService:
    """Service for searching journal entries using semantic similarity."""

    def __init__(
        self,
        project_path: Optional[Path] = None,
        user_path: Optional[Path] = None,
    ):
        """Initialize the search service.

        Args:
            project_path: Path to project journal directory
            user_path: Path to user journal directory
        """
        self.project_path = project_path or resolve_project_journal_path()
        self.user_path = user_path or resolve_user_journal_path()

    async def search(
        self, query: str, options: Optional[SearchOptions] = None
    ) -> list[SearchResult]:
        """Search journal entries using natural language query.

        Args:
            query: Natural language search query
            options: Search options (limit, filters, etc.)

        Returns:
            List of search results sorted by relevance
        """
        if options is None:
            options = SearchOptions()

        # Generate query embedding
        query_embedding = await embeddings.generate_embedding(query)

        # Collect all embeddings
        all_embeddings: list[tuple[EmbeddingData, str]] = []

        if options.type in ("both", "project"):
            project_embeddings = await self._load_embeddings_from_path(
                self.project_path, "project"
            )
            all_embeddings.extend(project_embeddings)

        if options.type in ("both", "user"):
            user_embeddings = await self._load_embeddings_from_path(
                self.user_path, "user"
            )
            all_embeddings.extend(user_embeddings)

        # Filter by criteria
        filtered = []
        for embedding, entry_type in all_embeddings:
            # Filter by sections if specified
            if options.sections:
                has_matching_section = any(
                    any(
                        section.lower() in embedding_section.lower()
                        for embedding_section in embedding.sections
                    )
                    for section in options.sections
                )
                if not has_matching_section:
                    continue

            # Filter by date range
            if options.date_range_start or options.date_range_end:
                entry_date = datetime.fromtimestamp(embedding.timestamp / 1000)
                if options.date_range_start and entry_date < options.date_range_start:
                    continue
                if options.date_range_end and entry_date > options.date_range_end:
                    continue

            filtered.append((embedding, entry_type))

        # Calculate similarities and sort
        results: list[SearchResult] = []
        for embedding, entry_type in filtered:
            score = embeddings.cosine_similarity(query_embedding, embedding.embedding)
            excerpt = self._generate_excerpt(embedding.text, query)

            results.append(
                SearchResult(
                    path=embedding.path,
                    score=score,
                    text=embedding.text,
                    sections=embedding.sections,
                    timestamp=embedding.timestamp,
                    excerpt=excerpt,
                    type=entry_type,
                )
            )

        # Filter by min score and sort
        results = [r for r in results if r.score >= options.min_score]
        results.sort(key=lambda r: r.score, reverse=True)

        # Apply limit
        return results[: options.limit]

    async def list_recent(
        self, options: Optional[SearchOptions] = None
    ) -> list[SearchResult]:
        """List recent journal entries chronologically.

        Args:
            options: Search options (limit, filters, etc.)

        Returns:
            List of recent entries sorted by timestamp
        """
        if options is None:
            options = SearchOptions()

        all_embeddings: list[tuple[EmbeddingData, str]] = []

        if options.type in ("both", "project"):
            project_embeddings = await self._load_embeddings_from_path(
                self.project_path, "project"
            )
            all_embeddings.extend(project_embeddings)

        if options.type in ("both", "user"):
            user_embeddings = await self._load_embeddings_from_path(
                self.user_path, "user"
            )
            all_embeddings.extend(user_embeddings)

        # Filter by date range
        filtered = []
        if options.date_range_start or options.date_range_end:
            for embedding, entry_type in all_embeddings:
                entry_date = datetime.fromtimestamp(embedding.timestamp / 1000)
                if options.date_range_start and entry_date < options.date_range_start:
                    continue
                if options.date_range_end and entry_date > options.date_range_end:
                    continue
                filtered.append((embedding, entry_type))
        else:
            filtered = all_embeddings

        # Sort by timestamp (most recent first) and limit
        results: list[SearchResult] = []
        for embedding, entry_type in filtered:
            excerpt = self._generate_excerpt(embedding.text, "", 150)
            results.append(
                SearchResult(
                    path=embedding.path,
                    score=1.0,  # No similarity score for recent entries
                    text=embedding.text,
                    sections=embedding.sections,
                    timestamp=embedding.timestamp,
                    excerpt=excerpt,
                    type=entry_type,
                )
            )

        results.sort(key=lambda r: r.timestamp, reverse=True)
        return results[: options.limit]

    async def read_entry(self, file_path: str) -> Optional[str]:
        """Read the full content of a journal entry.

        Args:
            file_path: Path to the journal entry file

        Returns:
            Entry content if found, None otherwise
        """
        try:
            async with aiofiles.open(file_path, "r", encoding="utf-8") as f:
                return await f.read()
        except FileNotFoundError:
            return None

    async def _load_embeddings_from_path(
        self, base_path: Path, entry_type: str
    ) -> list[tuple[EmbeddingData, str]]:
        """Load all embeddings from a directory.

        Args:
            base_path: Base path to search for embeddings
            entry_type: Type of entries ('project' or 'user')

        Returns:
            List of (embedding_data, entry_type) tuples
        """
        embeddings: list[tuple[EmbeddingData, str]] = []

        try:
            if not base_path.exists():
                return embeddings

            for day_dir in base_path.iterdir():
                if not day_dir.is_dir():
                    continue

                # Check if it matches YYYY-MM-DD pattern
                if not day_dir.name.replace("-", "").isdigit():
                    continue

                for embedding_file in day_dir.glob("*.embedding"):
                    try:
                        async with aiofiles.open(
                            embedding_file, "r", encoding="utf-8"
                        ) as f:
                            content = await f.read()
                            embedding_data = EmbeddingData(**json.loads(content))
                            embeddings.append((embedding_data, entry_type))
                    except Exception as e:
                        print(
                            f"Failed to load embedding {embedding_file}: {e}",
                            file=sys.stderr,
                        )
                        # Continue with other files

        except Exception as e:
            print(
                f"Failed to read embeddings from {base_path}: {e}", file=sys.stderr
            )
            # Return empty list if directory doesn't exist

        return embeddings

    def _generate_excerpt(
        self, text: str, query: str, max_length: int = 200
    ) -> str:
        """Generate an excerpt from text, focusing on query terms.

        Args:
            text: The full text
            query: The search query (for highlighting relevant sections)
            max_length: Maximum length of excerpt

        Returns:
            Excerpt string
        """
        if not query or not query.strip():
            excerpt = text[:max_length]
            return excerpt + "..." if len(text) > max_length else excerpt

        query_words = query.lower().split()
        text_lower = text.lower()

        # Find the best position to start the excerpt
        best_position = 0
        best_score = 0

        for i in range(0, max(1, len(text) - max_length + 1), 20):
            window = text_lower[i : i + max_length]
            score = sum(1 for word in query_words if word in window)

            if score > best_score:
                best_score = score
                best_position = i

        excerpt = text[best_position : best_position + max_length]
        if best_position > 0:
            excerpt = "..." + excerpt
        if best_position + max_length < len(text):
            excerpt += "..."

        return excerpt
