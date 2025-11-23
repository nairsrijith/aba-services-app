import os
import smtplib
import logging
from email.message import EmailMessage

logger = logging.getLogger(__name__)

# Read SMTP config from environment variables
SMTP_HOST = os.environ.get('SMTP_HOST', 'localhost')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 25))
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASS = os.environ.get('SMTP_PASS')
SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'false').lower() in ('1', 'true', 'yes')
SMTP_USE_SSL = os.environ.get('SMTP_USE_SSL', 'false').lower() in ('1', 'true', 'yes')
DEFAULT_FROM = os.environ.get('ORG_EMAIL', 'no-reply@example.com')
ORG_NAME = os.environ.get('ORG_NAME', '')


def send_email(subject: str, recipients, body_text: str = None, body_html: str = None, attachments: list = None, from_addr: str = None):
    """Send an email using SMTP. attachments is a list of tuples (filename, content_bytes, mime_type).

    Recipients can be a string or list.
    """
    if isinstance(recipients, str):
        recipients = [recipients]
import os
import smtplib
import logging
from email.message import EmailMessage
from threading import Thread
from typing import List, Tuple, Optional

from flask import render_template

logger = logging.getLogger(__name__)

# Read SMTP config from environment variables
SMTP_HOST = os.environ.get('SMTP_HOST', 'localhost')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 25))
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASS = os.environ.get('SMTP_PASS')
SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'false').lower() in ('1', 'true', 'yes')
SMTP_USE_SSL = os.environ.get('SMTP_USE_SSL', 'false').lower() in ('1', 'true', 'yes')
DEFAULT_FROM = os.environ.get('ORG_EMAIL', 'no-reply@example.com')
ORG_NAME = os.environ.get('ORG_NAME', '')

# Optional Redis URL for RQ background queue. If not provided, fallback to threaded background send.
REDIS_URL = os.environ.get('REDIS_URL')


def _build_message(subject: str, recipients, body_text: Optional[str] = None, body_html: Optional[str] = None, attachments: Optional[List[Tuple[str, bytes, str]]] = None, from_addr: Optional[str] = None) -> EmailMessage:
    if isinstance(recipients, str):
        recipients = [recipients]

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_addr or DEFAULT_FROM
    msg['To'] = ', '.join(recipients)

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


def _send_message(msg: EmailMessage) -> bool:
    try:
        if SMTP_USE_SSL:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
                if SMTP_USER and SMTP_PASS:
                    server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                if SMTP_USE_TLS:
                    server.starttls()
                if SMTP_USER and SMTP_PASS:
                    server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
        logger.info('Email sent to %s (subject=%s)', msg['To'], msg['Subject'])
        return True
    except Exception as e:
        logger.exception('Failed to send email to %s: %s', msg['To'], e)
        return False


def send_email(subject: str, recipients, body_text: str = None, body_html: str = None, attachments: list = None, from_addr: str = None) -> bool:
    """Build and send an email immediately (blocking). Use `queue_email` to send async."""
    msg = _build_message(subject, recipients, body_text, body_html, attachments, from_addr)
    return _send_message(msg)


def send_email_with_pdf(recipient: str, subject: str, body_text: str, pdf_bytes: bytes, filename: str, body_html: str = None, from_addr: str = None) -> bool:
    attachments = [(filename, pdf_bytes, 'application/pdf')]
    return send_email(subject=subject, recipients=[recipient], body_text=body_text, body_html=body_html, attachments=attachments, from_addr=from_addr)


def _background_send(subject: str, recipients, body_text: str = None, body_html: str = None, attachments: list = None, from_addr: str = None):
    # Simple threaded background sender for environments without Redis
    try:
        send_email(subject, recipients, body_text, body_html, attachments, from_addr)
    except Exception:
        logger.exception('Background email send failed')


def queue_email(subject: str, recipients, body_text: str = None, body_html: str = None, attachments: list = None, from_addr: str = None):
    """Queue email for background sending. If REDIS_URL is configured RQ is used; otherwise falls back to a background thread.

    attachments: list of (filename, bytes, mime_type)
    """
    # If Redis is configured, enqueue job via rq
    if REDIS_URL:
        try:
            from redis import Redis
            from rq import Queue

            conn = Redis.from_url(REDIS_URL)
            q = Queue(connection=conn)
            # We enqueue the _send_message helper to avoid pickling Flask objects
            msg = _build_message(subject, recipients, body_text, body_html, attachments, from_addr)
            # enqueue a tiny wrapper that calls _send_message
            q.enqueue(_send_message, msg)
            logger.info('Email enqueued to Redis queue')
            return True
        except Exception:
            logger.exception('Failed to enqueue email to Redis; falling back to threaded send')

    # Fallback: run in a background thread so request isn't blocked
    t = Thread(target=_background_send, args=(subject, recipients, body_text, body_html, attachments, from_addr), daemon=True)
    t.start()
    return True


def queue_email_with_pdf(recipients, subject: str, body_text: str, pdf_bytes: bytes, filename: str, body_html: str = None, from_addr: str = None) -> bool:
    """Queue an email with a single PDF attachment.

    `recipients` may be a single email string or a list of emails.
    """
    if isinstance(recipients, str):
        recipients = [recipients]
    attachments = [(filename, pdf_bytes, 'application/pdf')]
    return queue_email(subject=subject, recipients=recipients, body_text=body_text, body_html=body_html, attachments=attachments, from_addr=from_addr)
