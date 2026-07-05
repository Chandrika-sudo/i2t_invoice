from app.audit.auditor import run_audit

if __name__ == "__main__":
    result = run_audit("data/raw_invoices/sample.jpg")
    print(result)
