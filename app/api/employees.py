from flask import request, jsonify, g
from . import api_bp, token_required
from app import db
from app.models import Employee, Client


def _serialize_emp(e: Employee):
    return {
        'id': e.id,
        'firstname': e.firstname,
        'lastname': e.lastname,
        'email': e.email,
        'cell': e.cell,
        'position': e.position,
        'rba_number': e.rba_number,
        'user_type': e.user_type,
        'is_active': bool(e.is_active),
        'login_enabled': bool(e.login_enabled)
    }


def _determine_user_type(position, current_user_type=None):
    if current_user_type == 'super':
        return 'super'
    if position == 'Administrator':
        return 'admin'
    elif position == 'Behaviour Analyst':
        return 'supervisor'
    return 'therapist'


def _require_admin():
    if g.current_user.user_type not in ['admin', 'super']:
        return jsonify({'error': 'admin access required'}), 403
    return None


@api_bp.route('/employees', methods=['GET'])
@token_required
def list_employees():
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    emps = Employee.query.order_by(Employee.firstname).all()
    return jsonify([_serialize_emp(e) for e in emps])


@api_bp.route('/employees/<int:emp_id>', methods=['GET'])
@token_required
def get_employee(emp_id):
    employee = Employee.query.get_or_404(emp_id)
    if g.current_user.user_type not in ['admin', 'super'] and g.current_user.id != employee.id:
        return jsonify({'error': 'access denied'}), 403
    return jsonify(_serialize_emp(employee))


@api_bp.route('/employees', methods=['POST'])
@token_required
def create_employee():
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    data = request.get_json() or {}
    required = ['firstname', 'position', 'email', 'cell']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'missing field: {field}'}), 400

    if data.get('position') == 'Behaviour Analyst' and not data.get('rba_number'):
        return jsonify({'error': 'rba_number is required for Behaviour Analyst'}), 400

    if Employee.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'email already exists'}), 400

    user_type = _determine_user_type(data.get('position'), data.get('user_type'))
    employee = Employee(
        firstname=data.get('firstname'),
        lastname=data.get('lastname'),
        position=data.get('position'),
        rba_number=data.get('rba_number'),
        email=data.get('email'),
        cell=data.get('cell'),
        user_type=user_type,
        address1=data.get('address1'),
        address2=data.get('address2'),
        city=data.get('city'),
        state=data.get('state'),
        zipcode=data.get('zipcode'),
        is_active=data.get('is_active', True),
        login_enabled=bool(data.get('login_enabled', False))
    )

    if data.get('password'):
        employee.set_password(data.get('password'))
        employee.login_enabled = bool(data.get('login_enabled', True))
    else:
        employee.generate_activation_key()

    db.session.add(employee)
    db.session.commit()
    return jsonify(_serialize_emp(employee)), 201


@api_bp.route('/employees/<int:emp_id>', methods=['PUT'])
@token_required
def update_employee(emp_id):
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    employee = Employee.query.get_or_404(emp_id)
    data = request.get_json() or {}
    for field in ('firstname', 'lastname', 'email', 'cell', 'position', 'rba_number', 'address1', 'address2', 'city', 'state', 'zipcode'):
        if field in data:
            setattr(employee, field, data[field])

    if 'position' in data and employee.user_type != 'super':
        employee.user_type = _determine_user_type(data.get('position'), employee.user_type)

    if 'user_type' in data and data.get('user_type') in ['admin', 'super', 'supervisor', 'therapist']:
        employee.user_type = data.get('user_type')

    if 'password' in data and data.get('password'):
        employee.set_password(data.get('password'))

    if 'is_active' in data:
        employee.is_active = bool(data.get('is_active'))

    if 'login_enabled' in data:
        employee.login_enabled = bool(data.get('login_enabled'))

    db.session.commit()
    return jsonify(_serialize_emp(employee))


@api_bp.route('/employees/<int:emp_id>', methods=['DELETE'])
@token_required
def delete_employee(emp_id):
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    employee = Employee.query.get_or_404(emp_id)
    if employee.user_type == 'super' and g.current_user.user_type != 'super':
        return jsonify({'error': 'cannot delete super user'}), 403

    active_client = Client.query.filter_by(supervisor_id=employee.id, is_active=True).first()
    if active_client:
        return jsonify({'error': 'cannot delete employee supervising active clients'}), 400

    db.session.delete(employee)
    db.session.commit()
    return jsonify({'status': 'deleted'})
