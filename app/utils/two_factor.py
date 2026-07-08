import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote
import qrcode
from io import BytesIO


def generate_totp_secret(length=20):
    """Generate a Base32 secret for TOTP apps."""
    random_bytes = secrets.token_bytes(length)
    return base64.b32encode(random_bytes).decode('ascii').rstrip('=')


def _totp_counter(for_time=None):
    if for_time is None:
        for_time = int(time.time())
    return int(for_time // 30)


def _generate_hotp(secret, counter, digits=6, digest='sha1'):
    secret_bytes = base64.b32decode(secret.upper() + '=' * ((8 - len(secret) % 8) % 8))
    msg = struct.pack('>Q', counter)
    hmac_digest = hmac.new(secret_bytes, msg, getattr(hashlib, digest)).digest()
    offset = hmac_digest[-1] & 0x0F
    binary = struct.unpack('>I', hmac_digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(binary % (10 ** digits)).zfill(digits)


def generate_totp_code(secret, digits=6, for_time=None):
    return _generate_hotp(secret, _totp_counter(for_time), digits=digits)


def verify_totp_code(secret, code, digits=6, window=1, for_time=None):
    if not code or not secret:
        return False
    try:
        code_int = int(code)
    except (TypeError, ValueError):
        return False

    current_counter = _totp_counter(for_time)
    for offset in range(-window, window + 1):
        expected = _generate_hotp(secret, current_counter + offset, digits=digits)
        if str(code_int).zfill(digits) == expected:
            return True
    return False


def build_otpauth_uri(email, secret, issuer='ABA Services'):
    label = quote(f'{issuer}:{email}')
    return f'otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}'


def generate_qr_code_base64(uri):
    """Generate a QR code from the otpauth URI and return it as base64 data URI."""
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color='black', back_color='white')
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f'data:image/png;base64,{img_base64}'
