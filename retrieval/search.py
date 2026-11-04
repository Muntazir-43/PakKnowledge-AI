
from pathlib import Path
import re
from collections import defaultdict

import chromadb


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CHROMA_DIR = PROJECT_ROOT / "data" / "chroma_db"
COLLECTION_NAME = "pakknowledge_documents"


def normalize_text(text: str) -> str:
    """Normalize text for duplicate detection."""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\w\s]", "", text)
    return text.strip()


def is_low_value_page(text: str) -> bool:
    """
    Identify obvious navigation-only or very short passages.

    This is intentionally conservative. Ordinary introductory
    paragraphs are not automatically removed.
    """
    normalized = normalize_text(text)

    if not normalized:
        return True

    words = normalized.split()

    # Avoid indexing/searching extremely short fragments.
    if len(words) < 8:
        return True

    markers = [
        "table of contents",
        "list of figures",
        "list of tables",
        "acknowledgements",
        "acknowledgments",
        "all rights reserved",
        "copyright",
        "bibliography",
        "references",
    ]

    marker_hits = sum(
        1 for marker in markers if marker in normalized
    )

    # Filter only pages strongly dominated by navigation/reference text.
    if marker_hits >= 2 and len(words) < 180:
        return True

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    if len(lines) >= 5:
        dot_leaders = sum(
            1 for line in lines
            if re.search(r"\.{5,}|_{5,}", line)
        )

        if dot_leaders / len(lines) >= 0.45:
            return True

    return False


def is_duplicate(candidate: dict, selected: list[dict]) -> bool:
    """Detect exact and highly overlapping passages."""

    candidate_text = normalize_text(candidate.get("text", ""))

    if not candidate_text:
        return True

    candidate_tokens = set(candidate_text.split())

    for existing in selected:

        existing_text = normalize_text(
            existing.get("text", "")
        )

        if candidate_text == existing_text:
            return True

        existing_tokens = set(existing_text.split())

        smaller_size = min(
            len(candidate_tokens),
            len(existing_tokens)
        )

        if smaller_size >= 20:

            overlap = (
                len(candidate_tokens & existing_tokens)
                / smaller_size
            )

            if overlap >= 0.90:
                return True

    return False


def search_documents(
    query: str,
    top_k: int = 5,
    candidate_multiplier: int = 4,
    max_per_page: int = 1,
) -> list[dict]:
    """
    Retrieve relevant passages from ChromaDB.

    Improvements:
    - Retrieve additional candidates.
    - Include category metadata.
    - Remove duplicate passages.
    - Improve page diversity.
    - Filter obvious navigation-only passages.

    Lower cosine distance indicates a closer match.
    """

    if not query or not query.strip():
        raise ValueError("Search query cannot be empty.")

    if top_k < 1:
        raise ValueError("top_k must be at least 1.")

    if candidate_multiplier < 1:
        raise ValueError(
            "candidate_multiplier must be at least 1."
        )

    if max_per_page < 1:
        raise ValueError(
            "max_per_page must be at least 1."
        )

    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    total = collection.count()

    if total == 0:
        return []

    # Retrieve more candidates than the final requested number.
    candidate_count = min(
        max(top_k * candidate_multiplier, top_k),
        total
    )

    results = collection.query(
        query_texts=[query.strip()],
        n_results=candidate_count,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    candidates = []

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    for index, text in enumerate(documents):

        if not text or not text.strip():
            continue

        metadata = metadatas[index] or {}
        distance = distances[index]

        if is_low_value_page(text):
            continue

        candidates.append({
            "text": text.strip(),

            "source": metadata.get(
                "source",
                "Unknown source"
            ),

            "title": metadata.get(
                "title",
                "Untitled document"
            ),

            "category": metadata.get(
                "category",
                "Uncategorized"
            ),

            "source_type": metadata.get(
                "source_type"
            ),

            "page": metadata.get("page"),

            "chunk_index": metadata.get(
                "chunk_index"
            ),

            "distance": (
                float(distance)
                if distance is not None
                else None
            ),
        })

    # ChromaDB already orders results by cosine distance.
    # Preserve this relevance ordering while applying diversity.
    selected = []
    page_counts = defaultdict(int)

    # First pass: limit repeated passages from the same page.
    for candidate in candidates:

        page_key = (
            candidate["source"],
            (
                candidate["page"]
                if candidate["page"] is not None
                else candidate["chunk_index"]
            ),
        )

        if page_counts[page_key] >= max_per_page:
            continue

        if is_duplicate(candidate, selected):
            continue

        selected.append(candidate)
        page_counts[page_key] += 1

        if len(selected) >= top_k:
            break

    # Second pass: fill remaining slots if necessary.
    # This avoids returning too few results for small collections.
    if len(selected) < top_k:

        for candidate in candidates:

            if candidate in selected:
                continue

            if is_duplicate(candidate, selected):
                continue

            selected.append(candidate)

            if len(selected) >= top_k:
                break

    return selected


if __name__ == "__main__":

    question = input(
        "Enter a question about Pakistan: "
    ).strip()

    results = search_documents(
        question,
        top_k=8
    )

    for number, passage in enumerate(
        results,
        start=1
    ):

        print(f"\n--- Result {number} ---")

        print(
            f"Source: {passage['title']}"
        )

        print(
            f"Category: {passage['category']}"
        )

        if passage["page"] is not None:
            print(
                f"Page: {passage['page']}"
            )

        if passage["distance"] is not None:
            print(
                f"Distance: {passage['distance']:.4f}"
            )

        print(
            passage["text"][:700]
        )
