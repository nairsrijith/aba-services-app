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
            return redirect(url_for('users.add_user'))
        return render_template('add_user.html', form=form)
    else:
        return redirect(url_for('index'))
