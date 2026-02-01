from flask import Blueprint, render_template, redirect, url_for, request, flash, abort, current_app
from app import db
from flask_login import login_required, current_user
from app.models import Employee
from app.users.forms import UpdatePasswordForm
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os, string, secrets
from app.utils.email_utils import queue_email
from app.utils.settings_utils import get_org_settings
from werkzeug.utils import secure_filename
import time

users_bp = Blueprint('users', __name__, template_folder='templates')





@users_bp.route('/list', methods=['GET','POST'])
@login_required
def list_users():
    # Only admin and super can list/manage users
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        users_pagination = Employee.query.filter(
            ~((Employee.user_type == 'super') | (Employee.email == current_user.email) | (Employee.failed_attempt <= -5 ))
        ).paginate(page=page, per_page=per_page, error_out=False)
        settings = get_org_settings()
        return render_template(
            'list_user.html',
            users=users_pagination.items,
            pagination=users_pagination,
            per_page=per_page,
            org_name=settings['org_name']
        )
    else:
        abort(403)
    

@users_bp.route('/lock/<int:id>', methods=['GET', 'POST'])
@login_required
def lock_user(id):
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        employee = Employee.query.get_or_404(id)
        employee.locked_until = datetime.now() + relativedelta(years=1000)
        employee.failed_attempt = -2
        db.session.commit()
        flash("User account locked.", "success")
        return redirect(url_for('users.list_users'))
    else:
        abort(403)


@users_bp.route('/unlock/<int:id>', methods=['GET', 'POST'])
@login_required
def unlock_user(id):
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        employee = Employee.query.get_or_404(id)
        employee.locked_until = None
        employee.failed_attempt = 0
        db.session.commit()
        flash("User account unlocked.","success")
        return redirect(url_for('users.list_users'))
    else:
        abort(403)


@users_bp.route('/promote/<int:id>', methods=['GET','POST'])
@login_required
def promote_user(id):
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        employee = Employee.query.get_or_404(id)
        # Keep track of the previous role
        previous_role = employee.user_type
        employee.user_type = "admin"
        if previous_role != employee.user_type:
            db.session.commit()
            flash(f"User account promoted from {previous_role.capitalize()} to Admin.", "success")
        else:
            flash(f"User's role is already Admin.", "info")
        return redirect(url_for('users.list_users'))
    else:
        abort(403)


@users_bp.route('/demote/<int:id>', methods=['GET','POST'])
@login_required
def demote_user(id):
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        employee = Employee.query.get_or_404(id)
        
        # Store previous role and position
        previous_role = employee.user_type
        
        # Determine new role based on position
        if employee.position == 'Administrator':
            employee.user_type = 'admin'
        elif employee.position == 'Behaviour Analyst':
            employee.user_type = 'supervisor'
        else:
            employee.user_type = 'therapist'
            
        # Only commit and show message if role actually changed
        if previous_role != employee.user_type:
            db.session.commit()
            flash(f"User account demoted from {previous_role.capitalize()} to {employee.user_type.capitalize()}.", 'success')
        else:
            flash(f"User's role already matches their position ({employee.user_type.capitalize()}).", 'info')
            
        return redirect(url_for('users.list_users'))
    else:
        abort(403)


@users_bp.route('/send_activation/<int:id>', methods=['POST'])
@login_required
def send_activation_email(id):
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        employee = Employee.query.get_or_404(id)
        
        # Generate activation email content
        subject = f"Account Activation - {get_org_settings()['org_name']}"
        body_html = render_template('email/activation_email.html', 
                                  firstname=employee.firstname,
                                  activation_key=employee.activation_key)
        body_text = render_template('email/activation_email.txt',
                                  firstname=employee.firstname,
                                  activation_key=employee.activation_key)
        
        # Send email
        success = queue_email(
            subject=subject,
            recipients=[employee.email],
            body_text=body_text,
            body_html=body_html
        )
        
        if success:
            flash(f"Activation email sent to {employee.email}.", "success")
        else:
            flash(f"Failed to send activation email to {employee.email}.", "danger")
            
        return redirect(url_for('users.list_users'))
    else:
        abort(403)


@users_bp.route('/update_profile', methods=['GET', 'POST'])
@login_required
def update_profile():
    if current_user.is_authenticated:
        form = UpdatePasswordForm()
        if form.validate_on_submit():
            action = request.form.get('action')
            # Update profile picture only
            if action == 'update_picture':
                file_field = form.profile_pic.data
                if file_field and getattr(file_field, 'filename', None):
                    try:
                        orig_name = secure_filename(file_field.filename)
                        if orig_name:
                            # remember previous pic so we can remove it after successful save
                            prev_pic = current_user.profile_pic
                            ext = orig_name.rsplit('.', 1)[-1].lower()
                            filename = f"user_{current_user.id}_{int(time.time())}.{ext}"
                            folder = current_app.config.get('PROFILE_PIC_FOLDER')
                            os.makedirs(folder, exist_ok=True)
                            dest = os.path.join(folder, filename)
                            file_field.save(dest)
                            rel_path = os.path.join('data', 'profile_pic', filename).replace('\\', '/')
                            current_user.profile_pic = rel_path
                            db.session.commit()
                            # remove previous file if it exists and is different
                            try:
                                if prev_pic:
                                    prev_basename = prev_pic.split('/')[-1]
                                    if prev_basename and prev_basename != filename:
                                        prev_path = os.path.join(folder, prev_basename)
                                        if os.path.exists(prev_path):
                                            os.remove(prev_path)
                            except Exception:
                                pass
                            flash('Profile picture updated.', 'success')
                            return redirect(url_for('users.update_profile'))
                    except Exception:
                        flash('Could not save profile picture; please try again.', 'warning')
                else:
                    flash('No file selected to upload.', 'warning')

            # Update password only
            elif action == 'update_password':
                # require current + new + confirm
                if not form.current_password.data or not form.new_password.data or not form.confirm_password.data:
                    flash('Please provide current and new password (and confirmation).', 'danger')
                elif form.new_password.data != form.confirm_password.data:
                    flash('New passwords do not match.', 'danger')
                else:
                    if current_user.check_password(form.current_password.data):
                        current_user.set_password(form.new_password.data)
                        db.session.commit()
                        flash('Your password has been updated.', 'success')
                        return redirect(url_for('logout'))
                    else:
                        flash('Current password is incorrect.', 'danger')

            # Fallback: if no explicit action, treat as original (password change)
            else:
                if current_user.check_password(form.current_password.data):
                    current_user.set_password(form.new_password.data)
                    file_field = form.profile_pic.data
                    if file_field and getattr(file_field, 'filename', None):
                        try:
                            orig_name = secure_filename(file_field.filename)
                            if orig_name:
                                prev_pic = current_user.profile_pic
                                ext = orig_name.rsplit('.', 1)[-1].lower()
                                filename = f"user_{current_user.id}_{int(time.time())}.{ext}"
                                folder = current_app.config.get('PROFILE_PIC_FOLDER')
                                os.makedirs(folder, exist_ok=True)
                                dest = os.path.join(folder, filename)
                                file_field.save(dest)
                                rel_path = os.path.join('data', 'profile_pic', filename).replace('\\', '/')
                                current_user.profile_pic = rel_path
                                # remove previous file if different
                                try:
                                    if prev_pic:
                                        prev_basename = prev_pic.split('/')[-1]
                                        if prev_basename and prev_basename != filename:
                                            prev_path = os.path.join(folder, prev_basename)
                                            if os.path.exists(prev_path):
                                                os.remove(prev_path)
                                except Exception:
                                    pass
                        except Exception:
                            flash('Could not save profile picture; please try again.', 'warning')
                    db.session.commit()
                    flash('Your password has been updated.', 'success')
                    return redirect(url_for('logout'))
                else:
                    flash('Current password is incorrect.', 'danger')
        settings = get_org_settings()
        # render new centered template with profile-pic upload
        return render_template('update_profile.html', form=form, org_name=settings['org_name'])
    else:
        abort(403)