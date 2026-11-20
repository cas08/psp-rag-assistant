#!/usr/bin/env python3
"""Measure retrieval alone, without the LLM: does retrieve(question, k) return the chunks with the evidence?

  python -m eval.retrieval_eval                  # hybrid search (default)
  python -m eval.retrieval_eval --method vector  # embeddings only, for comparison
"""
import argparse

import yaml

from eval.run_eval import QUESTIONS
from rag.retrieve import retrieve

DEPTH = 20
KS = (3, 5, 8)


def evidence_ranks(question: dict, method: str) -> list[int | None]:
    """1-based rank of the first chunk containing each evidence item, or None if not in the top DEPTH."""
    chunks = retrieve(question["question"], DEPTH, method)
    ranks = []
    for alternatives in question.get("evidence", []):
        hit = next((i for i, c in enumerate(chunks, 1) if any(a in c.text for a in alternatives)), None)
        ranks.append(hit)
    return ranks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--method", default="hybrid", choices=["hybrid", "vector", "bm25"])
    args = parser.parse_args()
    questions = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))
    all_ranks = []
    print(f"{'id':4} ranks   question")
    for q in questions:
        ranks = evidence_ranks(q, args.method)
        all_ranks += ranks
        shown = ",".join(str(r) if r else "-" for r in ranks)
        print(f"{q['id']:4} {shown:7} {q['question']}")
    total = len(all_ranks)
    print(f"\n{args.method}: " + "  ".join(f"recall@{k} {sum(1 for r in all_ranks if r and r <= k)}/{total}" for k in KS))


if __name__ == "__main__":
    main()
