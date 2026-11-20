"""Streamlit UI: streamlit run app.py"""
import re
from pathlib import Path

import streamlit as st
import yaml

from assistant import ask, llm
from assistant.llm import LLMError

HEADING_LINE = re.compile(r"^#{1,6} +(.*)$")


def fragment_markdown(text: str) -> str:
    """Docs fragment as markdown: drop the "Page > heading" line (already shown in the title)
    and turn headings into bold lines so they do not outshout the answer. Tables and code render as is."""
    body = text.split("\n\n", 1)[1] if "\n\n" in text else text
    lines, in_code = [], False
    for line in body.splitlines():
        if line.startswith("```"):
            in_code = not in_code
        match = None if in_code else HEADING_LINE.match(line)
        lines.append(f"**{match.group(1)}**" if match else line)
    return "\n".join(lines).strip()


QUESTIONS = yaml.safe_load((Path(__file__).parent / "eval" / "questions.yaml").read_text(encoding="utf-8"))

st.set_page_config(page_title="Qorvex Pay docs assistant", page_icon="💳", layout="wide")
st.title("Qorvex Pay docs assistant")
st.caption(f"Local model `{llm.OLLAMA_MODEL}` via Ollama · retrieval over docs/ with Chroma")

with st.sidebar:
    mode = st.radio("Mode", ["Compare both", "RAG", "No RAG"])
    k = st.slider("Sections to retrieve (k)", 1, 10, 5,
                  help="How many of the most relevant documentation sections are added to the prompt (RAG mode only).")
    temperature = st.slider("Temperature", 0.0, 1.5, 0.0, 0.1,
                            help="Randomness of the model's word choice. 0 = same answer every time; "
                                 "higher = more varied and 'creative'. It does not limit the model to the docs — "
                                 "the prompt and the retrieved context do that.")
    example = st.selectbox("Example question", ["—"] + [q["question"] for q in QUESTIONS])
    reference = next((q["reference"] for q in QUESTIONS if q["question"] == example), None)

question = st.text_area("Question", value="" if example == "—" else example, height=80)


def render(use_rag: bool) -> None:
    st.subheader("With RAG" if use_rag else "Without RAG")
    with st.spinner("Thinking…"):
        try:
            result = ask(question, use_rag, k, temperature=temperature)
        except LLMError as exc:
            st.error(str(exc))
            return
    st.markdown(result.text)
    st.caption(f"{result.seconds} s · temperature {temperature}")
    if result.chunks:
        with st.expander(f"Retrieved fragments ({len(result.chunks)})"):
            for i, c in enumerate(result.chunks):
                if i:
                    st.divider()
                st.caption(f"{c.section_id} › {c.heading} · score {c.score:.3f}")
                st.markdown(fragment_markdown(c.text))


_, button_column = st.columns([6, 1])
with button_column:
    clicked = st.button("Ask", type="primary", disabled=not question.strip(), use_container_width=True)

if clicked:
    if mode == "Compare both":
        left, right = st.columns(2)
        with left:
            render(True)
        with right:
            render(False)
    else:
        render(mode == "RAG")
    if reference and question.strip() == example:  # only while the example question is unchanged
        st.info(f"**Reference answer:** {reference}")
