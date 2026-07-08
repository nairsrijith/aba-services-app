from flask import request, jsonify, g
from . import api_bp, token_required
from app import db
from app.models import Designation, Activity, AppSettings, Employee, Intervention


def _serialize_designation(d: Designation):
    return {'designation': d.designation}


def _serialize_activity(a: Activity):
    return {'activity_name': a.activity_name, 'activity_category': a.activity_category}


def _serialize_settings(s: AppSettings):
    return {
        'id': s.id,
        'org_name': s.org_name,
        'org_address': s.org_address,
        'org_phone': s.org_phone,
        'org_email': s.org_email,
        'payment_email': s.payment_email,
        'logo_path': s.logo_path,
        'gmail_client_id': s.gmail_client_id,
        'gmail_client_secret': s.gmail_client_secret,
        'gmail_refresh_token': s.gmail_refresh_token,
        'testing_mode': bool(s.testing_mode),
        'testing_email': s.testing_email,
        'default_cc': s.default_cc,
        'invoice_reminder_enabled': bool(s.invoice_reminder_enabled),
        'invoice_reminder_days': s.invoice_reminder_days,
        'invoice_reminder_repeat_enabled': bool(s.invoice_reminder_repeat_enabled),
        'invoice_reminder_repeat_days': s.invoice_reminder_repeat_days,
        'invoice_reminder_time': s.invoice_reminder_time
    }


def _require_admin():
    if g.current_user.user_type not in ['admin', 'super']:
        return jsonify({'error': 'admin access required'}), 403
    return None


@api_bp.route('/manage/designations', methods=['GET'])
@token_required
def list_designations():
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    designations = Designation.query.order_by(Designation.designation).all()
    return jsonify([_serialize_designation(d) for d in designations])


@api_bp.route('/manage/designations', methods=['POST'])
@token_required
def create_designation():
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    data = request.get_json() or {}
    name = (data.get('designation') or data.get('name') or '').strip().title()
    if not name:
        return jsonify({'error': 'designation is required'}), 400

    if Designation.query.filter_by(designation=name).first():
        return jsonify({'error': 'designation already exists'}), 400

    designation = Designation(designation=name)
    db.session.add(designation)
    db.session.commit()
    return jsonify(_serialize_designation(designation)), 201


@api_bp.route('/manage/designations/<string:designation_name>', methods=['DELETE'])
@token_required
def delete_designation(designation_name):
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    designation = Designation.query.filter_by(designation=designation_name).first_or_404()
    in_use = Employee.query.filter_by(position=designation.designation).count()
    if in_use:
        return jsonify({'error': f'designation is used by {in_use} employee(s)'}), 400

    db.session.delete(designation)
    db.session.commit()
    return jsonify({'status': 'deleted'})


@api_bp.route('/manage/activities', methods=['GET'])
@token_required
def list_activities():
    admin_check = _require_admin()
    if admin_check:
        return admin_check
    activities = Activity.query.order_by(Activity.activity_name).all()
    return jsonify([_serialize_activity(a) for a in activities])


@api_bp.route('/manage/activities', methods=['POST'])
@token_required
def create_activity():
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    data = request.get_json() or {}
    name = (data.get('activity_name') or data.get('name') or '').strip().title()
    category = (data.get('activity_category') or data.get('category') or '').strip().title()
    if not name or not category:
        return jsonify({'error': 'activity_name and activity_category are required'}), 400

    if Activity.query.filter_by(activity_name=name).first():
        return jsonify({'error': 'activity already exists'}), 400

    activity = Activity(activity_name=name, activity_category=category)
    db.session.add(activity)
    db.session.commit()
    return jsonify(_serialize_activity(activity)), 201


@api_bp.route('/manage/activities/<string:activity_name>', methods=['DELETE'])
@token_required
def delete_activity(activity_name):
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    activity = Activity.query.filter_by(activity_name=activity_name).first_or_404()
    in_use = Intervention.query.filter_by(intervention_type=activity.activity_name).count()
    if in_use:
        return jsonify({'error': f'activity is used by {in_use} intervention(s)'}), 400

    db.session.delete(activity)
    db.session.commit()
    return jsonify({'status': 'deleted'})


@api_bp.route('/manage/settings', methods=['GET'])
@token_required
def get_settings():
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    settings = AppSettings.get()
    if not settings:
        return jsonify({'error': 'settings unavailable'}), 500
    return jsonify(_serialize_settings(settings))


@api_bp.route('/manage/settings', methods=['PUT'])
@token_required
def update_settings():
    admin_check = _require_admin()
    if admin_check:
        return admin_check

    settings = AppSettings.get()
    if not settings:
        settings = AppSettings()

    data = request.get_json() or {}
    for field in (
        'org_name', 'org_address', 'org_phone', 'org_email', 'payment_email',
        'gmail_client_id', 'gmail_client_secret', 'gmail_refresh_token',
        'testing_mode', 'testing_email', 'default_cc',
        'invoice_reminder_enabled', 'invoice_reminder_days',
        'invoice_reminder_repeat_enabled', 'invoice_reminder_repeat_days',
        'invoice_reminder_time', 'logo_path'
    ):
        if field in data:
            setattr(settings, field, data[field])

    if data.get('clear_logo'):
        settings.logo_path = None

    db.session.add(settings)
    db.session.commit()
    return jsonify(_serialize_settings(settings))
