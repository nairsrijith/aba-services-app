import json
from datetime import date
from flask import request, jsonify, g
from . import api_bp, token_required
from app import db
from app.models import Invoice, Intervention, Mileage, Client, Activity


def _serialize_invoice(inv: Invoice):
    return {
        'id': inv.id,
        'invoice_number': inv.invoice_number,
        'client_id': inv.client_id,
        'invoiced_date': inv.invoiced_date.isoformat() if inv.invoiced_date else None,
        'payby_date': inv.payby_date.isoformat() if inv.payby_date else None,
        'date_from': inv.date_from.isoformat() if inv.date_from else None,
        'date_to': inv.date_to.isoformat() if inv.date_to else None,
        'invoice_items': json.loads(inv.invoice_items) if inv.invoice_items else [],
        'total_cost': float(inv.total_cost or 0),
        'status': inv.status,
        'paid_date': inv.paid_date.isoformat() if inv.paid_date else None,
        'payment_comments': inv.payment_comments
    }


def _require_admin():
    if g.current_user.user_type not in ['admin', 'super']:
        return jsonify({'error': 'admin access required'}), 403
    return None


def _resolve_intervention_cost(intervention, client):
    activity_map = {a.activity_name: a.activity_category for a in Activity.query.all()}
    category = activity_map.get(intervention.intervention_type, '').lower()
    if category == 'therapy':
        return float(client.cost_therapy or 0)
    if category == 'supervision':
        return float(client.cost_supervision or 0)
    return 0.0


@api_bp.route('/invoices', methods=['GET'])
@token_required
def list_invoices():
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    invs = Invoice.query.order_by(Invoice.invoiced_date.desc()).limit(200).all()
    return jsonify([_serialize_invoice(i) for i in invs])


@api_bp.route('/invoices/<string:invoice_number>', methods=['GET'])
@token_required
def get_invoice(invoice_number):
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    inv = Invoice.query.filter_by(invoice_number=invoice_number).first_or_404()
    return jsonify(_serialize_invoice(inv))


@api_bp.route('/invoices', methods=['POST'])
@token_required
def create_invoice():
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    data = request.get_json() or {}
    required = ['client_id', 'date_from', 'date_to', 'selected_interventions']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'missing field: {field}'}), 400

    try:
        date_from = date.fromisoformat(data.get('date_from'))
        date_to = date.fromisoformat(data.get('date_to'))
    except Exception:
        return jsonify({'error': 'date_from and date_to must be YYYY-MM-DD'}), 400

    client = Client.query.get_or_404(data.get('client_id'))
    selected_interventions = data.get('selected_interventions', [])
    selected_mileages = data.get('selected_mileages', [])

    interventions = Intervention.query.filter(
        Intervention.id.in_(selected_interventions),
        Intervention.client_id == client.id,
        Intervention.invoiced == False,
        Intervention.date >= date_from,
        Intervention.date <= date_to
    ).all()
    if len(interventions) != len(selected_interventions):
        return jsonify({'error': 'one or more selected interventions are invalid or already invoiced'}), 400

    mileages = []
    if selected_mileages:
        mileages = Mileage.query.filter(
            Mileage.id.in_(selected_mileages),
            Mileage.client_id == client.id,
            Mileage.invoiced == False,
            Mileage.date >= date_from,
            Mileage.date <= date_to
        ).all()
        if len(mileages) != len(selected_mileages):
            return jsonify({'error': 'one or more selected mileages are invalid or already invoiced'}), 400

    invoice_items = []
    total_cost = 0.0
    for intervention in interventions:
        rate = _resolve_intervention_cost(intervention, client)
        cost = float(intervention.duration or 0) * rate
        invoice_items.append({
            'type': 'intervention',
            'intervention_id': intervention.id,
            'date': intervention.date.isoformat() if intervention.date else None,
            'activity': intervention.intervention_type,
            'duration': float(intervention.duration or 0),
            'rate': rate,
            'cost': cost
        })
        total_cost += cost

    for mileage in mileages:
        invoice_items.append({
            'type': 'mileage',
            'mileage_id': mileage.id,
            'date': mileage.date.isoformat() if mileage.date else None,
            'description': mileage.description or 'Mileage',
            'distance': float(mileage.distance or 0),
            'rate': float(mileage.mileage_rate.rate if mileage.mileage_rate else 0),
            'cost': float(mileage.cost or 0)
        })
        total_cost += float(mileage.cost or 0)

    invoice_number = Invoice.generate_invoice_number()
    invoice = Invoice(
        client_id=client.id,
        invoice_number=invoice_number,
        invoiced_date=date.today(),
        payby_date=date.fromisoformat(data.get('payby_date')) if data.get('payby_date') else date.today(),
        date_from=date_from,
        date_to=date_to,
        total_cost=total_cost,
        status=data.get('status', 'Draft'),
        paid_date=date.fromisoformat(data.get('paid_date')) if data.get('paid_date') else None,
        payment_comments=data.get('payment_comments', ''),
        invoice_items=json.dumps(invoice_items)
    )
    db.session.add(invoice)
    db.session.flush()

    for intervention in interventions:
        intervention.invoiced = True
        intervention.invoice_number = invoice_number
        db.session.add(intervention)

    for mileage in mileages:
        mileage.invoiced = True
        mileage.invoice_number = invoice_number
        db.session.add(mileage)

    db.session.commit()
    return jsonify(_serialize_invoice(invoice)), 201


@api_bp.route('/invoices/<string:invoice_number>', methods=['PUT'])
@token_required
def update_invoice(invoice_number):
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    invoice = Invoice.query.filter_by(invoice_number=invoice_number).first_or_404()
    data = request.get_json() or {}

    if 'payby_date' in data:
        try:
            invoice.payby_date = date.fromisoformat(data.get('payby_date'))
        except Exception:
            return jsonify({'error': 'payby_date must be YYYY-MM-DD'}), 400

    if 'status' in data:
        invoice.status = data.get('status')
        if invoice.status == 'Paid' and not invoice.paid_date:
            invoice.paid_date = date.today()
        elif invoice.status != 'Paid':
            invoice.paid_date = None

    if 'paid_date' in data:
        try:
            invoice.paid_date = date.fromisoformat(data.get('paid_date')) if data.get('paid_date') else None
        except Exception:
            return jsonify({'error': 'paid_date must be YYYY-MM-DD'}), 400

    if 'payment_comments' in data:
        invoice.payment_comments = data.get('payment_comments')

    if 'total_cost' in data:
        try:
            invoice.total_cost = float(data.get('total_cost'))
        except Exception:
            return jsonify({'error': 'total_cost must be numeric'}), 400

    db.session.commit()
    return jsonify(_serialize_invoice(invoice))


@api_bp.route('/invoices/<string:invoice_number>', methods=['DELETE'])
@token_required
def delete_invoice(invoice_number):
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    invoice = Invoice.query.filter_by(invoice_number=invoice_number).first_or_404()

    intervention_ids = set()
    if invoice.invoice_items:
        try:
            items = json.loads(invoice.invoice_items)
            intervention_ids.update(item.get('intervention_id') for item in items if item.get('intervention_id'))
        except Exception:
            pass

    linked_interventions = Intervention.query.filter_by(invoice_number=invoice_number).all()
    intervention_ids.update(i.id for i in linked_interventions)

    if intervention_ids:
        Intervention.query.filter(Intervention.id.in_(intervention_ids)).update(
            {
                Intervention.invoiced: False,
                Intervention.invoice_number: None
            },
            synchronize_session=False
        )

    Mileage.query.filter_by(invoice_number=invoice_number).update(
        {
            Mileage.invoiced: False,
            Mileage.invoice_number: None
        },
        synchronize_session=False
    )

    db.session.delete(invoice)
    db.session.commit()
    return jsonify({'status': 'deleted'})
