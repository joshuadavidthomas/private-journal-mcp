"""Core journal writing functionality for MCP server.

Handles file system operations, timestamps, and markdown formatting.
"""

import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles

from . import embeddings
from .paths import resolve_user_journal_path
from .types import EmbeddingData, ProcessThoughtsRequest


class JournalManager:
    """Manages journal entries and embeddings."""

    def __init__(
        self,
        project_journal_path: Path,
        user_journal_path: Optional[Path] = None,
    ):
        """Initialize the journal manager.

        Args:
            project_journal_path: Path for project-specific journal entries
            user_journal_path: Path for user-global journal entries
        """
        self.project_journal_path = Path(project_journal_path)
        self.user_journal_path = (
            Path(user_journal_path)
            if user_journal_path
            else resolve_user_journal_path()
        )

    async def write_entry(self, content: str) -> None:
        """Write a simple journal entry.

        Args:
            content: The journal entry content
        """
        timestamp = datetime.now()
        date_string = self._format_date(timestamp)
        time_string = self._format_timestamp(timestamp)

        day_directory = self.project_journal_path / date_string
        file_name = f"{time_string}.md"
        file_path = day_directory / file_name

        await self._ensure_directory_exists(day_directory)

        formatted_entry = self._format_entry(content, timestamp)
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(formatted_entry)

        # Generate and save embedding
        await self._generate_embedding_for_entry(file_path, formatted_entry, timestamp)

    async def write_thoughts(self, thoughts: ProcessThoughtsRequest) -> None:
        """Write categorized thoughts to appropriate locations.

        Args:
            thoughts: Categorized thoughts to write
        """
        timestamp = datetime.now()

        # Split thoughts into project-local and user-global
        project_thoughts = ProcessThoughtsRequest(project_notes=thoughts.project_notes)
        user_thoughts = ProcessThoughtsRequest(
            feelings=thoughts.feelings,
            user_context=thoughts.user_context,
            technical_insights=thoughts.technical_insights,
            world_knowledge=thoughts.world_knowledge,
        )

        # Write project notes to project directory
        if project_thoughts.project_notes:
            await self._write_thoughts_to_location(
                project_thoughts, timestamp, self.project_journal_path
            )

        # Write user thoughts to user directory
        has_user_content = any(
            [
                user_thoughts.feelings,
                user_thoughts.user_context,
                user_thoughts.technical_insights,
                user_thoughts.world_knowledge,
            ]
        )
        if has_user_content:
            await self._write_thoughts_to_location(
                user_thoughts, timestamp, self.user_journal_path
            )

    def _format_date(self, date: datetime) -> str:
        """Format date as YYYY-MM-DD."""
        return date.strftime("%Y-%m-%d")

    def _format_timestamp(self, date: datetime) -> str:
        """Format timestamp with microseconds as HH-MM-SS-μμμμμμ."""
        import random

        hours = date.strftime("%H")
        minutes = date.strftime("%M")
        seconds = date.strftime("%S")
        # Python's microseconds + extra random precision
        microseconds = str(date.microsecond + random.randint(0, 999)).zfill(6)
        return f"{hours}-{minutes}-{seconds}-{microseconds}"

    def _format_entry(self, content: str, timestamp: datetime) -> str:
        """Format entry with YAML frontmatter."""
        time_display = timestamp.strftime("%I:%M:%S %p")
        date_display = timestamp.strftime("%B %d, %Y")

        return f"""---
title: "{time_display} - {date_display}"
date: {timestamp.isoformat()}
timestamp: {int(timestamp.timestamp() * 1000)}
---

{content}
"""

    async def _write_thoughts_to_location(
        self, thoughts: ProcessThoughtsRequest, timestamp: datetime, base_path: Path
    ) -> None:
        """Write thoughts to a specific location."""
        date_string = self._format_date(timestamp)
        time_string = self._format_timestamp(timestamp)

        day_directory = base_path / date_string
        file_name = f"{time_string}.md"
        file_path = day_directory / file_name

        await self._ensure_directory_exists(day_directory)

        formatted_entry = self._format_thoughts(thoughts, timestamp)
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(formatted_entry)

        # Generate and save embedding
        await self._generate_embedding_for_entry(file_path, formatted_entry, timestamp)

    def _format_thoughts(
        self, thoughts: ProcessThoughtsRequest, timestamp: datetime
    ) -> str:
        """Format thoughts with YAML frontmatter and sections."""
        time_display = timestamp.strftime("%I:%M:%S %p")
        date_display = timestamp.strftime("%B %d, %Y")

        sections = []

        if thoughts.feelings:
            sections.append(f"## Feelings\n\n{thoughts.feelings}")

        if thoughts.project_notes:
            sections.append(f"## Project Notes\n\n{thoughts.project_notes}")

        if thoughts.user_context:
            sections.append(f"## User Context\n\n{thoughts.user_context}")

        if thoughts.technical_insights:
            sections.append(f"## Technical Insights\n\n{thoughts.technical_insights}")

        if thoughts.world_knowledge:
            sections.append(f"## World Knowledge\n\n{thoughts.world_knowledge}")

        return f"""---
title: "{time_display} - {date_display}"
date: {timestamp.isoformat()}
timestamp: {int(timestamp.timestamp() * 1000)}
---

{chr(10).join(sections)}
"""

    async def _generate_embedding_for_entry(
        self, file_path: Path, content: str, timestamp: datetime
    ) -> None:
        """Generate and save embedding for a journal entry."""
        try:
            text, sections = embeddings.extract_searchable_text(content)

            if not text.strip():
                return  # Skip empty entries

            embedding = await embeddings.generate_embedding(text)

            embedding_data = EmbeddingData(
                embedding=embedding,
                text=text,
                sections=sections,
                timestamp=int(timestamp.timestamp() * 1000),
                path=str(file_path),
            )

            await embeddings.save_embedding(file_path, embedding_data)
        except Exception as e:
            print(
                f"Failed to generate embedding for {file_path}: {e}", file=sys.stderr
            )
            # Don't throw - embedding failure shouldn't prevent journal writing

    async def generate_missing_embeddings(self) -> int:
        """Generate embeddings for entries that don't have them yet.

        Returns:
            Number of embeddings generated
        """
        count = 0
        paths = [self.project_journal_path, self.user_journal_path]

        for base_path in paths:
            try:
                if not base_path.exists():
                    continue

                for day_dir in base_path.iterdir():
                    if not day_dir.is_dir():
                        continue

                    # Check if it matches YYYY-MM-DD pattern
                    if not day_dir.name.replace("-", "").isdigit():
                        continue

                    for md_file in day_dir.glob("*.md"):
                        embedding_path = md_file.with_suffix(".embedding")

                        if not embedding_path.exists():
                            # Generate missing embedding
                            print(
                                f"Generating missing embedding for {md_file}",
                                file=sys.stderr,
                            )
                            async with aiofiles.open(
                                md_file, "r", encoding="utf-8"
                            ) as f:
                                content = await f.read()
                            timestamp = self._extract_timestamp_from_path(
                                md_file
                            ) or datetime.now()
                            await self._generate_embedding_for_entry(
                                md_file, content, timestamp
                            )
                            count += 1

            except Exception as e:
                print(
                    f"Failed to scan {base_path} for missing embeddings: {e}",
                    file=sys.stderr,
                )

        return count

    def _extract_timestamp_from_path(self, file_path: Path) -> Optional[datetime]:
        """Extract timestamp from file path."""
        import re

        filename = file_path.stem
        match = re.match(r"^(\d{2})-(\d{2})-(\d{2})-\d{6}$", filename)

        if not match:
            return None

        hours, minutes, seconds = match.groups()
        dir_name = file_path.parent.name
        date_match = re.match(r"^(\d{4})-(\d{2})-(\d{2})$", dir_name)

        if not date_match:
            return None

        year, month, day = date_match.groups()
        return datetime(
            int(year), int(month), int(day), int(hours), int(minutes), int(seconds)
        )

    async def _ensure_directory_exists(self, dir_path: Path) -> None:
        """Ensure directory exists, creating it if necessary."""
        try:
            dir_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise Exception(
                f"Failed to create journal directory at {dir_path}: {e}"
            ) from e
