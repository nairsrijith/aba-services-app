from flask import Blueprint, render_template, redirect, url_for, request
from app import db
from app.models import User
from app.users.forms import AddUserForm
from flask_login import login_required, current_user


users_bp = Blueprint('users', __name__, template_folder='templates')


@users_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_user():
    if current_user.is_authenticated and not current_user.user_type == "user":
        form = AddUserForm()
        form.user_type.choices = [("admin", "Admin"), ("user", "User")]
        if form.validate_on_submit():
            new_user = User(email=form.email.data,
                            password_hash="",
                            user_type=form.user_type.data,
                            locked=0,
                            activation_key=form.activation_key.data
                            )
            db.session.add(new_user)
            db.session.commit()
            return redirect(url_for('users.list_users'))
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