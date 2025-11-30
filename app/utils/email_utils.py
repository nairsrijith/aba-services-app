import os
import smtplib
import logging
from email.message import EmailMessage
from email.utils import getaddresses
from threading import Thread
from typing import List, Tuple, Optional

from flask import render_template

logger = logging.getLogger(__name__)
# Ensure logs are visible in container stdout/stderr when not otherwise configured
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s: %(message)s'))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Read SMTP config from environment variables
SMTP_HOST = os.environ.get('SMTP_HOST', 'localhost')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 25))
SMTP_USER = os.environ.get('SMTP_USER')
SMTP_PASS = os.environ.get('SMTP_PASS')
SMTP_USE_TLS = os.environ.get('SMTP_USE_TLS', 'false').lower() in ('1', 'true', 'yes')
SMTP_USE_SSL = os.environ.get('SMTP_USE_SSL', 'false').lower() in ('1', 'true', 'yes')
DEFAULT_FROM = os.environ.get('ORG_EMAIL', 'no-reply@example.com')
ORG_NAME = os.environ.get('ORG_NAME', '')

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


def _send_message(msg: EmailMessage) -> bool:
    try:
        # Allow AppSettings to override SMTP configuration and enable testing mode
        try:
            from app.models import AppSettings
            s = AppSettings.get()
        except Exception:
            s = None

        smtp_host = s.smtp_host if s and s.smtp_host else SMTP_HOST
        smtp_port = int(s.smtp_port) if s and s.smtp_port else SMTP_PORT
        smtp_user = s.smtp_user if s and s.smtp_user else SMTP_USER
        smtp_pass = s.smtp_pass if s and s.smtp_pass else SMTP_PASS
        smtp_use_tls = bool(s.smtp_use_tls) if s and s.smtp_use_tls is not None else SMTP_USE_TLS
        smtp_use_ssl = bool(s.smtp_use_ssl) if s and s.smtp_use_ssl is not None else SMTP_USE_SSL

        # If testing mode is enabled, rewrite recipients to testing email and annotate
        if s and s.testing_mode and s.testing_email:
            original_to = msg['To']
            msg['X-Original-To'] = original_to
            try:
                msg.replace_header('To', s.testing_email)
            except Exception:
                msg['To'] = s.testing_email

        # Log recipients before sending (include original recipients if present)
        try:
            orig = msg.get('X-Original-To')
            if orig:
                logger.info('Sending email to %s (original: %s) subject=%s', msg['To'], orig, msg['Subject'])
            else:
                logger.info('Sending email to %s subject=%s', msg['To'], msg['Subject'])
        except Exception:
            logger.info('Sending email (subject=%s)', msg.get('Subject'))

        # Determine explicit recipient list to pass to send_message.
        # This avoids relying solely on msg headers (which some environments
        # or transport layers may ignore) and ensures testing override is used.
        if s and s.testing_mode and s.testing_email:
            to_addrs = [s.testing_email]
        else:
            # extract addresses from the To header(s)
            raw_to = msg.get_all('To', [])
            # getaddresses expects a list of address-containing strings
            parsed = getaddresses(raw_to)
            to_addrs = [addr for name, addr in parsed if addr]

        # Log what we're about to send and why — helpful for debugging testing mode
        try:
            logger.info('AppSettings testing_mode=%s testing_email=%s', bool(s.testing_mode) if s else None, (s.testing_email if s else None))
            orig = msg.get('X-Original-To')
            if orig:
                logger.info('Prepared message To header=%s (X-Original-To=%s) subject=%s', msg.get('To'), orig, msg.get('Subject'))
            else:
                logger.info('Prepared message To header=%s subject=%s', msg.get('To'), msg.get('Subject'))
            logger.info('Computed to_addrs=%s', to_addrs)
        except Exception:
            logger.exception('Failed while logging email send debug info')

        if smtp_use_ssl:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.send_message(msg, to_addrs=to_addrs)
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                if smtp_use_tls:
                    server.starttls()
                if smtp_user and smtp_pass:
                    server.login(smtp_user, smtp_pass)
                server.send_message(msg, to_addrs=to_addrs)

        # Confirm send
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
    t = Thread(target=_send_message, args=(msg,), daemon=True)
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
