"""CLI: python -m assistant "How long is the refund window?" [--no-rag] [--compare] [-k 5]"""
import argparse
import textwrap

from assistant.core import DEFAULT_K, ask


def show(answer, show_sources: bool) -> None:
    mode = "RAG" if answer.use_rag else "NO RAG"
    print(f"\n=== {mode} · {answer.model} · {answer.seconds}s ===\n{answer.text}")
    if show_sources and answer.chunks:
        print("\nSources:")
        for c in answer.chunks:
            print(f"  {c.score:.3f}  {c.section_id} > {c.heading}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the Qorvex Pay docs assistant.")
    parser.add_argument("question", nargs="?", help="question; omit for interactive mode")
    parser.add_argument("--no-rag", action="store_true", help="ask the model without documentation")
    parser.add_argument("--compare", action="store_true", help="show both modes one after another")
    parser.add_argument("-k", type=int, default=DEFAULT_K, help=f"chunks to retrieve (default {DEFAULT_K})")
    parser.add_argument("--sources", action="store_true", help="list retrieved chunks")
    args = parser.parse_args()

    modes = [True, False] if args.compare else [not args.no_rag]

    def run(question: str) -> None:
        for use_rag in modes:
            show(ask(question, use_rag, args.k), args.sources)

    if args.question:
        run(args.question)
        return
    print(textwrap.dedent("""\
        Qorvex Pay docs assistant. Empty line or Ctrl-D to quit."""))
    while True:
        try:
            question = input("\n? ").strip()
        except EOFError:
            break
        if not question:
            break
        run(question)


if __name__ == "__main__":
    main()
