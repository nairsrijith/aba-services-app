#!/usr/bin/env python
"""
Direct script to trigger invoice reminders without relying on Flask CLI.
Can be called from cron or manually.
"""
import sys
import os
import logging

# Set up logging
log_file = '/var/log/invoice_reminders.log'

# Try to write to /var/log, fall back to /tmp if permission denied
try:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, 'a'):
        pass
except (PermissionError, FileNotFoundError, OSError):
    log_file = '/tmp/invoice_reminders.log'

# Configure logging to both file and console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)
logger.info(f'Invoice reminders log file: {log_file}')

# Change to app directory if needed
if os.path.exists('/myapp'):
    os.chdir('/myapp')
    sys.path.insert(0, '/myapp')

try:
    logger.info('Starting invoice reminders processing...')
    from app import create_app
    from app.utils.invoice_reminder import process_invoice_reminders
    
    # Create app context
    app = create_app()
    with app.app_context():
        process_invoice_reminders()
    
    logger.info('Invoice reminders processing completed successfully')
    sys.exit(0)
    
except Exception as e:
    logger.exception(f'Error processing invoice reminders: {e}')
    sys.exit(1)
