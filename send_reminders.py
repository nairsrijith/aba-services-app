#!/usr/bin/env python
"""
Direct script to trigger invoice reminders without relying on Flask CLI.
Can be called from cron or manually.
"""
import sys
import os
import logging

# Set up logging with careful handler management
log_file = '/var/log/invoice_reminders.log'

# Try to write to /var/log, fall back to /tmp if permission denied
try:
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    with open(log_file, 'a'):
        pass
except (PermissionError, FileNotFoundError, OSError):
    log_file = '/tmp/invoice_reminders.log'

# Get root logger and clear any existing handlers to prevent duplicates
root_logger = logging.getLogger()
for handler in root_logger.handlers[:]:
    root_logger.removeHandler(handler)

# Configure logging - only use file handler since stdout is redirected to the same file
formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s')
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.INFO)

root_logger.addHandler(file_handler)
root_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)
logger.info(f'Invoice reminders log file: {log_file}')

# Change to app directory if needed
if os.path.exists('/myapp'):
    os.chdir('/myapp')
    sys.path.insert(0, '/myapp')

try:
    logger.info('Starting invoice reminders processing...')
    from app import create_app, db
    from app.utils.invoice_reminder import process_invoice_reminders
    
    # Create app context
    app = create_app()
    
    # Log the database URL being used (obscure credentials for security)
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'not configured')
    if 'password' in db_uri.lower():
        # Obscure password for logging
        db_uri = 'postgres://***:***@...' if 'postgres' in db_uri else 'mysql://***:***@...' if 'mysql' in db_uri else db_uri.split('@')[0] + '@***'
    logger.info(f'Database URL: {db_uri}')
    
    with app.app_context():
        # Ensure database tables exist
        logger.info('Ensuring database tables are initialized...')
        try:
            db.create_all()
            logger.info('Database tables initialized successfully')
        except Exception as e:
            logger.error(f'Error initializing database tables: {e}', exc_info=True)
        
        # Ensure AppSettings row exists
        from app.models import AppSettings
        settings = AppSettings.get()
        if settings:
            logger.info(f'AppSettings loaded (invoice_reminder_enabled: {settings.invoice_reminder_enabled})')
        else:
            logger.error('Failed to load or create AppSettings')
        
        # Process reminders
        logger.info('Processing invoice reminders...')
        process_invoice_reminders()
    
    logger.info('Invoice reminders processing completed successfully')
    sys.exit(0)
    
except Exception as e:
    logger.exception(f'Error processing invoice reminders: {e}')
    sys.exit(1)
