from flask import request, jsonify, g
from . import api_bp, token_required
from app.models import Employee, Client, Intervention, Invoice, PayStub
from datetime import date


def _serialize_employee(e: Employee):
    return {
        'id': e.id,
        'firstname': e.firstname,
        'lastname': e.lastname,
        'position': e.position,
        'email': e.email,
        'cell': e.cell,
        'address1': e.address1,
        'address2': e.address2,
        'city': e.city,
        'state': e.state,
        'zipcode': e.zipcode,
        'is_active': bool(e.is_active)
    }


def _serialize_client(c: Client):
    return {
        'id': c.id,
        'firstname': c.firstname,
        'lastname': c.lastname,
        'dob': c.dob.isoformat() if c.dob else None,
        'gender': c.gender,
        'parentname': c.parentname,
        'parentemail': c.parentemail,
        'parentcell': c.parentcell,
        'supervisor_id': c.supervisor_id,
        'address1': c.address1,
        'address2': c.address2,
        'city': c.city,
        'state': c.state,
        'zipcode': c.zipcode,
        'is_active': bool(c.is_active)
    }


def _serialize_intervention(i: Intervention):
    return {
        'id': i.id,
        'client_id': i.client_id,
        'employee_id': i.employee_id,
        'intervention_type': i.intervention_type,
        'date': i.date.isoformat() if i.date else None,
        'start_time': i.start_time.strftime('%H:%M') if i.start_time else None,
        'end_time': i.end_time.strftime('%H:%M') if i.end_time else None,
        'duration': float(i.duration) if i.duration is not None else None,
        'invoiced': bool(i.invoiced),
        'invoice_number': i.invoice_number
    }


def _serialize_invoice(inv: Invoice):
    return {
        'id': inv.id,
        'invoice_number': inv.invoice_number,
        'client_id': inv.client_id,
        'invoiced_date': inv.invoiced_date.isoformat() if inv.invoiced_date else None,
        'payby_date': inv.payby_date.isoformat() if inv.payby_date else None,
        'date_from': inv.date_from.isoformat() if inv.date_from else None,
        'date_to': inv.date_to.isoformat() if inv.date_to else None,
        'total_cost': float(inv.total_cost or 0),
        'status': inv.status,
        'paid_date': inv.paid_date.isoformat() if inv.paid_date else None
    }


def _serialize_paystub(s: PayStub):
    return {
        'id': s.id,
        'employee_id': s.employee_id,
        'period_start': s.period_start.isoformat() if s.period_start else None,
        'period_end': s.period_end.isoformat() if s.period_end else None,
        'generated_date': s.generated_date.isoformat() if s.generated_date else None,
        'total_hours': float(s.total_hours),
        'total_amount': float(s.total_amount),
        'email_sent': bool(s.email_sent)
    }


def _require_report_access():
    if not getattr(g.current_user, 'position', None) == 'Administrator':
        return jsonify({'error': 'administrator access required'}), 403
    return None


def _parse_list_param(value):
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


@api_bp.route('/reports/employees', methods=['GET'])
@token_required
def employees_report():
    admin_check = _require_report_access()
    if admin_check:
        return admin_check

    query = Employee.query.filter(Employee.user_type != 'super')
    position = request.args.get('position')
    city = request.args.get('city')
    state = request.args.get('state')
    active = request.args.get('active')

    if position:
        query = query.filter(Employee.position.in_(_parse_list_param(position)))
    if city:
        query = query.filter(Employee.city.in_(_parse_list_param(city)))
    if state:
        query = query.filter(Employee.state.in_(_parse_list_param(state)))
    if active == 'active':
        query = query.filter_by(is_active=True)
    elif active == 'inactive':
        query = query.filter_by(is_active=False)

    results = query.order_by(Employee.firstname).all()
    return jsonify([_serialize_employee(e) for e in results])


@api_bp.route('/reports/clients', methods=['GET'])
@token_required
def clients_report():
    admin_check = _require_report_access()
    if admin_check:
        return admin_check

    query = Client.query.filter_by(is_active=True)
    city = request.args.get('city')
    state = request.args.get('state')
    supervisor_id = request.args.get('supervisor_id')

    if city:
        query = query.filter(Client.city.in_(_parse_list_param(city)))
    if state:
        query = query.filter(Client.state.in_(_parse_list_param(state)))
    if supervisor_id:
        query = query.filter_by(supervisor_id=int(supervisor_id))

    results = query.order_by(Client.firstname).all()
    return jsonify([_serialize_client(c) for c in results])


@api_bp.route('/reports/sessions', methods=['GET'])
@token_required
def sessions_report():
    admin_check = _require_report_access()
    if admin_check:
        return admin_check

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    try:
        start = date.fromisoformat(start_date) if start_date else date.today().replace(day=1)
        end = date.fromisoformat(end_date) if end_date else (date.today().replace(day=1) + date.resolution * 31).replace(day=1) - date.resolution
    except Exception:
        return jsonify({'error': 'invalid date format; expected YYYY-MM-DD'}), 400

    query = Intervention.query.filter(Intervention.date >= start, Intervention.date <= end)
    client_id = request.args.get('client_id')
    employee_id = request.args.get('employee_id')
    if client_id:
        query = query.filter_by(client_id=int(client_id))
    if employee_id:
        query = query.filter_by(employee_id=int(employee_id))

    results = query.order_by(Intervention.date).all()
    return jsonify({'start_date': start.isoformat(), 'end_date': end.isoformat(), 'interventions': [_serialize_intervention(i) for i in results]})


@api_bp.route('/reports/invoices', methods=['GET'])
@token_required
def invoices_report():
    admin_check = _require_report_access()
    if admin_check:
        return admin_check

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    try:
        start = date.fromisoformat(start_date) if start_date else date.today().replace(day=1)
        end = date.fromisoformat(end_date) if end_date else (date.today().replace(day=1) + date.resolution * 31).replace(day=1) - date.resolution
    except Exception:
        return jsonify({'error': 'invalid date format; expected YYYY-MM-DD'}), 400

    query = Invoice.query.filter(Invoice.invoiced_date >= start, Invoice.invoiced_date <= end)
    client_id = request.args.get('client_id')
    if client_id:
        query = query.filter_by(client_id=int(client_id))

    results = query.order_by(Invoice.invoiced_date.desc()).all()
    return jsonify({'start_date': start.isoformat(), 'end_date': end.isoformat(), 'invoices': [_serialize_invoice(inv) for inv in results]})


@api_bp.route('/reports/paystubs', methods=['GET'])
@token_required
def paystubs_report():
    admin_check = _require_report_access()
    if admin_check:
        return admin_check

    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    try:
        start = date.fromisoformat(start_date) if start_date else date.today().replace(day=1)
        end = date.fromisoformat(end_date) if end_date else (date.today().replace(day=1) + date.resolution * 31).replace(day=1) - date.resolution
    except Exception:
        return jsonify({'error': 'invalid date format; expected YYYY-MM-DD'}), 400

    query = PayStub.query.filter(PayStub.generated_date >= start, PayStub.generated_date <= end)
    employee_id = request.args.get('employee_id')
    if employee_id:
        query = query.filter_by(employee_id=int(employee_id))

    results = query.order_by(PayStub.generated_date.desc()).all()
    return jsonify({'start_date': start.isoformat(), 'end_date': end.isoformat(), 'paystubs': [_serialize_paystub(p) for p in results]})
