import os
import logging
from email.message import EmailMessage
from threading import Thread, Lock
from typing import List, Tuple, Optional
import base64
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from flask import render_template, current_app
from app import app

logger = logging.getLogger(__name__)
# Ensure logs are visible in container stdout/stderr when not otherwise configured
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Read configuration from environment variables
DEFAULT_FROM = os.environ.get('ORG_EMAIL', 'no-reply@example.com')
ORG_NAME = os.environ.get('ORG_NAME', '')

# Track active background email threads
_active_email_threads = []
_email_thread_lock = Lock()

# No Redis/RQ support in this deployment; always use threaded background send.
def _build_message(subject: str, recipients, body_text: Optional[str] = None, body_html: Optional[str] = None, attachments: Optional[List[Tuple[str, bytes, str]]] = None, from_addr: Optional[str] = None) -> EmailMessage:
    if isinstance(recipients, str):
        recipients = [recipients]

    msg = EmailMessage()
    msg['Subject'] = subject
    # Allow AppSettings to override the default From address
    try:
        from app.models import AppSettings
        s = AppSettings.get()
        default_from = s.org_email if s and s.org_email else DEFAULT_FROM
    except Exception:
        default_from = DEFAULT_FROM

    msg['From'] = from_addr or default_from
    msg['To'] = ', '.join(recipients)
    
    # Add CC for all outgoing emails if configured in AppSettings
    try:
        from app.models import AppSettings
        s = AppSettings.get()
        if s and s.default_cc:
            msg['Cc'] = s.default_cc
    except Exception:
        pass

    # If testing mode is enabled in AppSettings, rewrite recipients now
    try:
        from app.models import AppSettings
        s_test = AppSettings.get()
        if s_test and s_test.testing_mode and s_test.testing_email:
            original_to = msg['To']
            msg['X-Original-To'] = original_to
            # replace_header will fail if header not present, but 'To' is set above
            try:
                msg.replace_header('To', s_test.testing_email)
            except Exception:
                msg['To'] = s_test.testing_email
    except Exception:
        # if AppSettings can't be read, continue without testing override
        pass

    if body_html and body_text:
        msg.set_content(body_text)
        msg.add_alternative(body_html, subtype='html')
    elif body_html:
        msg.set_content('Please view this message in an HTML capable client')
        msg.add_alternative(body_html, subtype='html')
    elif body_text:
        msg.set_content(body_text)
    else:
        msg.set_content('')

    if attachments:
        for filename, content, mime_type in attachments:
            maintype, _, subtype = mime_type.partition('/')
            try:
                msg.add_attachment(content, maintype=maintype or 'application', subtype=subtype or 'octet-stream', filename=filename)
            except Exception:
                msg.add_attachment(content, maintype='application', subtype='octet-stream', filename=filename)

    return msg


def _send_via_gmail_api(msg: EmailMessage, settings) -> bool:
    try:
        # Log recipients before sending (include original recipients if present)
        try:
            orig = msg.get('X-Original-To')
            if orig:
                logger.info('Sending email via Gmail API to %s (original: %s) subject=%s', msg['To'], orig, msg['Subject'])
            else:
                logger.info('Sending email via Gmail API to %s subject=%s', msg['To'], msg['Subject'])
        except Exception:
            logger.info('Sending email via Gmail API (subject=%s)', msg.get('Subject'))

        if not settings:
            logger.error('AppSettings is None, cannot send email via Gmail API')
            return False

        if not settings.gmail_refresh_token:
            logger.error('Gmail refresh token not configured, cannot send email')
            return False

        creds = Credentials(
            token=None,
            refresh_token=settings.gmail_refresh_token,
            token_uri='https://oauth2.googleapis.com/token',
            client_id=settings.gmail_client_id,
            client_secret=settings.gmail_client_secret,
            scopes=['https://www.googleapis.com/auth/gmail.send']
        )
        service = build('gmail', 'v1', credentials=creds)

        # Encode the message
        raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode()

        message = {'raw': raw_message}

        # Send the message
        logger.debug('Executing Gmail API send request')
        sent_message = service.users().messages().send(userId='me', body=message).execute()
        logger.info('Email sent via Gmail API successfully, message ID: %s', sent_message['id'])
        return True
    except HttpError as e:
        logger.error('Failed to send email via Gmail API - HTTP Error: %s', e)
        return False
    except Exception as e:
        logger.error('Failed to send email via Gmail API - Exception: %s', e)
        return False


def _send_message(msg: EmailMessage) -> bool:
    try:
        # Allow AppSettings to override configuration and enable testing mode
        try:
            from app.models import AppSettings
            s = AppSettings.get()
        except Exception:
            s = None

        # If testing mode is enabled, rewrite recipients to testing email and annotate
        if s and s.testing_mode and s.testing_email:
            original_to = msg['To']
            msg['X-Original-To'] = original_to
            try:
                msg.replace_header('To', s.testing_email)
            except Exception:
                msg['To'] = s.testing_email

        # Use Gmail API for sending emails
        if not s or not s.gmail_client_id or not s.gmail_client_secret or not s.gmail_refresh_token:
            logger.error('Gmail OAuth not configured. Please set Gmail OAuth credentials in app settings.')
            return False

        return _send_via_gmail_api(msg, s)

    except Exception as e:
        logger.exception('Failed to send email: %s', e)
        return False


def send_email(subject: str, recipients, body_text: str = None, body_html: str = None, attachments: list = None, from_addr: str = None) -> bool:
    """Build and send an email immediately (blocking). Use `queue_email` to send async."""
    msg = _build_message(subject, recipients, body_text, body_html, attachments, from_addr)
    return _send_message(msg)


def send_email_with_pdf(recipient: str, subject: str, body_text: str, pdf_bytes: bytes, filename: str, body_html: str = None, from_addr: str = None) -> bool:
    attachments = [(filename, pdf_bytes, 'application/pdf')]
    return send_email(subject=subject, recipients=[recipient], body_text=body_text, body_html=body_html, attachments=attachments, from_addr=from_addr)


# _background_send removed — always build message in request thread and send in background thread



def queue_email(subject: str, recipients, body_text: str = None, body_html: str = None, attachments: list = None, from_addr: str = None):
    """Queue email for background sending. Uses a background thread to send the prebuilt message.

    attachments: list of (filename, bytes, mime_type)
    """
    # Build the message in the current thread/context so AppSettings and
    # environment-based overrides are read while the Flask app/context is active.
    try:
        msg = _build_message(subject, recipients, body_text, body_html, attachments, from_addr)
    except Exception:
        logger.exception('Failed to build email message')
        return False

    # Send in a background thread so request isn't blocked.
    def send_in_thread(msg):
        try:
            with app.app_context():
                result = _send_message(msg)
                if result:
                    logger.info('Email queued background thread: email sent successfully')
                else:
                    logger.error('Email queued background thread: email failed to send')
        except Exception as e:
            logger.exception(f'Email queued background thread: exception occurred: {e}')

    t = Thread(target=send_in_thread, args=(msg,), daemon=False)  # daemon=False to ensure thread completes
    t.start()
    
    # Track the thread so we can wait for it if needed
    with _email_thread_lock:
        _active_email_threads.append(t)
    
    return True


def wait_for_pending_emails(timeout: float = 30.0):
    """Wait for all pending background email threads to complete.
    
    Args:
        timeout: Maximum time to wait in seconds. Logs a warning if timeout is reached.
    """
    with _email_thread_lock:
        threads_to_wait = list(_active_email_threads)
        _active_email_threads.clear()
    
    if not threads_to_wait:
        return
    
    logger.info(f'Waiting for {len(threads_to_wait)} pending email threads to complete (timeout: {timeout}s)')
    
    for i, t in enumerate(threads_to_wait, 1):
        t.join(timeout=timeout)
        if t.is_alive():
            logger.warning(f'Email thread {i}/{len(threads_to_wait)} did not complete within {timeout}s')
        else:
            logger.info(f'Email thread {i}/{len(threads_to_wait)} completed')
    
    logger.info('All pending email threads processed')


def queue_email_with_pdf(recipients, subject: str, body_text: str, pdf_bytes: bytes, filename: str, body_html: str = None, from_addr: str = None) -> bool:
    """Queue an email with a single PDF attachment.

    `recipients` may be a single email string or a list of emails.
    """
    if isinstance(recipients, str):
        recipients = [recipients]
    attachments = [(filename, pdf_bytes, 'application/pdf')]
    return queue_email(subject=subject, recipients=recipients, body_text=body_text, body_html=body_html, attachments=attachments, from_addr=from_addr)
