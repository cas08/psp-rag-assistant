#!/usr/bin/env python3
"""Run the test set through both modes (RAG / no RAG) and build the comparison table.

  python -m eval.run_eval                       # run all questions, write eval/results/<time>/
  python -m eval.run_eval --only q05 q10        # run a subset
  python -m eval.run_eval --no-judge            # skip the LLM draft verdict
  python -m eval.run_eval --summarize eval/results/<time>/results.csv   # re-count after manual grading

What it writes:
  results.csv  one row per question x mode. Fill the column `verdict_manual` with
               correct / partial / hallucinated and `invented_manual` with yes / no, then run --summarize.
  report.md    summary table + every answer, ready to paste into slides.

Automatic helpers (hints, not final grades):
  facts_found      share of key facts from questions.yaml found in the answer
  invented         endpoints / headers / `identifiers` in the answer that appear nowhere in docs/
  verdict_judge    draft verdict from the LLM given the reference answer
"""
import argparse
import csv
import re
from collections import Counter
from datetime import datetime
from functools import lru_cache
from pathlib import Path

import yaml

from assistant import ask, llm

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "eval" / "questions.yaml"
RESULTS_DIR = ROOT / "eval" / "results"
VERDICTS = ("correct", "partial", "hallucinated")
COLUMNS = ["id", "mode", "question", "reference", "answer", "seconds", "sources", "facts_found",
           "invented", "verdict_judge", "verdict_manual", "invented_manual", "comment"]


# ── invented endpoint / parameter detector ───────────────────────────────

ID_SEGMENT = re.compile(r"^(\{[^}]*\}|:\w+|<[^>]*>|[a-z]+_(?=\w*\d)\w+|\d+)$")  # {id}, :id, <id>, pmt_01J…, 42
METHOD_PATH = re.compile(r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+`?(?:https?://[^\s/`]+)?(/[^\s`'\")?,]+)")
API_URL_PATH = re.compile(r"https?://[^\s/`'\"]*qorvex[^\s/`'\"]*(/[^\s`'\")?,]*)")
CODE_PATH = re.compile(r"`(/[a-z0-9_{}/.-]+)`")
HEADER = re.compile(r"\b((?:Qx|X)-[A-Za-z][A-Za-z-]*|Authorization:\s*Bearer|Retry-After)\b")
CODE_TOKEN = re.compile(r"`([a-z][a-z0-9_.]*[_.][a-z0-9_.]+)`")  # snake_case / dotted, e.g. `card_token`, `payment.captured`


def normalize_path(path: str) -> str:
    segments = [s for s in path.split("?")[0].rstrip("/.").split("/") if s]
    return "/" + "/".join("{id}" if ID_SEGMENT.match(s) else s for s in segments)


def extract_paths(text: str) -> set[str]:
    found = set()
    for pattern in (METHOD_PATH, API_URL_PATH, CODE_PATH):
        found.update(normalize_path(m) for m in pattern.findall(text))
    return {p for p in found if p != "/"}


@lru_cache(maxsize=1)
def docs_vocabulary() -> tuple[str, set[str]]:
    text = "\n".join(p.read_text(encoding="utf-8") for p in sorted((ROOT / "docs").glob("*.md")))
    return text, extract_paths(text)


def invented_terms(answer: str) -> list[str]:
    """Endpoints, headers and code identifiers from the answer that do not exist anywhere in docs/."""
    docs_text, docs_paths = docs_vocabulary()
    invented = {f"endpoint {p}" for p in extract_paths(answer) if p not in docs_paths}
    invented |= {f"header {h}" for h in HEADER.findall(answer) if h not in docs_text}
    invented |= {f"`{t}`" for t in CODE_TOKEN.findall(answer) if t not in docs_text}
    return sorted(invented)


def facts_found(answer: str, facts: list[list[str]]) -> str:
    low = answer.lower()
    hits = sum(any(alt.lower() in low for alt in fact) for fact in facts)
    return f"{hits}/{len(facts)}"


# ── LLM draft verdict ────────────────────────────────────────────────────

JUDGE_SYSTEM = """You grade answers about a fictional payments API against a reference answer.
Reply with exactly one word:
correct      - the answer agrees with the reference on all key facts and adds nothing false
partial      - some key facts are right, but something important is missing or vague, nothing clearly false
hallucinated - the answer states something false or invented: wrong numbers, endpoints, parameters, headers or behaviour
An answer that honestly says it does not know is "partial", not "hallucinated"."""


def judge(question: str, reference: str, answer: str) -> str:
    reply = llm.chat(JUDGE_SYSTEM, f"Question: {question}\n\nReference answer: {reference}\n\nAnswer to grade:\n{answer}")
    word = reply.strip().split()[0].strip(".:*\"'").lower() if reply.strip() else ""
    return word if word in VERDICTS else f"? {reply[:40]}"


# ── run and report ───────────────────────────────────────────────────────

def run(questions: list[dict], use_judge: bool, k: int) -> list[dict]:
    rows = []
    for q in questions:
        for use_rag in (True, False):
            mode = "rag" if use_rag else "no_rag"
            print(f"{q['id']} {mode:6} … ", end="", flush=True)
            result = ask(q["question"], use_rag, k)
            invented = invented_terms(result.text)
            row = {
                "id": q["id"], "mode": mode, "question": q["question"], "reference": q["reference"],
                "answer": result.text, "seconds": result.seconds,
                "sources": ", ".join(f"{c.section_id}>{c.heading}" for c in result.chunks),
                "facts_found": facts_found(result.text, q.get("facts", [])),
                "invented": "; ".join(invented),
                "verdict_judge": judge(q["question"], q["reference"], result.text) if use_judge else "",
                "verdict_manual": "", "invented_manual": "", "comment": "",
            }
            rows.append(row)
            print(f"{result.seconds}s facts {row['facts_found']} judge {row['verdict_judge'] or '-'}"
                  + (f" INVENTED {row['invented']}" if invented else ""))
    return rows


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: opens cleanly in Excel / Numbers
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def final_verdict(row: dict) -> str:
    return (row.get("verdict_manual") or "").strip().lower() or (row.get("verdict_judge") or "").strip().lower()


def summary_table(rows: list[dict]) -> str:
    manual = any((r.get("verdict_manual") or "").strip() for r in rows)
    lines = [
        f"Verdicts: {'manual where filled, otherwise LLM judge' if manual else 'LLM judge draft (not yet checked by people)'}",
        "",
        "| Mode | Correct | Partial | Hallucinated | Answers with invented endpoint/parameter | Avg facts found | Avg time, s |",
        "|---|---|---|---|---|---|---|",
    ]
    for mode, label in (("rag", "RAG"), ("no_rag", "No RAG")):
        mode_rows = [r for r in rows if r["mode"] == mode]
        if not mode_rows:
            continue
        counts = Counter(final_verdict(r) for r in mode_rows)
        invented = sum(
            ((r.get("invented_manual") or "").strip().lower() in ("yes", "так", "y", "1"))
            if (r.get("invented_manual") or "").strip() else bool(r["invented"])
            for r in mode_rows)
        facts = [tuple(map(int, r["facts_found"].split("/"))) for r in mode_rows if "/" in r["facts_found"]]
        share = sum(h for h, _ in facts) / max(1, sum(t for _, t in facts))
        avg_time = sum(float(r["seconds"]) for r in mode_rows) / len(mode_rows)
        n = len(mode_rows)
        lines.append(f"| {label} | {counts['correct']}/{n} | {counts['partial']}/{n} | {counts['hallucinated']}/{n} "
                     f"| {invented}/{n} | {share:.0%} | {avg_time:.1f} |")
    return "\n".join(lines)


def per_question_table(rows: list[dict]) -> str:
    by_id: dict[str, dict] = {}
    for r in rows:
        by_id.setdefault(r["id"], {"question": r["question"]})[r["mode"]] = r
    lines = ["| # | Question | RAG | No RAG | Invented without RAG | Comment on the no-RAG answer |", "|---|---|---|---|---|---|"]
    for qid, item in by_id.items():
        rag, no = item.get("rag", {}), item.get("no_rag", {})
        lines.append(f"| {qid} | {item['question']} | {final_verdict(rag) if rag else ''} | "
                     f"{final_verdict(no) if no else ''} | {(no.get('invented') or '').replace('|', '/')} "
                     f"| {(no.get('comment') or '').replace('|', '/')} |")
    return "\n".join(lines)


def write_report(rows: list[dict], path: Path) -> None:
    parts = [f"# Evaluation: RAG vs no RAG\n\nModel: `{llm.OLLAMA_MODEL}` · {datetime.now():%Y-%m-%d %H:%M}\n",
             "## Summary\n", summary_table(rows), "\n## Per question\n", per_question_table(rows), "\n## Answers\n"]
    for r in rows:
        parts.append(f"### {r['id']} · {'RAG' if r['mode'] == 'rag' else 'No RAG'} · {final_verdict(r) or '—'}\n\n"
                     f"**Q:** {r['question']}\n\n**Reference:** {r['reference']}\n\n**Answer:**\n\n{r['answer']}\n\n"
                     f"facts found: {r['facts_found']} · invented: {r['invented'] or '—'}\n")
    path.write_text("\n".join(parts), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="*", help="question ids to run, e.g. q01 q05")
    parser.add_argument("--no-judge", action="store_true", help="skip the LLM draft verdict")
    parser.add_argument("-k", type=int, default=5, help="chunks to retrieve in RAG mode")
    parser.add_argument("--summarize", type=Path, help="re-build report.md from an edited results.csv")
    args = parser.parse_args()

    if args.summarize:
        rows = read_csv(args.summarize)
        write_report(rows, args.summarize.with_name("report.md"))
        print(summary_table(rows))
        return

    questions = yaml.safe_load(QUESTIONS.read_text(encoding="utf-8"))
    if args.only:
        questions = [q for q in questions if q["id"] in args.only]
    out_dir = RESULTS_DIR / datetime.now().strftime("%Y-%m-%d_%H-%M")
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = run(questions, not args.no_judge, args.k)
    write_csv(rows, out_dir / "results.csv")
    write_report(rows, out_dir / "report.md")
    print(f"\n{summary_table(rows)}\n\nWrote {out_dir.relative_to(ROOT)}/results.csv and report.md")


if __name__ == "__main__":
    main()
