"""Invoice reminder utility for sending email reminders for due invoices."""

import logging
import sys
from datetime import datetime, timedelta
from app import db
from app.models import Invoice, Client, AppSettings
from app.utils.email_utils import queue_email
from flask import render_template

logger = logging.getLogger(__name__)

# Ensure logs are visible in container stdout/stderr when not otherwise configured
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def should_send_first_reminder(invoice: Invoice, settings: AppSettings) -> bool:
    """Check if first reminder should be sent for an invoice."""
    if invoice.status == 'Paid':
        return False
    
    days_until_due = (invoice.payby_date - datetime.now().date()).days
    
    # Send if within reminder window and no reminder sent yet
    return (days_until_due <= settings.invoice_reminder_days and 
            days_until_due > 0 and 
            invoice.reminder_count == 0)


def should_send_repeat_reminder(invoice: Invoice, settings: AppSettings) -> bool:
    """Check if repeat reminder should be sent for an invoice."""
    if invoice.status == 'Paid' or not settings.invoice_reminder_repeat_enabled:
        return False
    
    if not invoice.last_reminder_sent_date:
        return False
    
    days_since_last_reminder = (datetime.now() - invoice.last_reminder_sent_date).days
    
    # Send if enough days have passed since last reminder
    return days_since_last_reminder >= settings.invoice_reminder_repeat_days


def send_invoice_reminder(invoice: Invoice, settings: AppSettings) -> bool:
    """Send invoice reminder email to client."""
    try:
        client = invoice.client
        if not client or not client.parentemail:
            logger.warning(f'Invoice {invoice.invoice_number}: No client email found')
            return False
        
        # Prepare email data
        days_until_due = (invoice.payby_date - datetime.now().date()).days
        
        # Determine if this is a repeat reminder
        is_repeat = invoice.reminder_count > 0
        reminder_type = 'Follow-up Reminder' if is_repeat else 'Due Date Reminder'
        
        # Determine status: overdue, due soon, or upcoming
        if days_until_due < 0:
            status = 'overdue'
            days_overdue = abs(days_until_due)
            status_message = f"This invoice is now OVERDUE by {days_overdue} day{'s' if days_overdue != 1 else ''}!"
        elif days_until_due == 0:
            status = 'due_today'
            status_message = "This invoice is DUE TODAY!"
        else:
            status = 'upcoming'
            status_message = f"This invoice is due in {days_until_due} day{'s' if days_until_due != 1 else ''}."
        
        # Render email template
        try:
            body_html = render_template(
                'email/invoice_reminder_email.html',
                client_name=client.parentname,
                invoice_number=invoice.invoice_number,
                invoice_total=invoice.total_cost,
                due_date=invoice.payby_date.strftime('%B %d, %Y'),
                days_until_due=max(days_until_due, 0),
                reminder_type=reminder_type,
                is_repeat=is_repeat,
                status=status,
                status_message=status_message,
                days_overdue=abs(days_until_due) if days_until_due < 0 else 0
            )
            body_text = render_template(
                'email/invoice_reminder_email.txt',
                client_name=client.parentname,
                invoice_number=invoice.invoice_number,
                invoice_total=invoice.total_cost,
                due_date=invoice.payby_date.strftime('%B %d, %Y'),
                days_until_due=max(days_until_due, 0),
                reminder_type=reminder_type,
                is_repeat=is_repeat,
                status=status,
                status_message=status_message,
                days_overdue=abs(days_until_due) if days_until_due < 0 else 0
            )
        except Exception as e:
            logger.exception(f'Error rendering email template for invoice {invoice.invoice_number}: {e}')
            # Fall back to basic text version
            status_text = ''
            if days_until_due < 0:
                status_text = f'This invoice is OVERDUE by {abs(days_until_due)} days!'
            elif days_until_due == 0:
                status_text = 'This invoice is DUE TODAY!'
            else:
                status_text = f'This invoice is due in {days_until_due} days.'
            
            body_text = f"""
Dear {client.parentname},

This is a {reminder_type.lower()} for Invoice {invoice.invoice_number}.

{status_text}

Invoice Details:
Invoice Number: {invoice.invoice_number}
Total Amount: ${invoice.total_cost:.2f}
Due Date: {invoice.payby_date.strftime('%B %d, %Y')}

Please ensure payment is made by the due date.

Thank you,
{settings.org_name or 'Organization'}
"""
            body_html = None
        
        # Send email
        recipients = [client.parentemail]
        if client.parentemail2:
            recipients.append(client.parentemail2)
        
        success = queue_email(
            subject=f'{reminder_type}: Invoice {invoice.invoice_number}',
            recipients=recipients,
            body_text=body_text,
            body_html=body_html
        )
        
        if success:
            # Update invoice tracking
            invoice.last_reminder_sent_date = datetime.now()
            invoice.reminder_count += 1
            db.session.commit()
            logger.info(f'Invoice {invoice.invoice_number}: Reminder sent (count: {invoice.reminder_count})')
            return True
        else:
            logger.error(f'Invoice {invoice.invoice_number}: Failed to queue email')
            return False
            
    except Exception as e:
        logger.exception(f'Error sending invoice reminder: {e}')
        return False


def process_invoice_reminders():
    """Main function to process and send invoice reminders."""
    try:
        settings = AppSettings.get()
        
        if not settings or not settings.invoice_reminder_enabled:
            logger.info('Invoice reminders are disabled')
            return
        
        # Get unpaid invoices that need reminders
        unpaid_invoices = Invoice.query.filter(
            Invoice.status != 'Paid'
        ).all()
        
        reminders_sent = 0
        for invoice in unpaid_invoices:
            # Check for first reminder
            if should_send_first_reminder(invoice, settings):
                if send_invoice_reminder(invoice, settings):
                    reminders_sent += 1
            
            # Check for repeat reminder
            elif should_send_repeat_reminder(invoice, settings):
                if send_invoice_reminder(invoice, settings):
                    reminders_sent += 1
        
        logger.info(f'Processed {len(unpaid_invoices)} unpaid invoices, sent {reminders_sent} reminders')
        
    except Exception as e:
        logger.exception(f'Error in process_invoice_reminders: {e}')
