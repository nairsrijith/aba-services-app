from flask import request, jsonify, g
from . import api_bp, token_required
from app import db
from app.models import PayRate, PayStub, PayStubItem, Employee
from datetime import date


def _serialize_payrate(p: PayRate):
    return {
        'id': p.id,
        'employee_id': p.employee_id,
        'client_id': p.client_id,
        'rate': float(p.rate),
        'effective_date': p.effective_date.isoformat() if p.effective_date else None
    }


def _serialize_paystub_item(item: PayStubItem):
    return {
        'id': item.id,
        'intervention_id': item.intervention_id,
        'client_id': item.client_id,
        'rate': float(item.rate),
        'hours': float(item.hours),
        'amount': float(item.amount)
    }


def _serialize_paystub(s: PayStub):
    return {
        'id': s.id,
        'employee_id': s.employee_id,
        'period_start': s.period_start.isoformat(),
        'period_end': s.period_end.isoformat(),
        'generated_date': s.generated_date.isoformat() if s.generated_date else None,
        'total_hours': float(s.total_hours),
        'total_amount': float(s.total_amount),
        'notes': s.notes,
        'email_sent': bool(s.email_sent),
        'items': [_serialize_paystub_item(item) for item in s.items]
    }


def _require_admin():
    if g.current_user.user_type not in ['admin', 'super']:
        return jsonify({'error': 'admin access required'}), 403
    return None


@api_bp.route('/payrates', methods=['GET'])
@token_required
def list_payrates():
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    rates = PayRate.query.order_by(PayRate.effective_date.desc()).limit(200).all()
    return jsonify([_serialize_payrate(r) for r in rates])


@api_bp.route('/payrates/<int:rate_id>', methods=['GET'])
@token_required
def get_payrate(rate_id):
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    rate = PayRate.query.get_or_404(rate_id)
    return jsonify(_serialize_payrate(rate))


@api_bp.route('/payrates', methods=['POST'])
@token_required
def create_payrate():
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    data = request.get_json() or {}
    required = ['employee_id', 'rate', 'effective_date']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'missing field: {field}'}), 400

    try:
        effective_date = date.fromisoformat(data.get('effective_date'))
        rate_value = float(data.get('rate'))
    except Exception:
        return jsonify({'error': 'effective_date must be YYYY-MM-DD and rate must be numeric'}), 400

    payrate = PayRate(
        employee_id=data.get('employee_id'),
        client_id=data.get('client_id'),
        rate=rate_value,
        effective_date=effective_date
    )
    db.session.add(payrate)
    db.session.commit()
    return jsonify(_serialize_payrate(payrate)), 201


@api_bp.route('/payrates/<int:rate_id>', methods=['PUT'])
@token_required
def update_payrate(rate_id):
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    payrate = PayRate.query.get_or_404(rate_id)
    data = request.get_json() or {}

    if 'employee_id' in data:
        payrate.employee_id = data.get('employee_id')
    if 'client_id' in data:
        payrate.client_id = data.get('client_id')
    if 'rate' in data:
        try:
            payrate.rate = float(data.get('rate'))
        except Exception:
            return jsonify({'error': 'rate must be numeric'}), 400
    if 'effective_date' in data:
        try:
            payrate.effective_date = date.fromisoformat(data.get('effective_date'))
        except Exception:
            return jsonify({'error': 'effective_date must be YYYY-MM-DD'}), 400

    db.session.commit()
    return jsonify(_serialize_payrate(payrate))


@api_bp.route('/payrates/<int:rate_id>', methods=['DELETE'])
@token_required
def delete_payrate(rate_id):
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    payrate = PayRate.query.get_or_404(rate_id)
    db.session.delete(payrate)
    db.session.commit()
    return jsonify({'status': 'deleted'})


@api_bp.route('/paystubs', methods=['GET'])
@token_required
def list_paystubs():
    if g.current_user.user_type in ['admin', 'super']:
        stubs = PayStub.query.order_by(PayStub.generated_date.desc()).limit(200).all()
    else:
        stubs = PayStub.query.filter_by(employee_id=g.current_user.id).order_by(PayStub.generated_date.desc()).limit(200).all()
    return jsonify([_serialize_paystub(s) for s in stubs])


@api_bp.route('/paystubs/<int:stub_id>', methods=['GET'])
@token_required
def get_paystub(stub_id):
    paystub = PayStub.query.get_or_404(stub_id)
    if g.current_user.user_type not in ['admin', 'super'] and paystub.employee_id != g.current_user.id:
        return jsonify({'error': 'access denied'}), 403
    return jsonify(_serialize_paystub(paystub))


@api_bp.route('/paystubs', methods=['POST'])
@token_required
def create_paystub():
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    data = request.get_json() or {}
    required = ['employee_id', 'period_start', 'period_end', 'generated_date', 'total_hours', 'total_amount', 'items']
    for field in required:
        if field not in data:
            return jsonify({'error': f'missing field: {field}'}), 400

    try:
        period_start = date.fromisoformat(data.get('period_start'))
        period_end = date.fromisoformat(data.get('period_end'))
        generated_date = date.fromisoformat(data.get('generated_date'))
        total_hours = float(data.get('total_hours'))
        total_amount = float(data.get('total_amount'))
    except Exception:
        return jsonify({'error': 'invalid paystub date or numeric fields'}), 400

    paystub = PayStub(
        employee_id=data.get('employee_id'),
        period_start=period_start,
        period_end=period_end,
        generated_date=generated_date,
        total_hours=total_hours,
        total_amount=total_amount,
        notes=data.get('notes'),
        email_sent=bool(data.get('email_sent', False))
    )
    db.session.add(paystub)
    db.session.flush()

    items = data.get('items') or []
    for item in items:
        paystub_item = PayStubItem(
            paystub_id=paystub.id,
            intervention_id=item.get('intervention_id'),
            client_id=item.get('client_id'),
            rate=float(item.get('rate', 0)),
            hours=float(item.get('hours', 0)),
            amount=float(item.get('amount', 0))
        )
        db.session.add(paystub_item)

    db.session.commit()
    return jsonify(_serialize_paystub(paystub)), 201


@api_bp.route('/paystubs/<int:stub_id>', methods=['PUT'])
@token_required
def update_paystub(stub_id):
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    paystub = PayStub.query.get_or_404(stub_id)
    data = request.get_json() or {}

    if 'employee_id' in data:
        paystub.employee_id = data.get('employee_id')
    if 'period_start' in data:
        try:
            paystub.period_start = date.fromisoformat(data.get('period_start'))
        except Exception:
            return jsonify({'error': 'period_start must be YYYY-MM-DD'}), 400
    if 'period_end' in data:
        try:
            paystub.period_end = date.fromisoformat(data.get('period_end'))
        except Exception:
            return jsonify({'error': 'period_end must be YYYY-MM-DD'}), 400
    if 'generated_date' in data:
        try:
            paystub.generated_date = date.fromisoformat(data.get('generated_date'))
        except Exception:
            return jsonify({'error': 'generated_date must be YYYY-MM-DD'}), 400
    if 'total_hours' in data:
        try:
            paystub.total_hours = float(data.get('total_hours'))
        except Exception:
            return jsonify({'error': 'total_hours must be numeric'}), 400
    if 'total_amount' in data:
        try:
            paystub.total_amount = float(data.get('total_amount'))
        except Exception:
            return jsonify({'error': 'total_amount must be numeric'}), 400
    if 'notes' in data:
        paystub.notes = data.get('notes')
    if 'email_sent' in data:
        paystub.email_sent = bool(data.get('email_sent'))

    if 'items' in data:
        PayStubItem.query.filter_by(paystub_id=paystub.id).delete()
        for item in data.get('items', []):
            paystub_item = PayStubItem(
                paystub_id=paystub.id,
                intervention_id=item.get('intervention_id'),
                client_id=item.get('client_id'),
                rate=float(item.get('rate', 0)),
                hours=float(item.get('hours', 0)),
                amount=float(item.get('amount', 0))
            )
            db.session.add(paystub_item)

    db.session.commit()
    return jsonify(_serialize_paystub(paystub))


@api_bp.route('/paystubs/<int:stub_id>', methods=['DELETE'])
@token_required
def delete_paystub(stub_id):
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    paystub = PayStub.query.get_or_404(stub_id)
    db.session.delete(paystub)
    db.session.commit()
    return jsonify({'status': 'deleted'})
