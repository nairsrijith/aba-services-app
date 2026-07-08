from flask import request, jsonify
from . import api_bp, token_required
from app import db
from app.models import Intervention
from datetime import date, time, datetime


def _serialize_int(i: Intervention):
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


def _compute_duration(start_time, end_time):
    if end_time <= start_time:
        return None
    delta = datetime.combine(date.min, end_time) - datetime.combine(date.min, start_time)
    return round(delta.seconds / 3600.0, 2)


@api_bp.route('/interventions', methods=['GET'])
@token_required
def list_interventions():
    items = Intervention.query.order_by(Intervention.date.desc()).limit(200).all()
    return jsonify([_serialize_int(i) for i in items])


@api_bp.route('/interventions/<int:int_id>', methods=['GET'])
@token_required
def get_intervention(int_id):
    i = Intervention.query.get_or_404(int_id)
    return jsonify(_serialize_int(i))


@api_bp.route('/interventions', methods=['POST'])
@token_required
def create_intervention():
    data = request.get_json() or {}
    required = ['client_id', 'employee_id', 'intervention_type', 'date', 'start_time', 'end_time']
    for f in required:
        if f not in data:
            return jsonify({'error': f'missing field: {f}'}), 400

    try:
        d = date.fromisoformat(data.get('date'))
        st = time.fromisoformat(data.get('start_time'))
        et = time.fromisoformat(data.get('end_time'))
    except Exception:
        return jsonify({'error': 'date/time fields must be ISO format'}), 400

    duration = _compute_duration(st, et)
    if duration is None:
        return jsonify({'error': 'end_time must be later than start_time'}), 400

    employee_id = data.get('employee_id')
    client_id = data.get('client_id')
    intervention_type = data.get('intervention_type')

    if Intervention.has_overlap(employee_id, d, st, et):
        return jsonify({'error': 'session overlap detected for this employee'}), 400

    i = Intervention(
        client_id=client_id,
        employee_id=employee_id,
        intervention_type=intervention_type,
        date=d,
        start_time=st,
        end_time=et,
        duration=duration,
        file_names='[]',
        invoiced=False,
        invoice_number=None
    )
    db.session.add(i)
    db.session.commit()
    return jsonify(_serialize_int(i)), 201


@api_bp.route('/interventions/<int:int_id>', methods=['PUT'])
@token_required
def update_intervention(int_id):
    i = Intervention.query.get_or_404(int_id)
    data = request.get_json() or {}
    for k in ('client_id', 'employee_id', 'intervention_type', 'invoice_number'):
        if k in data:
            setattr(i, k, data[k])

    if 'date' in data:
        try:
            i.date = date.fromisoformat(data.get('date'))
        except Exception:
            return jsonify({'error': 'date must be YYYY-MM-DD'}), 400

    if 'start_time' in data:
        try:
            i.start_time = time.fromisoformat(data.get('start_time'))
        except Exception:
            return jsonify({'error': 'start_time must be HH:MM format'}), 400

    if 'end_time' in data:
        try:
            i.end_time = time.fromisoformat(data.get('end_time'))
        except Exception:
            return jsonify({'error': 'end_time must be HH:MM format'}), 400

    duration = _compute_duration(i.start_time, i.end_time)
    if duration is None:
        return jsonify({'error': 'end_time must be later than start_time'}), 400
    i.duration = duration

    if Intervention.has_overlap(i.employee_id, i.date, i.start_time, i.end_time, exclude_id=i.id):
        return jsonify({'error': 'session overlap detected for this employee'}), 400

    db.session.commit()
    return jsonify(_serialize_int(i))


@api_bp.route('/interventions/<int:int_id>', methods=['DELETE'])
@token_required
def delete_intervention(int_id):
    i = Intervention.query.get_or_404(int_id)
    db.session.delete(i)
    db.session.commit()
    return jsonify({'status': 'deleted'})
