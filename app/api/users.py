from flask import request, jsonify, g
from . import api_bp, token_required
from app import db
from app.models import Employee
from datetime import datetime


def _serialize_user(u: Employee):
    return {
        'id': u.id,
        'firstname': u.firstname,
        'lastname': u.lastname,
        'email': u.email,
        'position': u.position,
        'rba_number': u.rba_number,
        'user_type': u.user_type,
        'is_active': bool(u.is_active),
        'login_enabled': bool(u.login_enabled),
        'locked_until': u.locked_until.isoformat() if u.locked_until else None
    }


def _require_admin():
    if g.current_user.user_type not in ['admin', 'super']:
        return jsonify({'error': 'admin access required'}), 403
    return None


@api_bp.route('/users', methods=['GET'])
@token_required
def list_users():
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    users = Employee.query.filter(
        ~((Employee.user_type == 'super') | (Employee.email == g.current_user.email) | (Employee.failed_attempt <= -5))
    ).order_by(Employee.firstname).all()
    return jsonify([_serialize_user(u) for u in users])


@api_bp.route('/users/<int:user_id>', methods=['GET'])
@token_required
def get_user(user_id):
    user = Employee.query.get_or_404(user_id)
    if g.current_user.user_type not in ['admin', 'super'] and g.current_user.id != user.id:
        return jsonify({'error': 'access denied'}), 403
    return jsonify(_serialize_user(user))


@api_bp.route('/users', methods=['POST'])
@token_required
def create_user():
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    data = request.get_json() or {}
    required = ['firstname', 'lastname', 'position', 'email', 'cell']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'missing field: {field}'}), 400

    if Employee.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'email already exists'}), 400

    new_user = Employee(
        firstname=data.get('firstname'),
        lastname=data.get('lastname'),
        position=data.get('position'),
        rba_number=data.get('rba_number'),
        email=data.get('email'),
        cell=data.get('cell'),
        address1=data.get('address1'),
        address2=data.get('address2'),
        city=data.get('city'),
        state=data.get('state'),
        zipcode=data.get('zipcode'),
        user_type=data.get('user_type', 'therapist'),
        is_active=data.get('is_active', True),
        login_enabled=bool(data.get('login_enabled', False))
    )

    if data.get('password'):
        new_user.set_password(data.get('password'))
        new_user.login_enabled = bool(data.get('login_enabled', True))
    else:
        new_user.generate_activation_key()

    db.session.add(new_user)
    db.session.commit()
    return jsonify(_serialize_user(new_user)), 201


@api_bp.route('/users/<int:user_id>', methods=['PUT'])
@token_required
def update_user(user_id):
    user = Employee.query.get_or_404(user_id)
    if g.current_user.user_type not in ['admin', 'super'] and g.current_user.id != user.id:
        return jsonify({'error': 'access denied'}), 403

    data = request.get_json() or {}
    for field in ('firstname', 'lastname', 'position', 'rba_number', 'email', 'cell', 'address1', 'address2', 'city', 'state', 'zipcode'):
        if field in data:
            setattr(user, field, data[field])

    if 'user_type' in data and g.current_user.user_type in ['admin', 'super']:
        user.user_type = data.get('user_type')

    if 'is_active' in data and g.current_user.user_type in ['admin', 'super']:
        user.is_active = bool(data.get('is_active'))

    if 'login_enabled' in data and g.current_user.user_type in ['admin', 'super']:
        user.login_enabled = bool(data.get('login_enabled'))

    if 'password' in data and data.get('password'):
        user.set_password(data.get('password'))

    if 'locked_until' in data and g.current_user.user_type in ['admin', 'super']:
        if data.get('locked_until'):
            try:
                user.locked_until = datetime.fromisoformat(data.get('locked_until'))
            except Exception:
                return jsonify({'error': 'locked_until must be ISO datetime'}), 400
        else:
            user.locked_until = None

    db.session.commit()
    return jsonify(_serialize_user(user))


@api_bp.route('/users/<int:user_id>', methods=['DELETE'])
@token_required
def delete_user(user_id):
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    user = Employee.query.get_or_404(user_id)
    if user.user_type == 'super' and g.current_user.user_type != 'super':
        return jsonify({'error': 'cannot deactivate super user'}), 403
    if user.id == g.current_user.id:
        return jsonify({'error': 'cannot delete yourself via API'}), 400

    user.is_active = False
    user.login_enabled = False
    user.password_hash = None
    user.activation_key = None
    user.password_reset_key = None
    user.failed_attempt = -5
    user.locked_until = None
    db.session.commit()
    return jsonify({'status': 'deactivated'})
