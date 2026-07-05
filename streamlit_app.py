from __future__ import annotations
import io
import os
import tempfile
import csv
import json
from datetime import datetime
from pathlib import Path

import streamlit as st
import numpy as np
from PIL import Image

st.set_page_config(
    page_title="i2t · Invoice Auditor",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    #MainMenu, footer {visibility: hidden;}

    .main .block-container {
        padding-top: 2rem;
        max-width: 1200px;
    }

    .app-title {
        font-size: 2rem;
        font-weight: 800;
        margin-bottom: 0.1rem;
    }
    .app-subtitle {
        color: #6c757d;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }

    .status-approved {
        background: linear-gradient(135deg, #d4edda, #c3e6cb);
        color: #155724;
        padding: 10px 20px;
        border-radius: 10px;
        font-weight: 700;
        font-size: 1rem;
        display: inline-block;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }
    .status-review {
        background: linear-gradient(135deg, #fff3cd, #ffe8a1);
        color: #856404;
        padding: 10px 20px;
        border-radius: 10px;
        font-weight: 700;
        font-size: 1rem;
        display: inline-block;
        box-shadow: 0 2px 6px rgba(0,0,0,0.06);
    }

    .flag-box {
        background: #fff8e6;
        border-left: 4px solid #ffc107;
        padding: 10px 14px;
        margin: 6px 0;
        border-radius: 6px;
        font-size: 0.9rem;
        color: #6b5300;
    }

    .field-card {
        background: #ffffff;
        border: 1px solid #eef0f2;
        border-radius: 10px;
        padding: 14px 16px;
        margin-bottom: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .field-label {
        color: #9aa0a6;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 2px;
    }
    .field-value {
        font-size: 1.05rem;
        font-weight: 600;
        color: #1f2937;
    }
    .field-value.empty {
        color: #b0b5bb;
        font-weight: 500;
        font-style: italic;
    }

    .total-card {
        background: linear-gradient(135deg, #1f2937, #111827);
        color: white;
        border-radius: 14px;
        padding: 20px 24px;
        text-align: center;
        margin-top: 8px;
    }
    .total-card .label {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        opacity: 0.7;
    }
    .total-card .value {
        font-size: 2.2rem;
        font-weight: 800;
        margin-top: 4px;
    }

    section[data-testid="stSidebar"] {
        background: #1f2937;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def _load_pipeline():
    """Import heavy modules lazily so the UI renders before they load."""
    from app.ocr.preprocess import preprocess_image
    from app.ocr.extractor import extract_text
    from app.parser.invoice_parser import parse_invoice
    from app.validation import tax_rules, vendor_rules, duplicate, anomaly
    return preprocess_image, extract_text, parse_invoice, tax_rules, vendor_rules, duplicate, anomaly


def run_on_bytes(raw_bytes: bytes, filename: str, historical_avg: float) -> dict:
    """Save bytes to a temp file and run the full audit pipeline."""
    suffix = Path(filename).suffix or ".jpg"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(raw_bytes)
        tmp_path = tmp.name

    try:
        preprocess_image, extract_text, parse_invoice, tax_rules, vendor_rules, duplicate, anomaly = _load_pipeline()

        img_arr = preprocess_image(tmp_path)
        text = extract_text(img_arr)
        data = parse_invoice(text)

        flags: list[str] = []
        flags += tax_rules.check(data)
        flags += vendor_rules.check(data)
        flags += duplicate.check(data)
        flags += anomaly.check(data, historical_avg=historical_avg)

        status = "REVIEW" if flags else "APPROVED"
        return {"invoice_data": data, "raw_text": text, "flags": flags, "status": status}
    finally:
        os.unlink(tmp_path)


def _field_card(label: str, value, is_currency: bool = False) -> None:
    if value is None or value == "":
        display = "Not detected"
        css_class = "field-value empty"
    else:
        display = f"{value:,.2f}" if is_currency else str(value)
        css_class = "field-value"

    st.markdown(
        f'<div class="field-card">'
        f'<div class="field-label">{label}</div>'
        f'<div class="{css_class}">{display}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/receipt.png", width=56)
    st.markdown("### i2t Invoice Auditor")
    st.caption("Indian GST & UAE VAT · OCR-powered")
    st.divider()

    mode = st.radio("Mode", ["Single Invoice", "Batch (multiple files)"], index=0)
    st.divider()

    historical_avg = st.number_input(
        "Historical avg invoice (₹ / AED)",
        min_value=100.0, max_value=10_000_000.0,
        value=10_000.0, step=500.0,
        help="Used by anomaly detection to flag unusually large invoices.",
    )
    st.divider()
    st.markdown(
        "**What this checks**\n"
        "- Vendor, invoice no., GSTIN/TRN\n"
        "- Date, subtotal, tax, total\n"
        "- Tax arithmetic & rate consistency\n"
        "- Known vendors\n"
        "- Duplicate invoices\n"
        "- Statistical anomalies"
    )

if mode == "Single Invoice":
    st.markdown('<div class="app-title">🧾 Invoice Audit</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Upload an invoice to extract and validate its data automatically.</div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "Upload an invoice image",
        type=["jpg", "jpeg", "png", "tiff", "tif", "bmp"],
        help="Supported: JPG, PNG, TIFF, BMP",
        label_visibility="collapsed",
    )

    if uploaded:
        col_img, col_results = st.columns([1, 1.2], gap="large")

        with col_img:
            st.markdown("#### Preview")
            st.image(uploaded, width="stretch")

        with col_results:
            st.markdown("#### Audit Results")

            with st.spinner("Running OCR pipeline…"):
                try:
                    result = run_on_bytes(uploaded.read(), uploaded.name, historical_avg)
                except Exception as e:
                    st.error(f"Pipeline error: {e}")
                    st.stop()

            inv = result["invoice_data"]
            flags = result["flags"]
            status = result["status"]

            badge_class = "status-approved" if status == "APPROVED" else "status-review"
            st.markdown(
                f'<span class="{badge_class}">{"✅ APPROVED" if status == "APPROVED" else "⚠️ NEEDS REVIEW"}</span>',
                unsafe_allow_html=True,
            )
            st.write("")

            if flags:
                with st.expander(f"🚩 {len(flags)} flag(s) found", expanded=True):
                    for f in flags:
                        st.markdown(f'<div class="flag-box">⚠️ {f}</div>', unsafe_allow_html=True)
            else:
                st.success("No issues detected.")

            st.write("")

            c1, c2 = st.columns(2)
            with c1:
                _field_card("Document Type", inv.get("doc_type"))
                _field_card("Region", inv.get("region"))
                _field_card("Vendor", inv.get("vendor"))
                _field_card("Invoice No.", inv.get("invoice_no"))
            with c2:
                _field_card("Tax ID (GSTIN/TRN)", inv.get("tax_id"))
                _field_card("Date", inv.get("date"))
                _field_card("Subtotal", inv.get("subtotal"), is_currency=True)
                _field_card("Tax", inv.get("tax"), is_currency=True)

            total_val = inv.get("total")
            st.markdown(
                f'<div class="total-card">'
                f'<div class="label">Total Amount</div>'
                f'<div class="value">{f"{total_val:,.2f}" if total_val else "—"}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.write("")
            st.download_button(
                "⬇️ Download JSON",
                data=json.dumps(result["invoice_data"], indent=2),
                file_name=f"invoice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                width="stretch",
            )

else:
    st.markdown('<div class="app-title">📂 Batch Invoice Audit</div>', unsafe_allow_html=True)
    st.markdown('<div class="app-subtitle">Upload multiple invoice images and export results as CSV.</div>', unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Upload invoices",
        type=["jpg", "jpeg", "png", "tiff", "tif", "bmp"],
        accept_multiple_files=True,
        label_visibility="collapsed",
    )

    if uploaded_files and st.button("▶️ Run Batch Audit", type="primary"):
        rows = []
        progress = st.progress(0)
        status_text = st.empty()

        for i, f in enumerate(uploaded_files):
            status_text.text(f"Processing {f.name} ({i+1}/{len(uploaded_files)})…")
            try:
                result = run_on_bytes(f.read(), f.name, historical_avg)
                inv = result["invoice_data"]
                rows.append({
                    "file":       f.name,
                    "status":     result["status"],
                    "vendor":     inv.get("vendor", ""),
                    "invoice_no": inv.get("invoice_no", ""),
                    "tax_id":     inv.get("tax_id", ""),
                    "date":       inv.get("date", ""),
                    "region":     inv.get("region", ""),
                    "subtotal":   inv.get("subtotal", ""),
                    "tax":        inv.get("tax", ""),
                    "total":      inv.get("total", ""),
                    "flags":      " | ".join(result["flags"]),
                })
            except Exception as e:
                rows.append({"file": f.name, "status": "ERROR", "flags": str(e)})

            progress.progress((i + 1) / len(uploaded_files))

        status_text.text("Done!")
        progress.empty()

        approved = sum(1 for r in rows if r.get("status") == "APPROVED")
        review = sum(1 for r in rows if r.get("status") == "REVIEW")
        errored = sum(1 for r in rows if r.get("status") == "ERROR")

        m1, m2, m3 = st.columns(3)
        m1.metric("✅ Approved", approved)
        m2.metric("⚠️ Needs Review", review)
        m3.metric("❌ Errors", errored)

        st.dataframe(rows, width="stretch")

        buf = io.StringIO()
        if rows:
            writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

        st.download_button(
            "⬇️ Download CSV summary",
            data=buf.getvalue(),
            file_name=f"batch_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            width="stretch",
        )