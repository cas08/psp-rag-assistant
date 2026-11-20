"""The agreed interface: answer(question, use_rag) -> str.

`ask()` returns the same answer plus the retrieved chunks and timing, for the UI and the evaluation.
"""
import time
from dataclasses import dataclass, field

from assistant import llm, prompts
from rag.retrieve import Chunk, retrieve

DEFAULT_K = 5


@dataclass
class Answer:
    question: str
    text: str
    use_rag: bool
    model: str
    seconds: float
    chunks: list[Chunk] = field(default_factory=list)


def ask(question: str, use_rag: bool = True, k: int = DEFAULT_K, model: str = llm.OLLAMA_MODEL) -> Answer:
    question = question.strip()
    if not question:
        raise ValueError("question must not be empty")
    started = time.perf_counter()
    if use_rag:
        chunks = retrieve(question, k)
        text = llm.chat(prompts.RAG_SYSTEM, prompts.rag_user_message(question, chunks), model=model)
    else:
        chunks = []
        text = llm.chat(prompts.NO_RAG_SYSTEM, prompts.no_rag_user_message(question), model=model)
    return Answer(question, text, use_rag, model, round(time.perf_counter() - started, 2), chunks)


def answer(question: str, use_rag: bool) -> str:
    """Contract between person A and person B."""
    return ask(question, use_rag).text
