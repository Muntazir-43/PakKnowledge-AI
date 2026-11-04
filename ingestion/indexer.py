from pathlib import Path
import hashlib
import sys

import chromadb

from ingestion.load_documents import SUPPORTED_EXTENSIONS, chunk_documents, load_file

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
CHROMA_DIR = DATA_DIR / "chroma_db"
COLLECTION_NAME = "pakknowledge_documents"
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
BATCH_SIZE = 32


def get_collection():
    """Open or create the persistent collection without deleting existing data."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME, metadata={"hnsw:space": "cosine"}
    )


def discover_documents() -> list[Path]:
    """Recursively discover supported files under data/documents."""
    if not DOCUMENTS_DIR.exists():
        raise FileNotFoundError(f"Documents directory not found: {DOCUMENTS_DIR}")
    return sorted(
        [
            p.resolve()
            for p in DOCUMENTS_DIR.rglob("*")
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
        ],
        key=lambda p: str(p).lower(),
    )


def _content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _file_id(path: Path) -> str:
    normalized = str(path.resolve()).casefold()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


def _remove_legacy_root_copy(collection, path: Path) -> int:
    """Remove only old records whose source was data/<same filename>."""
    legacy_path = (DATA_DIR / path.name).resolve()
    if legacy_path == path:
        return 0

    result = collection.get(where={"title": path.name}, include=["metadatas"])
    old_source = str(legacy_path).casefold()
    ids_to_delete = [
        chunk_id
        for chunk_id, metadata in zip(result.get("ids", []), result.get("metadatas", []))
        if str(metadata.get("source", "")).casefold() == old_source
    ]
    if ids_to_delete:
        collection.delete(ids=ids_to_delete)
    return len(ids_to_delete)


def index_file(file_path: str, force: bool = False) -> int:
    """Index one file; skip unchanged content and replace changed content."""
    path = Path(file_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    collection = get_collection()
    file_id = _file_id(path)
    digest = _content_hash(path)

    legacy_removed = _remove_legacy_root_copy(collection, path)
    existing = collection.get(where={"file_id": file_id}, include=["metadatas"])
    existing_ids = existing.get("ids", [])
    hashes = {
        metadata.get("content_hash")
        for metadata in existing.get("metadatas", [])
        if metadata.get("content_hash")
    }

    if existing_ids and not force and hashes == {digest}:
        print(f"SKIPPED (unchanged): {path.name}")
        return 0
    if existing_ids:
        collection.delete(ids=existing_ids)

    chunks = chunk_documents(
        load_file(str(path)), chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP
    )
    if not chunks:
        print(f"SKIPPED (no text): {path.name}")
        return 0

    ids, texts, metadatas = [], [], []
    for index, chunk in enumerate(chunks):
        chunk_id = hashlib.sha256(
            f"{file_id}:{digest}:{index}".encode("utf-8")
        ).hexdigest()
        metadata = {
            "source": str(path),
            "title": path.name,
            "source_type": chunk.get("source_type", "file"),
            "category": chunk.get("category", "Uncategorized"),
            "file_id": file_id,
            "content_hash": digest,
            "chunk_index": index,
        }
        if chunk.get("page") is not None:
            metadata["page"] = int(chunk["page"])
        ids.append(chunk_id)
        texts.append(chunk["text"])
        metadatas.append(metadata)

    for offset in range(0, len(ids), BATCH_SIZE):
        collection.add(
            ids=ids[offset:offset + BATCH_SIZE],
            documents=texts[offset:offset + BATCH_SIZE],
            metadatas=metadatas[offset:offset + BATCH_SIZE],
        )

    if legacy_removed:
        print(f"Removed {legacy_removed} legacy chunks for {path.name}")
    print(f"INDEXED: {path.name} | {len(ids)} chunks | {chunks[0].get('category')}")
    return len(ids)


def index_all_documents(force: bool = False) -> dict:
    """Index every supported document in the subject folders."""
    files = discover_documents()
    collection = get_collection()
    before = collection.count()
    print(f"Found {len(files)} supported document(s).")
    print(f"Existing ChromaDB chunks: {before}")
    print("-" * 60)

    indexed = 0
    added = 0
    errors = []
    for path in files:
        try:
            count = index_file(str(path), force=force)
            if count:
                indexed += 1
                added += count
        except Exception as exc:
            message = f"{path}: {exc}"
            errors.append(message)
            print(f"ERROR: {message}")

    after = collection.count()
    print("-" * 60)
    print("INGESTION SUMMARY")
    print(f"Files discovered: {len(files)}")
    print(f"Files indexed/updated: {indexed}")
    print(f"New chunks added: {added}")
    print(f"Chunks before run: {before}")
    print(f"Chunks after run: {after}")
    print(f"Errors: {len(errors)}")
    for error in errors:
        print(f" - {error}")
    print(f"Persistent database: {CHROMA_DIR}")

    return {
        "files_found": len(files),
        "files_indexed": indexed,
        "chunks_added": added,
        "chunks_before": before,
        "chunks_after": after,
        "errors": errors,
    }


if __name__ == "__main__":
    index_all_documents(force="--force" in sys.argv)
