from flask import Blueprint, render_template, redirect, url_for, abort, flash
from app import db
from app.models import Designation, Activity, Intervention, Employee
from app.manage.forms import DesignationForm, ActivityForm
from flask_login import login_required, current_user
import os
import sys
import subprocess
from flask import request, current_app
from werkzeug.utils import secure_filename
from app.manage.forms import SettingsForm
from app import db
from app.models import AppSettings
from app.utils.settings_utils import get_org_settings

manage_bp = Blueprint('manage', __name__, template_folder='templates')



@manage_bp.route('/designations', methods=['GET', 'POST'])
@login_required
def designations():
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        form = DesignationForm()
        if form.validate_on_submit():
            # Strip whitespace from designation name to prevent duplicates due to spaces
            designation_name = form.name.data.strip().title()
            new_designation = Designation(designation=designation_name)
            db.session.add(new_designation)
            db.session.commit()
            flash('Designation added successfully.', 'success')
            return redirect(url_for('manage.designations'))
        designations = Designation.query.all()
        allocated_designations = [a.position for a in Employee.query.with_entities(Employee.position).distinct()] # Fetch unique designations
        settings = get_org_settings()
        return render_template('designations.html', form=form, designations=designations, allocated_designations=allocated_designations, org_name=settings['org_name'])
    else:
        abort(403)


@manage_bp.route('/activities', methods=['GET', 'POST'])
@login_required
def activities():
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        form = ActivityForm()
        form.category.choices = [("Therapy", "Therapy"), ("Supervision", "Supervision")]
        if form.validate_on_submit():
            # Strip whitespace from activity name to prevent duplicates due to spaces
            activity_name = form.name.data.strip().title()
            new_activity = Activity(activity_name=activity_name, activity_category=form.category.data.title())
            db.session.add(new_activity)
            db.session.commit()
            flash('Activity added successfully.', 'success')
            return redirect(url_for('manage.activities'))
        activities = Activity.query.all()
        allocated_activities = [a.intervention_type for a in Intervention.query.with_entities(Intervention.intervention_type).distinct()] # Fetch unique intervention types
        settings = get_org_settings()
        return render_template('activities.html', form=form, activities=activities, allocated_activities=allocated_activities, org_name=settings['org_name'])
    else:
        abort(403)


@manage_bp.route('/delete_activity/<string:activity_name>', methods=['POST'])
@login_required
def delete_activity(activity_name):
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        activity = Activity.query.filter_by(activity_name=activity_name).first()
        # make sure activity is not used in any schedules or other dependencies before deleting
        # still need to implement this check
        if activity:
            db.session.delete(activity)
            db.session.commit()
            flash('Activity deleted successfully.', 'success')
        else:
            flash('Activity not found.', 'danger')
        return redirect(url_for('manage.activities'))
    else:
        abort(403)


@manage_bp.route('/delete_designation/<string:designation_name>', methods=['POST'])
@login_required
def delete_designation(designation_name):
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        designation = Designation.query.filter_by(designation=designation_name).first()
        # make sure designation is not allocated to any employee or other dependencies before deleting
        # still need to implement this check
        if designation:
            db.session.delete(designation)
            db.session.commit()
            flash('Designation deleted successfully.', 'success')
        else:
            flash('Designation not found.', 'danger')
        return redirect(url_for('manage.designations'))
    else:
        abort(403)


@manage_bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if not (current_user.is_authenticated and current_user.user_type in ['admin', 'super']):
        abort(403)

    form = SettingsForm()
    settings = AppSettings.get()

    if request.method == 'GET' and settings:
        # populate form with existing values
        form.org_name.data = settings.org_name
        form.org_address.data = settings.org_address
        form.org_phone.data = settings.org_phone
        form.org_email.data = settings.org_email
        form.payment_email.data = settings.payment_email
        form.gmail_client_id.data = settings.gmail_client_id
        form.gmail_client_secret.data = settings.gmail_client_secret
        form.gmail_refresh_token.data = settings.gmail_refresh_token
        form.testing_mode.data = bool(settings.testing_mode)
        form.testing_email.data = settings.testing_email
        form.default_cc.data = settings.default_cc
        form.invoice_reminder_enabled.data = bool(settings.invoice_reminder_enabled)
        form.invoice_reminder_days.data = settings.invoice_reminder_days or 2
        form.invoice_reminder_repeat_enabled.data = bool(settings.invoice_reminder_repeat_enabled)
        form.invoice_reminder_repeat_days.data = settings.invoice_reminder_repeat_days or 2
        form.invoice_reminder_time.data = settings.invoice_reminder_time or '06:00'

    if form.validate_on_submit():
        try:
            if not settings:
                settings = AppSettings()

            settings.org_name = form.org_name.data or None
            settings.org_address = form.org_address.data or None
            settings.org_phone = form.org_phone.data or None
            settings.org_email = form.org_email.data or None
            settings.payment_email = form.payment_email.data or None
            settings.gmail_client_id = form.gmail_client_id.data or None
            if form.gmail_client_secret.data:
                settings.gmail_client_secret = form.gmail_client_secret.data
            if form.gmail_refresh_token.data:
                settings.gmail_refresh_token = form.gmail_refresh_token.data
            settings.testing_mode = bool(form.testing_mode.data)
            settings.testing_email = form.testing_email.data or None
            settings.default_cc = form.default_cc.data or None
            settings.invoice_reminder_enabled = bool(form.invoice_reminder_enabled.data)
            settings.invoice_reminder_days = form.invoice_reminder_days.data or 2
            settings.invoice_reminder_repeat_enabled = bool(form.invoice_reminder_repeat_enabled.data)
            settings.invoice_reminder_repeat_days = form.invoice_reminder_repeat_days.data or 2
            settings.invoice_reminder_time = form.invoice_reminder_time.data or '06:00'

            # handle logo upload
            if form.logo_file.data:
                f = form.logo_file.data
                filename = secure_filename(f.filename)
                images_dir = os.path.join(current_app.root_path, 'static', 'images', 'assets')
                os.makedirs(images_dir, exist_ok=True)
                save_path = os.path.join(images_dir, filename)
                f.save(save_path)
                # save relative path for templates
                settings.logo_path = os.path.join('static', 'images', 'assets', filename)

            db.session.add(settings)
            db.session.commit()
            
            # Update cron schedule if reminder settings changed
            try:
                # Get the project root (parent of the app folder)
                project_root = os.path.dirname(current_app.root_path)
                result = subprocess.run(
                    [sys.executable, os.path.join(project_root, 'setup_cron_schedule.py')],
                    cwd=project_root,
                    check=False,
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    print(f"Cron schedule updated: {result.stdout}")
                else:
                    print(f"Warning: Failed to update cron schedule.")
                    print(f"  stdout: {result.stdout}")
                    print(f"  stderr: {result.stderr}")
            except Exception as e:
                print(f"Warning: Could not update cron schedule: {e}")
            
            flash('Settings saved successfully.', 'success')
            return redirect(url_for('manage.settings'))
        except Exception as e:
            db.session.rollback()
            flash('Error saving settings. Please try again.', 'danger')

    return render_template('settings.html', form=form)


