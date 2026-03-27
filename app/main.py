"""
app/main.py — CLI entry point
Usage:
    python -m app.main path/to/invoice.jpg
    python -m app.main   # uses bundled sample
"""
import argparse, json, os, sys
from app.audit.auditor import run_audit
from app.config.settings import RAW_DIR

def main() -> None:
    parser = argparse.ArgumentParser(description="i2t — Invoice Intelligence Toolkit")
    parser.add_argument(
        "image", nargs="?",
        default=os.path.join(RAW_DIR, "sample.jpg"),
        help="Path to invoice image (default: data/raw_invoices/sample.jpg)",
    )
    args = parser.parse_args()
    result = run_audit(args.image)
    print(json.dumps(result, indent=2))
    sys.exit(1 if result["status"] == "REVIEW" else 0)

if __name__ == "__main__":
    main()