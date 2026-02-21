#!/usr/bin/env python
"""
Diagnostic script to debug invoice reminder matching issues.
Run this on your containerized server to identify timezone or date comparison problems.

Usage: python diagnose_reminder_issue.py
Or in Docker: docker exec <container_name> python diagnose_reminder_issue.py
"""
import sys
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# Change to app directory if needed
if os.path.exists('/myapp'):
    os.chdir('/myapp')
    sys.path.insert(0, '/myapp')

try:
    logger.info('=== Invoice Reminder Diagnostic Report ===')
    logger.info(f'Current working directory: {os.getcwd()}')
    logger.info(f'Python version: {sys.version}')
    
    # Initialize Flask app
    from app import create_app, db
    from app.models import Invoice, AppSettings
    
    app = create_app()
    with app.app_context():
        logger.info('\n=== Server Date/Time Information ===')
        current_time = datetime.now()
        current_date = current_time.date()
        
        logger.info(f'Current datetime.now(): {current_time}')
        logger.info(f'Current date (datetime.now().date()): {current_date}')
        logger.info(f'System timezone: {os.environ.get("TZ", "Not set - using system default")}')
        
        # Check AppSettings
        settings = AppSettings.get()
        if not settings:
            logger.warning('No AppSettings found in database')
        else:
            logger.info(f'Invoice Reminders Enabled: {settings.invoice_reminder_enabled}')
            logger.info(f'Invoice Reminder Days (days before due): {settings.invoice_reminder_days}')
            logger.info(f'Repeat Reminders Enabled: {settings.invoice_reminder_repeat_enabled}')
        
        # Check invoices
        logger.info('\n=== Invoices with "Sent" Status ===')
        sent_invoices = Invoice.query.filter(Invoice.status == 'Sent').all()
        
        if not sent_invoices:
            logger.warning('No invoices found with status "Sent"')
        else:
            logger.info(f'Found {len(sent_invoices)} invoices with status "Sent"\n')
            
            for inv in sent_invoices:
                logger.info(f'Invoice: {inv.invoice_number}')
                logger.info(f'  Status: {inv.status}')
                logger.info(f'  Due Date: {inv.payby_date} (type: {type(inv.payby_date).__name__})')
                logger.info(f'  Current Date: {current_date} (type: {type(current_date).__name__})')
                
                # Calculate days until due
                try:
                    days_until_due = (inv.payby_date - current_date).days
                    logger.info(f'  Days Until Due: {days_until_due}')
                except Exception as e:
                    logger.error(f'  Error calculating days until due: {e}')
                    days_until_due = None
                
                logger.info(f'  Reminder Count: {inv.reminder_count}')
                logger.info(f'  Last Reminder Sent: {inv.last_reminder_sent_date}')
                
                # Check conditions
                if settings:
                    if days_until_due is not None:
                        condition1 = inv.status == 'Sent'
                        condition2 = inv.status != 'Paid'
                        condition3 = days_until_due <= settings.invoice_reminder_days
                        condition4 = days_until_due >= 0
                        condition5 = inv.reminder_count == 0
                        
                        logger.info(f'\n  Checking first reminder conditions:')
                        logger.info(f'    Status is "Sent": {condition1}')
                        logger.info(f'    Status is NOT "Paid": {condition2}')
                        logger.info(f'    Days until due ({days_until_due}) <= reminder days ({settings.invoice_reminder_days}): {condition3}')
                        logger.info(f'    Days until due ({days_until_due}) >= 0: {condition4}')
                        logger.info(f'    Reminder count == 0: {condition5}')
                        
                        should_send = condition2 and condition3 and condition4 and condition5
                        logger.info(f'  → Should send FIRST reminder: {should_send}')
                        
                        # Check repeat reminder conditions
                        if not should_send and inv.reminder_count > 0:
                            repeat_condition1 = inv.status != 'Paid'
                            repeat_condition2 = settings.invoice_reminder_repeat_enabled
                            repeat_condition3 = inv.last_reminder_sent_date is not None
                            repeat_condition4 = days_until_due < 0  # Must be overdue
                            
                            if repeat_condition3:
                                days_since_last = (datetime.now() - inv.last_reminder_sent_date).days
                                repeat_condition5 = days_since_last >= settings.invoice_reminder_repeat_days
                            else:
                                days_since_last = None
                                repeat_condition5 = False
                            
                            logger.info(f'\n  Checking repeat reminder conditions:')
                            logger.info(f'    Status is NOT "Paid": {repeat_condition1}')
                            logger.info(f'    Repeat reminders enabled: {repeat_condition2}')
                            logger.info(f'    Last reminder sent date exists: {repeat_condition3}')
                            logger.info(f'    Days until due ({days_until_due}) < 0 (overdue): {repeat_condition4}')
                            if repeat_condition3:
                                logger.info(f'    Days since last reminder ({days_since_last}) >= repeat days ({settings.invoice_reminder_repeat_days}): {repeat_condition5}')
                            
                            should_send_repeat = repeat_condition1 and repeat_condition2 and repeat_condition3 and repeat_condition4 and repeat_condition5
                            logger.info(f'  → Should send REPEAT reminder: {should_send_repeat}')
                logger.info('')
        
        logger.info('\n=== Diagnosis Complete ===')
        logger.info('If no invoices matched above, check:')
        logger.info('1. Do you have any invoices with status "Sent"? (Check the database directly)')
        logger.info('2. Is the server timezone different from where invoices were created?')
        logger.info('3. Are invoice due dates in the past or future relative to server date?')
        logger.info('')
        logger.info('Common issues:')
        logger.info('- Container timezone is UTC, but invoices were created in a different timezone')
        logger.info('- Invoice due date is stored as datetime (not date), causing comparison issues')
        logger.info('- Invoices have reminder_count > 0 but are not overdue for repeat reminders')

except Exception as e:
    logger.exception(f'Error during diagnosis: {e}')
    sys.exit(1)
