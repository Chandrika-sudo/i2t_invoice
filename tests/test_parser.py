from app.parser.invoice_parser import parse_invoice

def test_parser():
    text = "Invoice No: 123\nVendor: ABC Traders\nTotal: 11800"
    data = parse_invoice(text)
    assert data["invoice_no"] == "123"
