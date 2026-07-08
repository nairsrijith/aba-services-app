from flask import current_app, request, jsonify
from flask_login import current_user, login_required
from . import api_bp, token_required


@api_bp.route('/auth/token', methods=['POST'])
def auth_token():
    """Exchange email+password for a bearer token (JSON).

    Request JSON: {"email": "...", "password": "..."}
    Response JSON: {"token": "...", "expires_in": seconds}
    """
    data = request.get_json() or {}
    email = (data.get('email') or '').lower()
    password = data.get('password')
    if not email or not password:
        return jsonify({'error': 'email and password required'}), 400

    from app.models import Employee
    emp = Employee.query.filter_by(email=email).first()
    if not emp or not emp.check_password(password) or not emp.login_enabled:
        return jsonify({'error': 'invalid credentials'}), 401

    from . import generate_token, DEFAULT_TOKEN_EXPIRY, MAX_TOKEN_EXPIRY
    expires_in = data.get('expires_in', DEFAULT_TOKEN_EXPIRY)
    try:
        expires_in = int(expires_in)
    except (TypeError, ValueError):
        return jsonify({'error': 'expires_in must be an integer number of seconds'}), 400

    if expires_in < 60 or expires_in > MAX_TOKEN_EXPIRY:
        return jsonify({'error': f'expires_in must be between 60 and {MAX_TOKEN_EXPIRY} seconds'}), 400

    t = generate_token(emp.id, expires_in=expires_in)
    return jsonify({'token': t, 'expires_in': expires_in})


@api_bp.route('/auth/service_accounts', methods=['POST'])
def create_service_account():
    """Create a named service account for automation token issuance."""
    data = request.get_json() or {}
    email = (data.get('email') or '').lower()
    password = data.get('password')
    name = (data.get('name') or '').strip()
    description = data.get('description')

    if not email or not password or not name:
        return jsonify({'error': 'email, password, and name are required'}), 400

    from app.models import Employee, ServiceAccount
    emp = Employee.query.filter_by(email=email).first()
    if not emp or not emp.check_password(password) or not emp.login_enabled:
        return jsonify({'error': 'invalid credentials'}), 401
    if emp.user_type not in ['admin', 'super']:
        return jsonify({'error': 'admin access required'}), 403

    existing = ServiceAccount.query.filter_by(name=name).first()
    if existing:
        return jsonify({'error': 'service account name already exists'}), 400

    service_account = ServiceAccount(name=name, description=description)
    from app import db
    db.session.add(service_account)
    db.session.commit()

    return jsonify({
        'id': service_account.id,
        'name': service_account.name,
        'description': service_account.description,
        'created_at': service_account.created_at.isoformat(),
    })


@api_bp.route('/auth/automation_token', methods=['POST'])
def create_automation_token():
    """Create an automation bearer token tied to a service account."""
    data = request.get_json() or {}
    email = (data.get('email') or '').lower()
    password = data.get('password')
    from . import DEFAULT_TOKEN_EXPIRY, MAX_TOKEN_EXPIRY
    expires_in = data.get('expires_in', DEFAULT_TOKEN_EXPIRY)
    service_account_id = data.get('service_account_id')
    service_account_name = (data.get('service_account_name') or '').strip()

    if not email or not password:
        return jsonify({'error': 'email and password required'}), 400

    try:
        expires_in = int(expires_in)
    except (TypeError, ValueError):
        return jsonify({'error': 'expires_in must be an integer number of seconds'}), 400

    from . import DEFAULT_TOKEN_EXPIRY, MAX_TOKEN_EXPIRY
    if expires_in < 60 or expires_in > MAX_TOKEN_EXPIRY:
        return jsonify({'error': f'expires_in must be between 60 and {MAX_TOKEN_EXPIRY} seconds'}), 400

    from app.models import Employee, ServiceAccount
    emp = Employee.query.filter_by(email=email).first()
    if not emp or not emp.check_password(password) or not emp.login_enabled:
        return jsonify({'error': 'invalid credentials'}), 401
    if emp.user_type not in ['admin', 'super']:
        return jsonify({'error': 'admin access required'}), 403

    if service_account_id is None and not service_account_name:
        return jsonify({'error': 'either service_account_id or service_account_name is required'}), 400

    if service_account_id is not None:
        try:
            service_account_id = int(service_account_id)
        except (TypeError, ValueError):
            return jsonify({'error': 'service_account_id must be an integer'}), 400
        service_account = ServiceAccount.query.get(service_account_id)
    else:
        service_account = ServiceAccount.query.filter_by(name=service_account_name).first()

    if not service_account:
        return jsonify({'error': 'service account not found'}), 404

    from . import generate_automation_token
    raw_token, token_obj = generate_automation_token(service_account.id, emp.id, expires_in=expires_in)
    return jsonify({
        'token': raw_token,
        'expires_in': expires_in,
        'service_account_id': service_account.id,
        'service_account_name': service_account.name,
        'created_by_id': emp.id,
        'expires_at': token_obj.expires_at.isoformat(),
    })


@api_bp.route('/auth/service_accounts/list', methods=['POST'])
@login_required
def list_service_accounts():
    """List service accounts for admin users."""
    if current_user.user_type not in ['admin', 'super']:
        return jsonify({'error': 'admin access required'}), 403

    from app.models import ServiceAccount
    accounts = ServiceAccount.query.order_by(ServiceAccount.name).all()
    return jsonify([{
        'id': acct.id,
        'name': acct.name,
        'description': acct.description,
        'created_at': acct.created_at.isoformat(),
    } for acct in accounts])


@api_bp.route('/auth/service_accounts/details', methods=['POST'])
@login_required
def service_account_details():
    """Return service account and token details for admin management."""
    if current_user.user_type not in ['admin', 'super']:
        return jsonify({'error': 'admin access required'}), 403

    from app.models import ServiceAccount
    accounts = ServiceAccount.query.order_by(ServiceAccount.name).all()
    payload = []
    for acct in accounts:
        payload.append({
            'id': acct.id,
            'name': acct.name,
            'description': acct.description,
            'created_at': acct.created_at.isoformat(),
            'tokens': [{
                'id': token.id,
                'expires_at': token.expires_at.isoformat(),
                'created_at': token.created_at.isoformat(),
                'revoked': token.revoked,
                'last_used': token.last_used.isoformat() if token.last_used else None,
            } for token in acct.tokens]
        })
    return jsonify(payload)


@api_bp.route('/auth/automation_token/revoke', methods=['POST'])
@login_required
def revoke_automation_token():
    data = request.get_json() or {}
    token_id = data.get('token_id')
    if not token_id:
        return jsonify({'error': 'token_id is required'}), 400

    if current_user.user_type not in ['admin', 'super']:
        return jsonify({'error': 'admin access required'}), 403

    from app.models import AutomationToken
    token = AutomationToken.query.get(token_id)
    if not token:
        return jsonify({'error': 'automation token not found'}), 404

    token.revoke()
    from app import db
    db.session.commit()

    return jsonify({'status': 'revoked', 'token_id': token.id})


@api_bp.route('/auth/service_account/delete', methods=['POST'])
@login_required
def delete_service_account():
    data = request.get_json() or {}
    service_account_id = data.get('service_account_id')
    if not service_account_id:
        return jsonify({'error': 'service_account_id is required'}), 400

    if current_user.user_type not in ['admin', 'super']:
        return jsonify({'error': 'admin access required'}), 403

    from app.models import ServiceAccount, AutomationToken
    service_account = ServiceAccount.query.get(service_account_id)
    if not service_account:
        return jsonify({'error': 'service account not found'}), 404

    from app import db
    AutomationToken.query.filter_by(service_account_id=service_account.id).delete()
    db.session.delete(service_account)
    db.session.commit()

    return jsonify({'status': 'deleted', 'service_account_id': service_account_id})


@api_bp.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@api_bp.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
@token_required
def proxy(path):
    """Proxy requests to the same web route and return the rendered HTML inside JSON.

    This mirrors web URLs under `/api/...` by internally dispatching the request
    to the application and returning a JSON payload containing the original
    response body (usually HTML). This is a pragmatic first step to mirror all
    web URLs without re-implementing every view as JSON endpoints.
    """
    # Reconstruct target path
    target = '/' + path
    # Use test_client to perform an internal request to the app
    client = current_app.test_client()

    # prepare kwargs for client.open
    kwargs = {}
    if request.query_string:
        kwargs['query_string'] = request.query_string
    if request.data:
        kwargs['data'] = request.get_data()
    headers = {}
    # forward form/content-type headers
    if request.content_type:
        headers['Content-Type'] = request.content_type
    # call internal client
    resp = client.open(target, method=request.method, headers=headers, **kwargs)

    content = resp.get_data(as_text=True)
    return jsonify({'status_code': resp.status_code, 'content': content}), resp.status_code
