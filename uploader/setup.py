import os, json, magic, requests, streamlit as st

UPLOAD_DIR  = "/tmp/uploads"
REPORTS_DIR = "/sandbox-output"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def dispatch_to_queue(fname: str):
    try:
        resp = requests.post(
            "http://dispatcher:8000/dispatch",
            json={"filename": fname},
            timeout=2
        )
        resp.raise_for_status()
        st.info("✅ Dispatched for sandboxing.")
    except Exception as e:
        st.warning(f"Could not notify dispatcher: {e}")

def file_upload():
    st.header("🔼 Upload an ELF binary")
    uploaded = st.file_uploader(
        "Choose an ELF binary to upload",
        accept_multiple_files=False,
        label_visibility="visible"  # or "collapsed"
    )
    if uploaded:
        file_type = magic.from_buffer(uploaded.read(2048)).split(",")[0]
        uploaded.seek(0)
        st.text(file_type)

        if st.button("Upload"):
            if "ELF" not in file_type:
                st.error("That doesn’t look like an ELF.")
            else:
                dest = os.path.join(UPLOAD_DIR, uploaded.name)
                with open(dest, "wb") as f:
                    f.write(uploaded.read())
                os.chmod(dest, 0o755)
                st.success(f"Saved `{uploaded.name}`")
                dispatch_to_queue(uploaded.name)

def file_download():
    st.header("🔍 Generated Reports")

    # Debug info
    st.write(
        "▶️ Debug — REPORTS_DIR exists?",
        os.path.isdir(REPORTS_DIR),
        "Contents:",
        os.listdir(REPORTS_DIR) if os.path.isdir(REPORTS_DIR) else "n/a",
    )

    if not os.path.isdir(REPORTS_DIR):
        return st.warning(f"Reports folder not found: {REPORTS_DIR}")

    # Recursively collect all .json/.md under REPORTS_DIR
    reports = []
    for root, _, files in os.walk(REPORTS_DIR):
        for fname in files:
            if fname.endswith((".json", ".md")):
                full_path = os.path.join(root, fname)
                # Show a nice relative path, e.g. "20250807T125248_malicious/report.json"
                rel_path = os.path.relpath(full_path, REPORTS_DIR)
                reports.append(rel_path)

    if not reports:
        return st.info("No reports available yet.")

    reports.sort()
    choice = st.selectbox("Select a report", ["<none>"] + reports)
    if choice == "<none>":
        return

    # Load the selected report
    path = os.path.join(REPORTS_DIR, choice)
    with st.spinner(f"Loading {choice}…"):
        raw = open(path, "r").read()

    st.subheader(choice)
    if choice.endswith(".json"):
        obj = json.loads(raw)
        st.json(obj)
        st.download_button(
            label="Download JSON",
            data=raw,
            file_name=os.path.basename(choice),
            mime="application/json",
        )
    else:
        st.markdown(raw)
        st.download_button(
            label="Download Markdown",
            data=raw,
            file_name=os.path.basename(choice),
            mime="text/markdown",
        )


if __name__ == "__main__":
    tab1, tab2 = st.tabs(["Upload", "Reports"])
    with tab1:
        file_upload()
    with tab2:
        file_download()
