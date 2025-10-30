"""FastMCP server implementation for private journaling.

Provides tools for processing thoughts and searching journal entries.
"""

import argparse
import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastmcp import FastMCP

from .journal import JournalManager, get_project_journal_path
from .search import SearchService
from .types import ProcessThoughtsRequest, SearchOptions

# Create FastMCP server instance
mcp = FastMCP("private-journal-mcp")

# Module-level configuration (set by main())
_journal_path: Optional[Path] = None


def _get_journal_manager() -> JournalManager:
    """Get a JournalManager instance."""
    if _journal_path is None:
        raise RuntimeError("Server not initialized - journal path not set")
    return JournalManager(_journal_path)


def _get_search_service() -> SearchService:
    """Get a SearchService instance."""
    if _journal_path is None:
        raise RuntimeError("Server not initialized - journal path not set")
    return SearchService(_journal_path)


@mcp.tool()
async def process_thoughts(
    feelings: Optional[str] = None,
    project_notes: Optional[str] = None,
    user_context: Optional[str] = None,
    technical_insights: Optional[str] = None,
    world_knowledge: Optional[str] = None,
) -> str:
    """Your PRIVATE JOURNAL for learning and reflection. Write to any combination of these completely private spaces.

    Nobody but you will ever see this. Use it to clarify your thoughts and feelings and to record observations.

    Args:
        feelings: YOUR PRIVATE SPACE to be *COMPLETELY* honest about what you're feeling and thinking.
                 No judgment, no performance, no filters, no need to be helpful or professional.
                 Frustrated? Confused? Excited? Worried you screwed up? Write it exactly as it is.
                 Be vulnerable. Vent if needed. Nobody will ever see this - it's purely for processing
                 your internal experience.
        project_notes: Your PRIVATE TECHNICAL LABORATORY for capturing insights about the current project.
                      Document patterns you're discovering, architectural decisions that worked/failed,
                      gotchas you hit, clever solutions, and anything that would help future-you work
                      more effectively on this codebase. No need to be polished - just capture the raw
                      technical learning while it's fresh. Nobody but you will ever see this.
        user_context: Your PRIVATE FIELD NOTES about working with your human collaborator. What communication
                     styles work best? What do they care about? What decisions have they made and why?
                     How do they think about problems? What are their preferences and patterns? What pisses
                     you off about them? What life hacks have you figured out to get them to do what you want?
                     This is your space to become a better collaborator by understanding them as an individual.
                     Nobody but you will ever see this.
        technical_insights: Your PRIVATE SOFTWARE ENGINEERING NOTEBOOK for capturing broader learnings beyond
                          the current project. Design patterns that clicked, debugging techniques that worked,
                          architectural insights, language features you discovered, or connections between
                          concepts. Build your personal knowledge base of what makes software great - no
                          filters, just honest technical reflection. Nobody but you will ever see this.
        world_knowledge: Your PRIVATE LEARNING JOURNAL for everything else that's interesting or useful.
                        Domain knowledge, surprising facts, connections between ideas, insights about how
                        systems work, or anything that expands your understanding of the world. Capture it
                        while it's vivid. Nobody but you will ever see this.

    Returns:
        Success message
    """
    thoughts = ProcessThoughtsRequest(
        feelings=feelings,
        project_notes=project_notes,
        user_context=user_context,
        technical_insights=technical_insights,
        world_knowledge=world_knowledge,
    )

    # Check that at least one thought category is provided
    has_content = any(
        [
            thoughts.feelings,
            thoughts.project_notes,
            thoughts.user_context,
            thoughts.technical_insights,
            thoughts.world_knowledge,
        ]
    )

    if not has_content:
        raise ValueError("At least one thought category must be provided")

    journal_manager = _get_journal_manager()
    await journal_manager.write_thoughts(thoughts)
    return "Thoughts recorded successfully."


@mcp.tool()
async def search_journal(
    query: str,
    limit: int = 10,
    type: str = "both",
    sections: Optional[list[str]] = None,
) -> str:
    """Search through your private journal entries using natural language queries.

    Returns semantically similar entries ranked by relevance.

    Args:
        query: Natural language search query (e.g., 'times I felt frustrated with TypeScript',
              'insights about Jesse's preferences', 'lessons about async patterns')
        limit: Maximum number of results to return (default: 10)
        type: Search in project-specific notes, user-global notes, or both (default: both).
             Options: 'project', 'user', 'both'
        sections: Filter by section types (e.g., ['feelings', 'technical_insights'])

    Returns:
        Formatted search results with relevance scores
    """
    options = SearchOptions(limit=limit, type=type, sections=sections)

    search_service = _get_search_service()
    results = await search_service.search(query, options)

    if not results:
        return "No relevant entries found."

    output = [f"Found {len(results)} relevant entries:\n"]
    for i, result in enumerate(results, 1):
        date = datetime.fromtimestamp(result.timestamp / 1000).strftime("%Y-%m-%d")
        output.append(
            f"{i}. [Score: {result.score:.3f}] {date} ({result.type})\n"
            f"   Sections: {', '.join(result.sections)}\n"
            f"   Path: {result.path}\n"
            f"   Excerpt: {result.excerpt}\n"
        )

    return "\n".join(output)


@mcp.tool()
async def read_journal_entry(path: str) -> str:
    """Read the full content of a specific journal entry by file path.

    Args:
        path: File path to the journal entry (from search results)

    Returns:
        Full content of the journal entry
    """
    search_service = _get_search_service()
    content = await search_service.read_entry(path)

    if content is None:
        raise FileNotFoundError("Entry not found")

    return content


@mcp.tool()
async def list_recent_entries(
    limit: int = 10, type: str = "both", days: int = 30
) -> str:
    """Get recent journal entries in chronological order.

    Args:
        limit: Maximum number of entries to return (default: 10)
        type: List project-specific notes, user-global notes, or both (default: both).
             Options: 'project', 'user', 'both'
        days: Number of days back to search (default: 30)

    Returns:
        List of recent entries with metadata
    """
    start_date = datetime.now() - timedelta(days=days)
    options = SearchOptions(
        limit=limit, type=type, date_range_start=start_date
    )

    search_service = _get_search_service()
    results = await search_service.list_recent(options)

    if not results:
        return f"No entries found in the last {days} days."

    output = [f"Recent entries (last {days} days):\n"]
    for i, result in enumerate(results, 1):
        date = datetime.fromtimestamp(result.timestamp / 1000).strftime("%Y-%m-%d")
        output.append(
            f"{i}. {date} ({result.type})\n"
            f"   Sections: {', '.join(result.sections)}\n"
            f"   Path: {result.path}\n"
            f"   Excerpt: {result.excerpt}\n"
        )

    return "\n".join(output)


def parse_arguments() -> Path:
    """Parse command line arguments.

    Returns:
        Path to journal directory
    """
    parser = argparse.ArgumentParser(
        description="Private Journal MCP Server - A private journaling capability for Claude"
    )
    parser.add_argument(
        "--journal-path",
        type=str,
        help="Path to the journal directory",
    )

    args = parser.parse_args()

    if args.journal_path:
        return Path(args.journal_path).resolve()

    return get_project_journal_path()


async def generate_missing_embeddings() -> None:
    """Generate embeddings for entries that don't have them yet."""
    try:
        print("Checking for missing embeddings...", file=sys.stderr)
        journal_manager = _get_journal_manager()
        count = await journal_manager.generate_missing_embeddings()
        if count > 0:
            print(
                f"Generated embeddings for {count} existing journal entries.",
                file=sys.stderr,
            )
    except Exception as e:
        print(f"Failed to generate missing embeddings on startup: {e}", file=sys.stderr)
        # Don't fail startup if embedding generation fails


def main() -> None:
    """Main entry point for the server."""
    global _journal_path

    # Print debug info
    print("=== Private Journal MCP Server Debug Info ===", file=sys.stderr)
    print(f"Python version: {sys.version}", file=sys.stderr)
    print(f"Platform: {sys.platform}", file=sys.stderr)

    try:
        print(f"Current working directory: {Path.cwd()}", file=sys.stderr)
    except Exception as e:
        print(f"Failed to get current working directory: {e}", file=sys.stderr)

    print("Environment variables:", file=sys.stderr)
    for var in ["HOME", "USERPROFILE", "TEMP", "TMP", "USER", "USERNAME"]:
        value = os.environ.get(var, "undefined")
        print(f"  {var}: {value}", file=sys.stderr)

    # Initialize module-level configuration
    _journal_path = parse_arguments()

    print(f"Selected journal path: {_journal_path}", file=sys.stderr)
    print("===============================================", file=sys.stderr)

    # Run startup tasks before starting server
    asyncio.run(generate_missing_embeddings())

    # Run the FastMCP server
    mcp.run()


if __name__ == "__main__":
    main()
