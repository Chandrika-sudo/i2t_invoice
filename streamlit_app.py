import streamlit as st
import os
from app.audit.auditor import run_audit

# Page config
st.set_page_config(
    page_title="Autonomous Financial Auditor",
    page_icon="🧾",
    layout="centered"
)

st.title("🧾 Autonomous Financial Auditor")
st.write("Upload an invoice or receipt image to audit it automatically.")

UPLOAD_DIR = "data/raw_invoices"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# File uploader
uploaded_file = st.file_uploader(
    "Upload Invoice / Receipt Image",
    type=["jpg", "jpeg", "png"]
)

if uploaded_file:
    file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)

    # Save uploaded file
    with open(file_path, "wb") as f:
        f.write(uploaded_file.read())

    st.image(file_path, caption="Uploaded Document", use_column_width=True)

    if st.button("🔍 Run Audit"):
        with st.spinner("Analyzing document..."):
            result = run_audit(file_path)

        st.subheader("📄 Extracted Invoice Data")
        st.json(result["invoice_data"])

        st.subheader("🚩 Audit Flags")
        if result["flags"]:
            for flag in result["flags"]:
                st.error(flag)
        else:
            st.success("No issues detected")

        st.subheader("✅ Final Status")
        if result["status"] == "APPROVED":
            st.success("APPROVED")
        else:
            st.warning("REVIEW REQUIRED")
