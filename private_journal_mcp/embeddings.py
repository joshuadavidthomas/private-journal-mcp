"""Local embedding utilities using sentence-transformers for semantic journal search.

Provides text embedding generation and similarity computation.
"""

import json
import re
import sys
from pathlib import Path
from typing import Optional

import aiofiles
import numpy as np
from sentence_transformers import SentenceTransformer

from .types import EmbeddingData

# Module-level cached model (lazy loaded)
_model = None
_model_name = "all-MiniLM-L6-v2"


def _get_model():
    """Get or load the sentence transformer model (cached)."""
    global _model
    if _model is None:
        try:
            print("Loading embedding model...", file=sys.stderr)
            _model = SentenceTransformer(_model_name)
            print("Embedding model loaded successfully", file=sys.stderr)
        except Exception as e:
            print(f"Failed to load embedding model: {e}", file=sys.stderr)
            raise
    return _model


async def generate_embedding(text: str) -> list[float]:
    """Generate an embedding vector for the given text.

    Args:
        text: The text to embed

    Returns:
        List of floats representing the embedding vector
    """
    model = _get_model()

    try:
        # sentence-transformers returns numpy arrays
        embedding = model.encode(text, convert_to_numpy=True)
        # Normalize the embedding
        embedding = embedding / np.linalg.norm(embedding)
        return embedding.tolist()
    except Exception as e:
        print(f"Failed to generate embedding: {e}", file=sys.stderr)
        raise


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Cosine similarity score between -1 and 1
    """
    if len(a) != len(b):
        raise ValueError("Vectors must have same length")

    arr_a = np.array(a)
    arr_b = np.array(b)

    dot_product = np.dot(arr_a, arr_b)
    norm_a = np.linalg.norm(arr_a)
    norm_b = np.linalg.norm(arr_b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(dot_product / (norm_a * norm_b))


async def save_embedding(file_path: Path, embedding_data: EmbeddingData) -> None:
    """Save embedding data to disk.

    Args:
        file_path: Path to the markdown file
        embedding_data: The embedding data to save
    """
    embedding_path = file_path.with_suffix(".embedding")
    async with aiofiles.open(embedding_path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(embedding_data.__dict__, indent=2))


async def load_embedding(file_path: Path) -> Optional[EmbeddingData]:
    """Load embedding data from disk.

    Args:
        file_path: Path to the markdown file

    Returns:
        EmbeddingData if found, None otherwise
    """
    embedding_path = file_path.with_suffix(".embedding")

    try:
        async with aiofiles.open(embedding_path, "r", encoding="utf-8") as f:
            content = await f.read()
            data = json.loads(content)
            return EmbeddingData(**data)
    except FileNotFoundError:
        return None


def extract_searchable_text(markdown_content: str) -> tuple[str, list[str]]:
    """Extract searchable text and sections from markdown content.

    Args:
        markdown_content: The markdown content to process

    Returns:
        Tuple of (cleaned text, list of section names)
    """
    # Remove YAML frontmatter
    without_frontmatter = re.sub(
        r"^---\n.*?\n---\n", "", markdown_content, flags=re.DOTALL
    )

    # Extract sections
    sections = []
    section_matches = re.findall(r"^## (.+)$", without_frontmatter, re.MULTILINE)
    sections.extend(section_matches)

    # Clean up markdown for embedding
    clean_text = re.sub(r"^## .+$", "", without_frontmatter, flags=re.MULTILINE)
    clean_text = re.sub(r"\n{3,}", "\n\n", clean_text)
    clean_text = clean_text.strip()

    return clean_text, sections
