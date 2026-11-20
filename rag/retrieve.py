#!/usr/bin/env python3
"""Search over docs/: build a Chroma index once, then retrieve(query, k) returns the k most relevant chunks.

Usage:
  python3 -m rag.retrieve --build                                # (re)build index/ from docs/
  python3 -m rag.retrieve "How long is the refund window?" -k 3   # try a query

From code:
  from rag.retrieve import retrieve
  for chunk in retrieve("How do I verify webhook signatures?", k=5):
      print(chunk.section_id, chunk.heading, chunk.score, chunk.text)

retrieve() builds the index automatically on first use. After editing docs/, rebuild with --build.
Embeddings: Chroma's default model all-MiniLM-L6-v2 (ONNX, ~80 MB, downloaded once to ~/.cache/chroma).
"""
import argparse
import re
import textwrap
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import chromadb
import yaml
from chromadb.config import Settings
from chromadb.utils import embedding_functions

ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs"
INDEX_DIR = ROOT / "index"
COLLECTION = "qorvex_docs"
MAX_WORDS = 350  # a heading block longer than this is split at blank lines (tables and code stay whole)
MIN_WORDS = 25   # a shorter piece is merged into the next piece of the same page
HEADING = re.compile(r"^#{2,3} ")


@dataclass(frozen=True)
class Chunk:
    text: str          # chunk text, starting with "<page title> > <heading>"
    section_id: str    # e.g. "06-refunds"
    heading: str       # nearest ## / ### heading
    api_version: str   # "v2", or "v1" for the legacy section
    score: float       # cosine similarity to the query, higher is closer


# ── chunking ─────────────────────────────────────────────────────────────

def read_doc(path: Path) -> tuple[dict, str]:
    _, front, body = path.read_text(encoding="utf-8").split("---\n", 2)
    return yaml.safe_load(front), body


def heading_blocks(body: str) -> list[tuple[str, list[str]]]:
    """Split a page at ## / ### headings; '#' lines inside code fences are not headings."""
    blocks, heading, lines, in_code = [], "", [], False
    for line in body.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        if not in_code and HEADING.match(line):
            blocks.append((heading, lines))
            heading, lines = line.lstrip("#").strip(), []
        lines.append(line)
    blocks.append((heading, lines))
    return [(h, ls) for h, ls in blocks if "".join(ls).strip()]


def paragraphs(lines: list[str]) -> list[str]:
    """Blank-line separated paragraphs; a code fence or a table always stays in one piece."""
    parts, current, in_code = [], [], False
    for line in lines:
        if line.startswith("```"):
            in_code = not in_code
        if line.strip() or in_code:
            current.append(line)
        elif current:
            parts.append("\n".join(current))
            current = []
    if current:
        parts.append("\n".join(current))
    return parts


def word_count(text: str) -> int:
    return len(text.split())


def split_long(parts: list[str]) -> list[str]:
    """Group paragraphs into pieces of at most MAX_WORDS; a single oversized paragraph stays whole."""
    pieces, current = [], []
    for part in parts:
        if current and word_count("\n\n".join([*current, part])) > MAX_WORDS:
            pieces.append("\n\n".join(current))
            current = []
        current.append(part)
    if current:
        pieces.append("\n\n".join(current))
    return pieces


def chunk_doc(path: Path) -> list[dict]:
    meta, body = read_doc(path)
    title = meta["title"]
    chunks, carry = [], ""
    for heading, lines in heading_blocks(body):
        for piece in split_long(paragraphs(lines)):
            piece = f"{carry}\n\n{piece}" if carry else piece
            if word_count(piece) < MIN_WORDS:
                carry = piece  # too short to stand alone, e.g. a heading followed by a sub-heading
                continue
            carry = ""
            chunks.append({"text": f"{title} > {heading or title}\n\n{piece}", "section_id": meta["section_id"],
                           "heading": heading or title, "api_version": meta["api_version"]})
    if carry and chunks:
        chunks[-1] = {**chunks[-1], "text": f"{chunks[-1]['text']}\n\n{carry}"}
    return chunks


# ── index and search ─────────────────────────────────────────────────────

def _client() -> chromadb.ClientAPI:
    return chromadb.PersistentClient(path=str(INDEX_DIR), settings=Settings(anonymized_telemetry=False))


@lru_cache(maxsize=1)
def _embedder() -> embedding_functions.DefaultEmbeddingFunction:
    return embedding_functions.DefaultEmbeddingFunction()


def build_index() -> int:
    """(Re)build index/ from docs/ and return the number of chunks."""
    chunks = [chunk for path in sorted(DOCS_DIR.glob("*.md")) for chunk in chunk_doc(path)]
    if not chunks:
        raise FileNotFoundError(f"no markdown files in {DOCS_DIR}")
    client = _client()
    try:
        client.delete_collection(COLLECTION)
    except chromadb.errors.NotFoundError:
        pass  # first build: nothing to delete
    collection = client.create_collection(COLLECTION, embedding_function=_embedder(),
                                          metadata={"hnsw:space": "cosine"})
    collection.add(
        ids=[f"{chunk['section_id']}#{i}" for i, chunk in enumerate(chunks)],
        documents=[chunk["text"] for chunk in chunks],
        metadatas=[{key: chunk[key] for key in ("section_id", "heading", "api_version")} for chunk in chunks],
    )
    _collection.cache_clear()
    return len(chunks)


@lru_cache(maxsize=1)
def _collection() -> chromadb.Collection:
    try:
        return _client().get_collection(COLLECTION, embedding_function=_embedder())
    except chromadb.errors.NotFoundError:
        build_index()
        return _client().get_collection(COLLECTION, embedding_function=_embedder())


def retrieve(query: str, k: int = 5) -> list[Chunk]:
    """Return the k chunks of docs/ closest in meaning to the query, best first."""
    if not query.strip():
        raise ValueError("query must not be empty")
    if k < 1:
        raise ValueError("k must be at least 1")
    result = _collection().query(query_texts=[query], n_results=k)
    return [
        Chunk(text=doc, section_id=meta["section_id"], heading=meta["heading"],
              api_version=meta["api_version"], score=round(1 - distance, 4))
        for doc, meta, distance in zip(result["documents"][0], result["metadatas"][0], result["distances"][0])
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query", nargs="?", help="question to search for")
    parser.add_argument("-k", type=int, default=5, help="number of chunks to return (default 5)")
    parser.add_argument("--build", action="store_true", help="rebuild the index from docs/")
    args = parser.parse_args()
    if not args.build and not args.query:
        parser.print_help()
        return
    if args.build:
        print(f"Indexed {build_index()} chunks from docs/ into {INDEX_DIR.name}/")
    if args.query:
        for rank, chunk in enumerate(retrieve(args.query, args.k), 1):
            print(f"\n[{rank}] score {chunk.score:.3f} | {chunk.section_id} > {chunk.heading} ({chunk.api_version})")
            print(textwrap.shorten(chunk.text.replace("\n", " "), 280))


if __name__ == "__main__":
    main()
