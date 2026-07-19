import os
import unittest
from datetime import date

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app import create_app, db
from app.models import Client, Invoice, InvoicePayment


class InvoicePaymentTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'connect_args': {'check_same_thread': False}}
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.drop_all()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_partial_payments_update_status_and_balance(self):
        client = Client(
            firstname='Jane',
            lastname='Doe',
            dob=date(1990, 1, 1),
            gender='Female',
            address1='123 Main St',
            address2='',
            city='Toronto',
            state='ON',
            zipcode='M1M1M1',
            supervisor_id=None,
            parent_firstname='John',
            parent_lastname='Doe',
            parent_email='parent@example.com',
            parent_cell='5555555555',
            cost_supervision=0.0,
            cost_therapy=0.0,
            is_active=True,
        )
        db.session.add(client)
        db.session.flush()

        invoice = Invoice(
            invoice_number='INVTEST0001',
            invoiced_date=date(2026, 7, 1),
            payby_date=date(2026, 7, 8),
            client_id=client.id,
            date_from=date(2026, 6, 1),
            date_to=date(2026, 6, 30),
            total_cost=100.0,
            status='Sent',
            paid_date=None,
            payment_comments='',
            invoice_items='[]',
        )
        db.session.add(invoice)
        db.session.flush()

        invoice.add_payment(amount=40.0, payment_date=date(2026, 7, 2), transaction_number='TXN-001')
        db.session.commit()

        self.assertEqual(invoice.payment_status, 'Partially Paid')
        self.assertEqual(invoice.paid_amount, 40.0)
        self.assertEqual(invoice.pending_amount, 60.0)
        self.assertEqual(InvoicePayment.query.count(), 1)

        invoice.add_payment(amount=60.0, payment_date=date(2026, 7, 5), transaction_number='TXN-002')
        db.session.commit()

        self.assertEqual(invoice.payment_status, 'Paid')
        self.assertEqual(invoice.paid_amount, 100.0)
        self.assertEqual(invoice.pending_amount, 0.0)
        self.assertEqual(InvoicePayment.query.count(), 2)

    def test_reset_to_draft_clears_payments_and_restores_balance(self):
        client = Client(
            firstname='Jane',
            lastname='Doe',
            dob=date(1990, 1, 1),
            gender='Female',
            address1='123 Main St',
            address2='',
            city='Toronto',
            state='ON',
            zipcode='M1M1M1',
            supervisor_id=None,
            parent_firstname='John',
            parent_lastname='Doe',
            parent_email='parent@example.com',
            parent_cell='5555555555',
            cost_supervision=0.0,
            cost_therapy=0.0,
            is_active=True,
        )
        db.session.add(client)
        db.session.flush()

        invoice = Invoice(
            invoice_number='INVTEST0002',
            invoiced_date=date(2026, 7, 1),
            payby_date=date(2026, 7, 8),
            client_id=client.id,
            date_from=date(2026, 6, 1),
            date_to=date(2026, 6, 30),
            total_cost=100.0,
            status='Sent',
            paid_date=None,
            payment_comments='',
            invoice_items='[]',
        )
        db.session.add(invoice)
        db.session.flush()

        invoice.add_payment(amount=40.0, payment_date=date(2026, 7, 2), transaction_number='TXN-001')
        db.session.commit()

        invoice.reset_to_draft()
        db.session.commit()

        self.assertEqual(invoice.status, 'Draft')
        self.assertIsNone(invoice.paid_date)
        self.assertEqual(invoice.payment_comments, '')
        self.assertEqual(invoice.paid_amount, 0.0)
        self.assertEqual(invoice.pending_amount, 100.0)
        self.assertEqual(invoice.payment_status, 'Pending')
        self.assertEqual(InvoicePayment.query.filter_by(invoice_id=invoice.id).count(), 0)


if __name__ == '__main__':
    unittest.main()
