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

How search works:
  1. Chunking. Pages are split at ## / ### headings; each chunk starts with "<page> > <## heading> > <### heading>".
     The embedding model reads only the first 256 tokens of a text, so chunks are capped at MAX_TOKENS
     (measured with the model's own tokenizer); long tables are split into row groups that repeat the header.
  2. Hybrid ranking. Embedding similarity and BM25 keyword ranking are merged with reciprocal rank fusion;
     keywords catch exact identifiers (`statement_descriptor`, `Qx-Retry-In`, 429) that embeddings miss.
  3. Small-to-big. A section split into several chunks is returned whole, so the LLM sees complete tables and lists.
Check search quality without the LLM: python -m eval.retrieval_eval [--method vector|bm25|hybrid]
"""
import argparse
import re
import textwrap
from collections import Counter
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
COLLECTION = "qorvex_docs_v2"  # bump when chunking changes, so old local indexes are rebuilt automatically
MAX_TOKENS = 230  # all-MiniLM-L6-v2 reads only the first 256 tokens of a text, so longer chunks are split
MIN_WORDS = 25    # a shorter piece is merged into the next piece of the same page
HEADING = re.compile(r"^#{2,3} ")


@dataclass(frozen=True)
class Chunk:
    text: str          # chunk text, starting with "<page title> > <heading>"
    section_id: str    # e.g. "06-refunds"
    heading: str       # heading path, e.g. "Create a payment > Parameters"
    api_version: str   # "v2", or "v1" for the legacy section
    score: float       # cosine similarity to the query, higher is closer (ranking itself is hybrid, see retrieve)


# ── chunking ─────────────────────────────────────────────────────────────

def read_doc(path: Path) -> tuple[dict, str]:
    _, front, body = path.read_text(encoding="utf-8").split("---\n", 2)
    return yaml.safe_load(front), body


def heading_blocks(body: str) -> list[tuple[str, list[str]]]:
    """Split a page at ## / ### headings; '#' lines inside code fences are not headings.

    A ### block is labelled with its parent heading too ("Create a payment > Parameters"),
    so that a generic sub-heading such as "Parameters" still says what it belongs to."""
    blocks, heading, parent, lines, in_code = [], "", "", [], False
    for line in body.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        if not in_code and HEADING.match(line):
            blocks.append((heading, lines))
            text = line.lstrip("#").strip()
            if line.startswith("### ") and parent:
                heading = f"{parent} > {text}"
            else:
                heading = parent = text
            lines = []
        lines.append(line)
    blocks.append((heading, lines))
    return [(h, ls) for h, ls in blocks if "".join(ls).strip()]


def paragraphs(lines: list[str]) -> list[str]:
    """Blank-line separated paragraphs; a code fence or a table is kept together as one paragraph."""
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


@lru_cache(maxsize=1)
def _tokenizer():
    from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2
    tokenizer = ONNXMiniLM_L6_V2().tokenizer
    tokenizer.no_truncation()
    tokenizer.no_padding()  # the model's tokenizer pads every text to 256; we need real lengths
    return tokenizer


def token_count(text: str) -> int:
    """Tokens as the embedding model counts them."""
    return len(_tokenizer().encode(text).ids)


def split_paragraph(part: str, budget: int) -> list[str]:
    """Split one oversized paragraph so every piece fits the budget.

    Tables are split into row groups that repeat the header row, code into line groups that keep the fence,
    prose into sentence groups."""
    lines = part.splitlines()
    if lines[0].startswith("|") and len(lines) > 2:
        head, units, tail, sep = lines[:2], lines[2:], [], "\n"
    elif lines[0].startswith("```") and lines[-1].startswith("```") and len(lines) > 2:
        head, units, tail, sep = lines[:1], lines[1:-1], lines[-1:], "\n"
    else:
        head, units, tail, sep = [], re.split(r"(?<=[.!?])\s+", part), [], " "
    pieces, current = [], []

    def render(body: list[str]) -> str:
        return "\n".join([*head, sep.join(body), *tail]) if head else sep.join(body)

    for unit in units:
        if current and token_count(render([*current, unit])) > budget:
            pieces.append(render(current))
            current = []
        current.append(unit)
    if current:
        pieces.append(render(current))
    return pieces


def split_long(parts: list[str], budget: int) -> list[str]:
    """Group paragraphs into pieces of at most `budget` tokens; oversized paragraphs are split first."""
    units = [piece for part in parts
             for piece in (split_paragraph(part, budget) if token_count(part) > budget else [part])]
    pieces, current = [], []
    for unit in units:
        if current and token_count("\n\n".join([*current, unit])) > budget:
            pieces.append("\n\n".join(current))
            current = []
        current.append(unit)
    if current:
        pieces.append("\n\n".join(current))
    return pieces


def chunk_doc(path: Path) -> list[dict]:
    meta, body = read_doc(path)
    title = meta["title"]
    chunks, carry = [], ""
    for heading, lines in heading_blocks(body):
        prefix = f"{title} > {heading or title}\n\n"
        parts = paragraphs(lines)
        if carry:  # a short piece left over from the previous block goes in front of this block's text
            parts, carry = [carry, *parts], ""
        for piece in split_long(parts, MAX_TOKENS - token_count(prefix)):
            if word_count(piece) < MIN_WORDS:
                carry = piece  # too short to stand alone, e.g. a heading followed by a sub-heading
                continue
            carry = ""
            chunks.append({"text": f"{prefix}{piece}", "section_id": meta["section_id"],
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
        metadatas=[{**{key: chunk[key] for key in ("section_id", "heading", "api_version")}, "position": i}
                   for i, chunk in enumerate(chunks)],
    )
    _collection.cache_clear()
    _bm25_index.cache_clear()
    return len(chunks)


@lru_cache(maxsize=1)
def _collection() -> chromadb.Collection:
    try:
        return _client().get_collection(COLLECTION, embedding_function=_embedder())
    except chromadb.errors.NotFoundError:
        build_index()
        return _client().get_collection(COLLECTION, embedding_function=_embedder())


# ── keyword search (BM25) ────────────────────────────────────────────────
# Embeddings capture meaning but are weak on exact identifiers such as `statement_descriptor`, `429`
# or `Qx-Retry-In`. BM25 is classic keyword ranking; the two rankings are merged with reciprocal rank fusion.

WORD = re.compile(r"[a-z0-9]+(?:[_+.-][a-z0-9]+)*")
STOPWORDS = frozenset(
    "a an and are as at be by can do does for from how i if in is it its my of on or so that the this to "
    "what when where which who why with you your me we our".split())
BM25_K1, BM25_B = 1.2, 0.75
RRF_K = 60  # standard constant of reciprocal rank fusion


def keywords(text: str) -> list[str]:
    """Lower-case words; identifiers are kept whole and also split, so `card_token` matches "card token"."""
    words = []
    for word in WORD.findall(text.lower()):
        if word in STOPWORDS:
            continue
        words.append(word)
        parts = re.split(r"[_+.-]", word)
        if len(parts) > 1:
            words += [part for part in parts if part and part not in STOPWORDS]
    return words


@lru_cache(maxsize=1)
def _bm25_index() -> tuple[list[str], list[Counter], dict[str, float], float]:
    import math
    ids = _collection().get(include=["documents"])
    docs = [Counter(keywords(text)) for text in ids["documents"]]
    df = Counter(word for doc in docs for word in doc)
    idf = {word: math.log(1 + (len(docs) - n + 0.5) / (n + 0.5)) for word, n in df.items()}
    avg_len = sum(sum(doc.values()) for doc in docs) / len(docs)
    return ids["ids"], docs, idf, avg_len


def bm25_ranking(query: str) -> list[str]:
    """Chunk ids ordered by BM25 score, best first; chunks sharing no keyword with the query are left out."""
    ids, docs, idf, avg_len = _bm25_index()
    terms = set(keywords(query))
    scores = []
    for chunk_id, doc in zip(ids, docs):
        length = sum(doc.values())
        score = sum(idf[t] * doc[t] * (BM25_K1 + 1) / (doc[t] + BM25_K1 * (1 - BM25_B + BM25_B * length / avg_len))
                    for t in terms if t in doc)
        if score > 0:
            scores.append((score, chunk_id))
    return [chunk_id for _, chunk_id in sorted(scores, reverse=True)]


# ── search ───────────────────────────────────────────────────────────────

def retrieve(query: str, k: int = 5, method: str = "hybrid", expand: bool = True) -> list[Chunk]:
    """Return the k pieces of docs/ most relevant to the query, best first.

    method: "hybrid" (default, embeddings + BM25 fused), "vector" (embeddings only) or "bm25" (keywords only).
    expand: small-to-big. Chunks are small so that the embedding model sees all of their text, but a long
            section split into several chunks is returned whole: each result is one heading section, and k
            counts sections. With expand=False each result is a single chunk."""
    if not query.strip():
        raise ValueError("query must not be empty")
    if k < 1:
        raise ValueError("k must be at least 1")
    if method not in ("hybrid", "vector", "bm25"):
        raise ValueError("method must be 'hybrid', 'vector' or 'bm25'")
    collection = _collection()
    # the collection is small (a few hundred chunks), so score all of them: every chunk then has a cosine score
    result = collection.query(query_texts=[query], n_results=collection.count())
    by_id = {chunk_id: (doc, meta, 1 - distance) for chunk_id, doc, meta, distance in zip(
        result["ids"][0], result["documents"][0], result["metadatas"][0], result["distances"][0])}
    vector = result["ids"][0]
    if method == "vector":
        ranked = vector
    elif method == "bm25":
        ranked = bm25_ranking(query)
    else:
        fused = Counter()
        for ranking in (vector, bm25_ranking(query)):
            for rank, chunk_id in enumerate(ranking, 1):
                fused[chunk_id] += 1 / (RRF_K + rank)
        ranked = [chunk_id for chunk_id, _ in fused.most_common()]

    def section(meta: dict) -> tuple[str, str]:
        return meta["section_id"], meta["heading"]

    results, seen = [], set()
    for chunk_id in ranked:
        doc, meta, similarity = by_id[chunk_id]
        if expand:
            if section(meta) in seen:
                continue
            seen.add(section(meta))
            parts = sorted((m["position"], d) for d, m, _ in by_id.values() if section(m) == section(meta))
            first, *rest = [d for _, d in parts]
            doc = "\n\n".join([first, *(d.split("\n\n", 1)[1] for d in rest)])  # drop the repeated title line
        results.append(Chunk(text=doc, section_id=meta["section_id"], heading=meta["heading"],
                             api_version=meta["api_version"], score=round(similarity, 4)))
        if len(results) == k:
            break
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("query", nargs="?", help="question to search for")
    parser.add_argument("-k", type=int, default=5, help="number of chunks to return (default 5)")
    parser.add_argument("--method", default="hybrid", choices=["hybrid", "vector", "bm25"], help="search method")
    parser.add_argument("--build", action="store_true", help="rebuild the index from docs/")
    args = parser.parse_args()
    if not args.build and not args.query:
        parser.print_help()
        return
    if args.build:
        print(f"Indexed {build_index()} chunks from docs/ into {INDEX_DIR.name}/")
    if args.query:
        for rank, chunk in enumerate(retrieve(args.query, args.k, args.method), 1):
            print(f"\n[{rank}] score {chunk.score:.3f} | {chunk.section_id} > {chunk.heading} ({chunk.api_version})")
            print(textwrap.shorten(chunk.text.replace("\n", " "), 280))


if __name__ == "__main__":
    main()
