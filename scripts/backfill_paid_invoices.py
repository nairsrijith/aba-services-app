"""Backfill invoice payments for legacy Paid invoices that have no InvoicePayment rows.

Usage:
  python scripts/backfill_paid_invoices.py

This script must be run from the project root and will use the Flask app context.
It will only create InvoicePayment rows for invoices where `status == 'Paid'` and
`len(invoice.payments) == 0`. The created payment amount will be the invoice.total_cost
and the payment_date will prefer invoice.paid_date (if present) otherwise today.

Make a DB backup before running this in production.
"""

from datetime import date
import logging
import os
import sys

# Ensure project root is on sys.path so imports work when running this script directly
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app import create_app, db
from app.models import Invoice, InvoicePayment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = create_app()

def main(dry_run=True):
    with app.app_context():
        invoices = Invoice.query.filter(Invoice.status == 'Paid').all()
        logger.info(f'Found {len(invoices)} invoices with status=Paid')
        created = 0
        for inv in invoices:
            if inv.payments:
                logger.debug(f'Skipping invoice {inv.invoice_number}: already has {len(inv.payments)} payments')
                continue
            amount = float(inv.total_cost or 0.0)
            if amount <= 0:
                logger.warning(f'Skipping invoice {inv.invoice_number}: total_cost is {amount}')
                continue
            pay_date = inv.paid_date or date.today()
            logger.info(f'Backfilling payment for {inv.invoice_number}: amount={amount:.2f} date={pay_date}')
            if not dry_run:
                p = InvoicePayment(
                    invoice_id=inv.id,
                    amount=amount,
                    payment_date=pay_date,
                    transaction_number=inv.payment_comments,
                )
                db.session.add(p)
                # mark invoice fields consistently without removing legacy comments
                inv.paid_date = pay_date
                inv.status = 'Paid'
                db.session.commit()
                created += 1
        logger.info(f'Backfill complete. Created {created} payments (dry_run={dry_run})')

if __name__ == '__main__':
    dry = True
    if len(sys.argv) > 1 and sys.argv[1] in ('--run','--apply'):
        dry = False
    logger.info('Running backfill script (dry_run=%s). Use --run to apply changes.' % dry)
    main(dry_run=dry)
