from flask import current_app, request, jsonify
from . import api_bp, token_required
from app import db
from app.models import Client
from datetime import date


def _serialize_client(c: Client):
    return {
        'id': c.id,
        'firstname': c.firstname,
        'lastname': c.lastname,
        'dob': c.dob.isoformat() if c.dob else None,
        'gender': c.gender,
        'address1': c.address1,
        'city': c.city,
        'state': c.state,
        'zipcode': c.zipcode,
        'is_active': bool(c.is_active)
    }


@api_bp.route('/clients', methods=['GET'])
@token_required
def list_clients():
    clients = Client.query.order_by(Client.firstname).all()
    return jsonify([_serialize_client(c) for c in clients])


@api_bp.route('/clients/<int:client_id>', methods=['GET'])
@token_required
def get_client(client_id):
    c = Client.query.get_or_404(client_id)
    return jsonify(_serialize_client(c))


@api_bp.route('/clients', methods=['POST'])
@token_required
def create_client():
    data = request.get_json() or {}
    required = ['firstname', 'dob', 'gender', 'address1', 'city', 'state', 'zipcode']
    for f in required:
        if f not in data:
            return jsonify({'error': f"missing field: {f}"}), 400
    try:
        dob = date.fromisoformat(data.get('dob'))
    except Exception:
        return jsonify({'error': 'dob must be YYYY-MM-DD'}), 400

    client = Client(
        firstname=data.get('firstname'),
        lastname=data.get('lastname'),
        dob=dob,
        gender=data.get('gender'),
        address1=data.get('address1'),
        address2=data.get('address2'),
        city=data.get('city'),
        state=data.get('state'),
        zipcode=data.get('zipcode'),
        supervisor_id=data.get('supervisor_id'),
        cost_supervision=data.get('cost_supervision', 0.0),
        cost_therapy=data.get('cost_therapy', 0.0),
        is_active=data.get('is_active', True)
    )
    db.session.add(client)
    db.session.commit()
    return jsonify(_serialize_client(client)), 201


@api_bp.route('/clients/<int:client_id>', methods=['PUT'])
@token_required
def update_client(client_id):
    c = Client.query.get_or_404(client_id)
    data = request.get_json() or {}
    # allow updating a subset of fields
    for k in ('firstname','lastname','gender','address1','address2','city','state','zipcode'):
        if k in data:
            setattr(c, k, data[k])
    if 'dob' in data:
        try:
            c.dob = date.fromisoformat(data.get('dob'))
        except Exception:
            return jsonify({'error': 'dob must be YYYY-MM-DD'}), 400
    if 'is_active' in data:
        c.is_active = bool(data.get('is_active'))
    db.session.commit()
    return jsonify(_serialize_client(c))


@api_bp.route('/clients/<int:client_id>', methods=['DELETE'])
@token_required
def delete_client(client_id):
    c = Client.query.get_or_404(client_id)
    db.session.delete(c)
    db.session.commit()
    return jsonify({'status': 'deleted'})
