from flask import request, jsonify, g
from . import api_bp, token_required
from app import db
from app.models import Mileage, MileageRate
from datetime import date


def _serialize_mileage(m: Mileage):
    return {
        'id': m.id,
        'employee_id': m.employee_id,
        'client_id': m.client_id,
        'date': m.date.isoformat(),
        'distance': float(m.distance),
        'description': m.description,
        'mileage_rate_id': m.mileage_rate_id,
        'cost': float(m.cost),
        'invoice_number': m.invoice_number,
        'invoiced': bool(m.invoiced),
        'is_paid': bool(m.is_paid)
    }


def _serialize_rate(r: MileageRate):
    return {
        'id': r.id,
        'rate': float(r.rate),
        'effective_date': r.effective_date.isoformat(),
        'created_date': r.created_date.isoformat() if r.created_date else None
    }


def _require_admin():
    if g.current_user.user_type not in ['admin', 'super']:
        return jsonify({'error': 'admin access required'}), 403
    return None


@api_bp.route('/mileages', methods=['GET'])
@token_required
def list_mileages():
    ms = Mileage.query.order_by(Mileage.date.desc()).limit(200).all()
    return jsonify([_serialize_mileage(m) for m in ms])


@api_bp.route('/mileages/<int:mileage_id>', methods=['GET'])
@token_required
def get_mileage(mileage_id):
    m = Mileage.query.get_or_404(mileage_id)
    return jsonify(_serialize_mileage(m))


@api_bp.route('/mileages', methods=['POST'])
@token_required
def create_mileage():
    data = request.get_json() or {}
    required = ['employee_id', 'client_id', 'date', 'distance', 'mileage_rate_id']
    for field in required:
        if field not in data:
            return jsonify({'error': f'missing field: {field}'}), 400
    try:
        d = date.fromisoformat(data.get('date'))
    except Exception:
        return jsonify({'error': 'date must be YYYY-MM-DD'}), 400

    mrate = MileageRate.query.get(data.get('mileage_rate_id'))
    if not mrate:
        return jsonify({'error': 'invalid mileage_rate_id'}), 400

    m = Mileage(
        employee_id=data.get('employee_id'),
        client_id=data.get('client_id'),
        date=d,
        distance=float(data.get('distance')),
        mileage_rate_id=mrate.id,
        description=data.get('description')
    )
    db.session.add(m)
    db.session.commit()
    return jsonify(_serialize_mileage(m)), 201


@api_bp.route('/mileages/<int:mileage_id>', methods=['PUT'])
@token_required
def update_mileage(mileage_id):
    m = Mileage.query.get_or_404(mileage_id)
    data = request.get_json() or {}

    if 'employee_id' in data:
        m.employee_id = data.get('employee_id')
    if 'client_id' in data:
        m.client_id = data.get('client_id')
    if 'date' in data:
        try:
            m.date = date.fromisoformat(data.get('date'))
        except Exception:
            return jsonify({'error': 'date must be YYYY-MM-DD'}), 400
    if 'distance' in data:
        try:
            m.distance = float(data.get('distance'))
        except Exception:
            return jsonify({'error': 'distance must be numeric'}), 400
    if 'description' in data:
        m.description = data.get('description')
    if 'mileage_rate_id' in data:
        mrate = MileageRate.query.get(data.get('mileage_rate_id'))
        if not mrate:
            return jsonify({'error': 'invalid mileage_rate_id'}), 400
        m.mileage_rate_id = mrate.id

    # Recalculate cost if rate or distance changed.
    if m.mileage_rate:
        m.cost = round(float(m.distance) * float(m.mileage_rate.rate), 2)

    if 'invoice_number' in data:
        m.invoice_number = data.get('invoice_number')
    if 'invoiced' in data:
        m.invoiced = bool(data.get('invoiced'))
    if 'is_paid' in data:
        m.is_paid = bool(data.get('is_paid'))

    db.session.commit()
    return jsonify(_serialize_mileage(m))


@api_bp.route('/mileages/<int:mileage_id>', methods=['DELETE'])
@token_required
def delete_mileage(mileage_id):
    m = Mileage.query.get_or_404(mileage_id)
    db.session.delete(m)
    db.session.commit()
    return jsonify({'status': 'deleted'})


@api_bp.route('/mileage_rates', methods=['GET'])
@token_required
def list_mileage_rates():
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    rates = MileageRate.query.order_by(MileageRate.effective_date.desc()).all()
    return jsonify([_serialize_rate(r) for r in rates])


@api_bp.route('/mileage_rates/<int:rate_id>', methods=['GET'])
@token_required
def get_mileage_rate(rate_id):
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    r = MileageRate.query.get_or_404(rate_id)
    return jsonify(_serialize_rate(r))


@api_bp.route('/mileage_rates', methods=['POST'])
@token_required
def create_mileage_rate():
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    data = request.get_json() or {}
    required = ['rate', 'effective_date']
    for field in required:
        if field not in data:
            return jsonify({'error': f'missing field: {field}'}), 400
    try:
        rate_value = float(data.get('rate'))
        effective_date = date.fromisoformat(data.get('effective_date'))
    except Exception:
        return jsonify({'error': 'rate must be numeric and effective_date must be YYYY-MM-DD'}), 400

    r = MileageRate(rate=rate_value, effective_date=effective_date)
    db.session.add(r)
    db.session.commit()
    return jsonify(_serialize_rate(r)), 201


@api_bp.route('/mileage_rates/<int:rate_id>', methods=['PUT'])
@token_required
def update_mileage_rate(rate_id):
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    r = MileageRate.query.get_or_404(rate_id)
    data = request.get_json() or {}
    if 'rate' in data:
        try:
            r.rate = float(data.get('rate'))
        except Exception:
            return jsonify({'error': 'rate must be numeric'}), 400
    if 'effective_date' in data:
        try:
            r.effective_date = date.fromisoformat(data.get('effective_date'))
        except Exception:
            return jsonify({'error': 'effective_date must be YYYY-MM-DD'}), 400
    db.session.commit()
    return jsonify(_serialize_rate(r))


@api_bp.route('/mileage_rates/<int:rate_id>', methods=['DELETE'])
@token_required
def delete_mileage_rate(rate_id):
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    r = MileageRate.query.get_or_404(rate_id)
    db.session.delete(r)
    db.session.commit()
    return jsonify({'status': 'deleted'})
