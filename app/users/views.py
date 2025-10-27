from flask import Blueprint, render_template, redirect, url_for, request, flash, abort
from app import db
from app.models import User, Employee
from app.users.forms import AddUserForm, UpdatePasswordForm
from flask_login import login_required, current_user
from app.utils.utils import manage_user_for_employee
import secrets
import string
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


@users_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_user():
    # Only super and admin can add new accounts
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        form = AddUserForm()
        # Expose both therapist and supervisor roles to be assigned when creating accounts
        form.user_type.choices = [("admin", "Admin"), ("therapist", "Therapist"), ("supervisor", "Supervisor")]
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if not user:
                new_user = User(email=form.email.data,
                                password_hash="",
                                user_type=form.user_type.data,
                                locked_until=None,
                                failed_attempt=0,
                                activation_key=generate_activation_code(8)
                                )
                db.session.add(new_user)
                db.session.commit()
                flash('User account created.', 'success')
                return redirect(url_for('users.list_users'))
            else:
                flash('This email is already registered.', 'warning')
        return render_template('add_user.html', form=form, org_name=org_name)
    else:
        abort(403)


@users_bp.route('/list', methods=['GET','POST'])
@login_required
def list_users():
    # Only admin and super can list/manage users
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        users_pagination = User.query.filter(~((User.user_type == 'super') | (User.email == current_user.email))).paginate(page=page, per_page=per_page, error_out=False)
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
        user = User.query.get_or_404(id)
        db.session.delete(user)
        db.session.commit()
        flash('User account deleted.', 'success')
        return redirect(url_for('users.list_users'))
    else:
        abort(403)
    

@users_bp.route('/lock/<int:id>', methods=['GET', 'POST'])
@login_required
def lock_user(id):
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        user = User.query.get_or_404(id)
        user.locked_until = datetime.now() + relativedelta(years=1000)
        user.failed_attempt = -5
        db.session.commit()
        flash("User account locked.", "success")
        return redirect(url_for('users.list_users'))
    else:
        abort(403)


@users_bp.route('/unlock/<int:id>', methods=['GET', 'POST'])
@login_required
def unlock_user(id):
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        user = User.query.get_or_404(id)
        user.locked_until = None
        user.failed_attempt = 1
        db.session.commit()
        flash("User account unlocked.","success")
        return redirect(url_for('users.list_users'))
    else:
        abort(403)
    

@users_bp.route('/promote/<int:id>', methods=['GET','POST'])
@login_required
def promote_user(id):
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        user = User.query.get_or_404(id)
        user.user_type = "admin"
        db.session.commit()
        flash("User account promoted to Admin.", "success")
        return redirect(url_for('users.list_users'))
    else:
        abort(403)


@users_bp.route('/demote/<int:id>', methods=['GET','POST'])
@login_required
def demote_user(id):
    if current_user.is_authenticated and current_user.user_type in ['admin', 'super']:
        user = User.query.get_or_404(id)
        # Find associated employee to determine role
        employee = Employee.query.filter_by(email=user.email).first()
        
        if employee:
            # Temporarily store the admin status
            was_admin = user.user_type == 'admin'
            # Use utility function to set role based on position
            manage_user_for_employee(employee.email, employee.position, user)
            if was_admin:
                flash(f"User account demoted from Admin to {user.user_type.capitalize()}.", 'success')
        else:
            # If no employee record found, default to therapist role
            user.user_type = "therapist"
            flash("User account demoted to Therapist (no employee record found).", 'warning')
        
        db.session.commit()
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
                return redirect(url_for('logout'))
            else:
                flash('Current password is incorrect.', 'danger')
        return render_template('change_password.html', form=form, org_name=org_name)
    else:
        abort(403)