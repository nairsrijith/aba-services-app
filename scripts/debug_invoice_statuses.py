"""Diagnostic: print invoice status fields to debug 'Pending' showing for paid invoices.

Usage: python scripts/debug_invoice_statuses.py
"""
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app
from app import db
from app.models import Invoice

app = create_app()

with app.app_context():
    invoices = Invoice.query.order_by(Invoice.invoiced_date.desc()).limit(50).all()
    print(f"Found {Invoice.query.count()} invoices (showing up to 50):\n")
    fmt = "{:<18} {:<8} {:<12} {:>10} {:>10} {:>10} {:>8}"
    print(fmt.format("invoice_number","status","paid_date","total_cost","paid_amount","pending","#payments"))
    print("-"*80)
    for inv in invoices:
        paid_date = inv.paid_date.isoformat() if inv.paid_date else ''
        total = float(inv.total_cost or 0.0)
        paid_amt = float(inv.paid_amount or 0.0)
        pending = float(inv.pending_amount or 0.0)
        payments_count = len(inv.payments) if inv.payments else 0
        print(fmt.format(inv.invoice_number, str(inv.status), paid_date, f"{total:.2f}", f"{paid_amt:.2f}", f"{pending:.2f}", payments_count))
    # Also show any invoices where status='Paid' but pending_amount>0
    print('\nInvoices with status=Paid but pending_amount>0:')
    mismatches = Invoice.query.filter(Invoice.status == 'Paid').all()
    problems = [inv for inv in mismatches if inv.pending_amount > 0]
    print(f"Found {len(problems)} mismatches")
    for inv in problems[:20]:
        print(f"{inv.invoice_number}: total={inv.total_cost}, paid_amount={inv.paid_amount}, pending={inv.pending_amount}, payments={len(inv.payments)}")
