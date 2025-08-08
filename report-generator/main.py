# main.py

import os
import tempfile
import logging
import json
from typing import List

import streamlit as st

from ingestion import ingest
from chunker import make_chunks
from llm_client import OpenAIClient, GoogleClient
from cost_estimator import estimate_cost
import re

# ─── Logging Configuration ─────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def aggregate_findings(json_responses: List[str]):
    """
    Turn list of JSON-encoded responses into a de-duped, sorted list of findings.
    Each response is expected to be a JSON array of items with keys:
      - "chunk" (int)
      - "section" (str)
      - "issue" (str)
      - "recommendation" (str)
    """
    rows = []
    for idx, resp in enumerate(json_responses, start=1):
        try:
            items = json.loads(resp)
        except json.JSONDecodeError:
            logger.warning(f"Chunk {idx} returned invalid JSON, skipping.")
            continue
        for it in items:
            # ensure chunk index
            it.setdefault("chunk", idx)
            rows.append(it)

    # de-dupe based on (section,issue,recommendation)
    unique = []
    seen = set()
    for r in rows:
        key = (r.get("section"), r.get("issue"), r.get("recommendation"))
        if key not in seen:
            seen.add(key)
            unique.append(r)

    # sort by chunk then section
    unique.sort(key=lambda r: (r.get("chunk"), r.get("section", "")))
    return unique

def main():
    st.set_page_config(page_title="LLM Report Pipeline", layout="wide")
    st.title("📄🔗 LLM Report Pipeline")

    # ─── Sidebar: Chunking Settings ────────────────────────────────────────────
    st.sidebar.header("Chunking Settings")
    max_tokens = st.sidebar.number_input(
        "Max tokens per chunk", min_value=100, max_value=8000, value=1000, step=100
    )
    overlap = st.sidebar.number_input(
        "Token overlap",    min_value=0,   max_value=2000, value=200,  step=50
    )

    # ─── Sidebar: LLM Provider Settings ───────────────────────────────────────
    st.sidebar.header("LLM Provider")
    provider = st.sidebar.selectbox("Provider", ["OpenAI", "Google"])
    if provider == "OpenAI":
        openai_key = st.sidebar.text_input("OpenAI API Key", type="password")
        model = st.sidebar.selectbox("OpenAI Model", ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"])
        if openai_key:
            os.environ["OPENAI_API_KEY"] = openai_key
    else:
        google_key = st.sidebar.text_input("Google/Gemini API Key", type="password")
        model = st.sidebar.selectbox(
            "Google Model",
            ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.5-flash-lite", "gemini-2.0-flash"]
        )
        if google_key:
            os.environ["GEMINI_API_KEY"] = google_key
            os.environ["GOOGLE_API_KEY"] = google_key

    # ─── File Upload ───────────────────────────────────────────────────────────
    uploaded = st.file_uploader("Upload report (.md or .json)", type=["md", "json"])
    if not uploaded:
        st.info("Please upload a Markdown or JSON report to continue.")
        return

    # Save to a temp file
    suffix = os.path.splitext(uploaded.name)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded.getvalue())
        tmp_path = tmp.name
    logger.info(f"Saved uploaded file to {tmp_path}")

    # ─── Ingestion ─────────────────────────────────────────────────────────────
    try:
        data = ingest(tmp_path)
        dtype = "Markdown" if isinstance(data, str) else "JSON snippets"
        st.success(f"Ingested file as **{dtype}**.")
        logger.info(f"Ingested file as {dtype}")
    except Exception as e:
        st.error(f"Ingestion error: {e}")
        logger.exception("Failed to ingest file")
        return

    # ─── Preview Chunks ────────────────────────────────────────────────────────
    if st.button("Preview Chunks"):
        try:
            chunks = make_chunks(data, max_tokens, overlap)
            st.write(f"Generated **{len(chunks)}** chunks.")
            for i, chunk in enumerate(chunks[:3], start=1):
                with st.expander(f"Chunk {i}"):
                    st.code(chunk, language="")
            logger.info(f"Previewed {min(3, len(chunks))} chunks")
        except Exception as e:
            st.error(f"Chunking error: {e}")
            logger.exception("Failed to chunk data")
            return

    # ─── Estimate Cost ─────────────────────────────────────────────────────────
    if st.button("Estimate Cost"):
        try:
            chunks = make_chunks(data, max_tokens, overlap)
            _, total_cost = estimate_cost(chunks, model, provider)
            st.write(f"**Provider:** {provider}  •  **Model:** {model}")
            st.write(f"**Estimated cost:** ${total_cost:.4f} USD")
            logger.info(f"Cost estimate for {provider}/{model}: ${total_cost:.4f}")
        except Exception as e:
            st.error(f"Cost estimation error: {e}")
            logger.exception("Failed to estimate cost")
            return

    # ─── Run Analysis & Post-Process ───────────────────────────────────────────
    if st.button("Run Analysis"):
        try:
            chunks = make_chunks(data, max_tokens, overlap)
            client = OpenAIClient(model=model) if provider == "OpenAI" else GoogleClient(model=model)

            raw_json_responses = []
            progress = st.progress(0)
            total = len(chunks)

            for idx, chunk in enumerate(chunks, start=1):
                st.write(f"Processing chunk {idx}/{total}…")
                logger.info(f"Sending chunk {idx}/{total} to {provider}")

                resp = client.send_chunk(chunk)

                # 1) Strip code fences like ```json …```
                cleaned = resp.strip()
                cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)   # remove leading ``` or ```json
                cleaned = re.sub(r"\s*```$", "", cleaned)            # remove trailing ```
                cleaned = cleaned.strip()

                # 2) Parse JSON
                try:
                    items = json.loads(cleaned)
                except json.JSONDecodeError:
                    logger.warning(f"Chunk {idx} returned invalid JSON, raw was:\n{cleaned}")
                    continue

                # 3) Inject the real chunk index
                for it in items:
                    it["chunk"] = idx

                raw_json_responses.append(items)
                progress.progress(idx / total)

            # 4) Flatten list of lists, de-duplicate, and sort
            all_findings = []
            seen = set()
            for items in raw_json_responses:
                for r in items:
                    key = (r["section"], r["issue"], r["recommendation"])
                    if key not in seen:
                        seen.add(key)
                        all_findings.append(r)
            all_findings.sort(key=lambda r: (r["chunk"], r["section"]))

            # 5) Display one consolidated table
            st.subheader("🔍 Consolidated Findings")
            if all_findings:
                display = [
                    {"Section": f["section"], "Issue": f["issue"], "Recommendation": f["recommendation"]}
                    for f in all_findings
                ]
                st.table(display)
            else:
                st.info("No valid findings extracted.")

            logger.info("Analysis complete and findings displayed.")

        except Exception as e:
            st.error(f"Analysis error: {e}")
            logger.exception("Analysis pipeline failed")

if __name__ == "__main__":
    main()
