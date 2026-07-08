from flask import Blueprint, current_app, request, jsonify, g
from itsdangerous import URLSafeTimedSerializer as Serializer
from itsdangerous import BadSignature
from functools import wraps
from app import db
from app.models import Employee, AutomationToken, ServiceAccount
from datetime import datetime, timedelta
import hashlib
import secrets
import time

api_bp = Blueprint('api', __name__)

DEFAULT_TOKEN_EXPIRY = 1800
MAX_TOKEN_EXPIRY = 15552000


def _get_serializer():
    secret = current_app.config.get('SECRET_KEY') or 'my_app_super_secret_key'
    return Serializer(secret)


def generate_token(user_id, expires_in=DEFAULT_TOKEN_EXPIRY):
    s = _get_serializer()
    now = int(time.time())
    payload = {
        'id': user_id,
        'expires_in': expires_in,
        'expires_at': now + expires_in,
    }
    return s.dumps(payload)


def generate_automation_token(service_account_id, created_by_id, expires_in=DEFAULT_TOKEN_EXPIRY):
    raw_token = secrets.token_urlsafe(48)
    token_hash = _hash_token(raw_token)
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    token_obj = AutomationToken(
        service_account_id=service_account_id,
        created_by_id=created_by_id,
        token_hash=token_hash,
        expires_at=expires_at,
        created_at=datetime.utcnow(),
        revoked=False,
    )
    db.session.add(token_obj)
    db.session.commit()
    return raw_token, token_obj


def _hash_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def verify_signed_token(token):
    s = _get_serializer()
    try:
        data = s.loads(token)
    except BadSignature:
        return None

    if not isinstance(data, dict):
        return None

    expires_at = data.get('expires_at')
    if not isinstance(expires_at, (int, float)):
        return None
    if time.time() > expires_at:
        return None

    return Employee.query.get(data.get('id'))


def verify_automation_token(token):
    token_hash = _hash_token(token)
    token_obj = AutomationToken.query.filter_by(token_hash=token_hash, revoked=False).first()
    if not token_obj:
        return None
    if not isinstance(token_obj.expires_at, datetime):
        return None
    if datetime.utcnow() > token_obj.expires_at:
        return None
    token_obj.mark_used()
    db.session.add(token_obj)
    db.session.commit()
    return token_obj


def verify_token(token):
    user = verify_signed_token(token)
    if user:
        return {'type': 'user', 'user': user}

    token_obj = verify_automation_token(token)
    if token_obj:
        return {'type': 'automation', 'token': token_obj}

    return None


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth or not auth.lower().startswith('bearer '):
            return jsonify({'error': 'Authorization header missing or malformed'}), 401
        token = auth.split(None, 1)[1]
        auth_payload = verify_token(token)
        if not auth_payload:
            return jsonify({'error': 'Invalid or expired token'}), 401

        if auth_payload['type'] == 'user':
            g.current_user = auth_payload['user']
            g.current_service_account = None
            g.current_automation_token = None
        else:
            g.current_automation_token = auth_payload['token']
            g.current_service_account = auth_payload['token'].service_account
            g.current_user = auth_payload['token'].created_by

        return f(*args, **kwargs)
    return decorated


# Import submodules to ensure their routes are registered when this package is imported
try:
    from . import proxy  # noqa: F401
except Exception:
    # avoid import-time crash in environments where dependencies may be missing;
    # errors will surface later when the endpoint is used and can be inspected
    pass

# import resource modules
try:
    from . import clients, employees, invoices, interventions, payroll, mileage, users, manage, reports  # noqa: F401
except Exception:
    pass
