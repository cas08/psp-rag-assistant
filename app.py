"""Streamlit UI: streamlit run app.py"""
from pathlib import Path

import streamlit as st
import yaml

from assistant import ask, llm
from assistant.llm import LLMError

QUESTIONS = yaml.safe_load((Path(__file__).parent / "eval" / "questions.yaml").read_text(encoding="utf-8"))

st.set_page_config(page_title="Qorvex Pay docs assistant", page_icon="💳", layout="wide")
st.title("Qorvex Pay docs assistant")
st.caption(f"Local model `{llm.OLLAMA_MODEL}` via Ollama · retrieval over docs/ with Chroma")

with st.sidebar:
    mode = st.radio("Mode", ["Compare both", "RAG", "No RAG"])
    k = st.slider("Chunks to retrieve (k)", 1, 10, 5)
    example = st.selectbox("Example question", ["—"] + [q["question"] for q in QUESTIONS])
    reference = next((q["reference"] for q in QUESTIONS if q["question"] == example), None)

question = st.text_area("Question", value="" if example == "—" else example, height=80)


def render(use_rag: bool) -> None:
    st.subheader("With RAG" if use_rag else "Without RAG")
    with st.spinner("Thinking…"):
        try:
            result = ask(question, use_rag, k)
        except LLMError as exc:
            st.error(str(exc))
            return
    st.markdown(result.text)
    st.caption(f"{result.seconds} s")
    if result.chunks:
        with st.expander(f"Retrieved fragments ({len(result.chunks)})"):
            for c in result.chunks:
                st.markdown(f"**{c.section_id} › {c.heading}** · score {c.score:.3f}")
                st.text(c.text)


if st.button("Ask", type="primary", disabled=not question.strip()):
    if mode == "Compare both":
        left, right = st.columns(2)
        with left:
            render(True)
        with right:
            render(False)
    else:
        render(mode == "RAG")
    if reference:
        st.info(f"**Reference answer:** {reference}")
