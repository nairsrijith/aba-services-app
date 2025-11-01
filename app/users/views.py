from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from app import db
from flask_login import login_required, current_user
from app.models import Employee
from app.users.forms import SetRoleForm, UpdatePasswordForm
from datetime import datetime
from dateutil.relativedelta import relativedelta
import os

users_bp = Blueprint('users', __name__, template_folder='templates')


org_name = os.environ.get('ORG_NAME', 'My Organization')

def generate_activation_code(length=8):
    """
    Generates a random alphanumeric activation code of a specified length.
    """
    characters = string.ascii_letters + string.digits
    code = ''.join(secrets.choice(characters) for _ in range(length))
    return code
# Example usage:
# activation_code = generate_activation_code(length=8)


@users_bp.route('/set_role/<int:id>', methods=['GET', 'POST'])
@login_required
def set_role(id):
    # Only super and admin can modify roles
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        employee = Employee.query.get_or_404(id)
        form = SetRoleForm()
        form.user_type.choices = [("admin", "Admin"), ("therapist", "Therapist"), ("supervisor", "Supervisor")]
        if form.validate_on_submit():
            employee.user_type = form.user_type.data
            db.session.commit()
            flash('User role updated.', 'success')
            return redirect(url_for('users.list_users'))
        return render_template('set_role.html', form=form, employee=employee, org_name=org_name)
    else:
        abort(403)


@users_bp.route('/list', methods=['GET','POST'])
@login_required
def list_users():
    # Only admin and super can list/manage users
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        users_pagination = Employee.query.filter(
            ~((Employee.user_type == 'super') | (Employee.email == current_user.email))
        ).paginate(page=page, per_page=per_page, error_out=False)
        return render_template(
            'list_user.html',
            users=users_pagination.items,
            pagination=users_pagination,
            per_page=per_page,
            org_name=org_name
        )
    else:
        abort(403)
    

@users_bp.route('/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_user(id):
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        employee = Employee.query.get_or_404(id)
        
        # Cannot delete super users
        if employee.user_type == 'super':
            flash('Cannot delete super user accounts.', 'danger')
            return redirect(url_for('users.list_users'))
        
        # Set user as inactive instead of deleting
        employee.is_active = False
        db.session.commit()
        flash('User account deactivated.', 'success')
        return redirect(url_for('users.list_users'))
    else:
        abort(403)
    

@users_bp.route('/lock/<int:id>', methods=['GET', 'POST'])
@login_required
def lock_user(id):
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        employee = Employee.query.get_or_404(id)
        employee.locked_until = datetime.now() + relativedelta(years=1000)
        employee.failed_attempt = -5
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
        db.session.commit()
        flash(f"User account promoted from {previous_role.capitalize()} to Admin.", "success")
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
        if employee.position == 'Supervisor':
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


@users_bp.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if current_user.is_authenticated:
        form = UpdatePasswordForm()
        if form.validate_on_submit():
            if current_user.check_password(form.current_password.data):
                current_user.set_password(form.new_password.data)
                db.session.commit()
                flash('Your password has been updated.', 'success')
                return redirect(url_for('auth.logout'))
            else:
                flash('Current password is incorrect.', 'danger')
        return render_template('change_password.html', form=form, org_name=org_name)
    else:
        abort(403)