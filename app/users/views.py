from flask import Blueprint, render_template, redirect, url_for, request, flash
from app import db
from app.models import User
from app.users.forms import AddUserForm
from flask_login import login_required, current_user
import secrets
import string

users_bp = Blueprint('users', __name__, template_folder='templates')


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
    if current_user.is_authenticated and not current_user.user_type == "user":
        form = AddUserForm()
        form.user_type.choices = [("admin", "Admin"), ("user", "User")]
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if not user:
                new_user = User(email=form.email.data,
                                password_hash="",
                                user_type=form.user_type.data,
                                locked=1,
                                failed_attempt=0,
                                activation_key=form.activation_key.data
                                )
                db.session.add(new_user)
                db.session.commit()
                return redirect(url_for('users.list_users'))
            else:
                flash('This email is already registered. Try logging in or contact Administrator', 'warning')
        return render_template('add_user.html', form=form)
    else:
        return redirect(url_for('index'))


@users_bp.route('/list', methods=['GET','POST'])
@login_required
def list_users():
    if current_user.is_authenticated and not current_user.user_type == "user":
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        users_pagination = User.query.filter(~((User.user_type == 'super') | (User.email == current_user.email))).paginate(page=page, per_page=per_page, error_out=False)
        return render_template(
            'list_user.html',
            users=users_pagination.items,
            pagination=users_pagination,
            per_page=per_page
        )
    else:
        return redirect(url_for('index'))
    

@users_bp.route('/delete/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_user(id):
    if current_user.is_authenticated and not current_user.user_type == "user":
        user = User.query.get_or_404(id)
        db.session.delete(user)
        db.session.commit()
        return redirect(url_for('users.list_users'))
    else:
        return redirect(url_for('index'))
    

@users_bp.route('/lock/<int:id>', methods=['GET', 'POST'])
@login_required
def lock_user(id):
    if current_user.is_authenticated and not current_user.user_type == "user":
        user = User.query.get_or_404(id)
        user.locked = True
        user.failed_attempt = 0
        db.session.commit()
        return redirect(url_for('users.list_users'))
    else:
        return redirect(url_for('index'))


@users_bp.route('/unlock/<int:id>', methods=['GET', 'POST'])
@login_required
def unlock_user(id):
    if current_user.is_authenticated and not current_user.user_type == "user":
        user = User.query.get_or_404(id)
        user.locked = False
        user.failed_attempt = 3
        db.session.commit()
        return redirect(url_for('users.list_users'))
    else:
        return redirect(url_for('index'))
    

@users_bp.route('/deactivate/<int:id>', methods=['GET', 'POST'])
@login_required
def deactivate_user(id):
    if current_user.is_authenticated and not current_user.user_type == "user":
        user = User.query.get_or_404(id)
        user.locked = True
        user.failed_attempt = 0
        user.password_hash = ""
        db.session.commit()
        return redirect(url_for('users.list_users'))
    else:
        return redirect(url_for('index'))


@users_bp.route('/activate/<int:id>', methods=['GET', 'POST'])
@login_required
def activate_user(id):
    if current_user.is_authenticated and not current_user.user_type == "user":
        user = User.query.get_or_404(id)
        user.locked = False
        user.failed_attempt = 3
        user.activation_key = generate_activation_code(length=12)
        db.session.commit()
        return redirect(url_for('users.list_users'))
    else:
        return redirect(url_for('index'))


