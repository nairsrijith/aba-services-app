from flask import Blueprint, render_template, redirect, url_for, abort, request
from app import db
from app.models import Client
from app.clients.forms import AddClientForm, UpdateClientForm
from flask_login import login_required, current_user

clients_bp = Blueprint('clients', __name__, template_folder='templates')


@clients_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_client():
    if current_user.is_authenticated and current_user.user_type == "admin":
        form = AddClientForm()
        form.state.choices = [("AB", "Alberta"), ("BC", "British Columbia"), ("MB", "Manitoba"),
                            ("NB", "New Brunswick"), ("NL", "Newfoundland and Labrador"),
                            ("NS", "Nova Scotia"), ("ON", "Ontario"), ("PE", "Prince Edward Island"),
                            ("QC", "Quebec"), ("SK", "Saskatchewan"), ("NT", "Northwest Territories"),
                            ("NU", "Nunavut"), ("YT", "Yukon")]
        form.gender.choices = [("Male", "Male"), ("Female", "Female"), ("Unspecified", "Unspecified")]
        if form.validate_on_submit():
            new_client = Client(firstname=form.firstname.data.title(),
                                lastname=form.lastname.data.title(),
                                dob=form.dob.data,
                                gender=form.gender.data.title(),
                                parentname=form.parentname.data.title(),
                                parentemail=form.parentemail.data,
                                parentcell=form.parentcell.data,
                                address1=form.address1.data.title(),
                                address2=form.address2.data.title(),
                                city=form.city.data.title(),
                                state=form.state.data,
                                zipcode=form.zipcode.data.upper(),
                                cost_supervision=form.cost_supervision.data or 0.0,
                                cost_therapy=form.cost_therapy.data or 0.0)
            db.session.add(new_client)
            db.session.commit()
            return redirect(url_for('clients.list_clients'))
        return render_template('add.html', form=form)
    else:
        abort(403)


@clients_bp.route('/list', methods=['GET', 'POST'])
@login_required
def list_clients():
    if current_user.is_authenticated and current_user.user_type == "admin":
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)  # default to 10
        clients_pagination = Client.query.paginate(page=page, per_page=per_page, error_out=False)    
        return render_template(
            'list.html',
            clients=clients_pagination.items,
            pagination=clients_pagination,
            per_page=per_page
        )
    else:
        abort(403)


@clients_bp.route('/delete/<int:client_id>', methods=['GET', 'POST'])
@login_required
def delete_client(client_id):
    if current_user.is_authenticated and current_user.user_type == "admin":
        client = Client.query.get_or_404(client_id)
        db.session.delete(client)
        db.session.commit()
        return redirect(url_for('clients.list_clients'))
    else:
        abort(403)


@clients_bp.route('/update/<int:client_id>', methods=['GET', 'POST'])
@login_required
def update_client(client_id):
    if current_user.is_authenticated and current_user.user_type == "admin":
        client = Client.query.get_or_404(client_id)
        form = UpdateClientForm(obj=client)
        form.state.choices = [("AB", "Alberta"), ("BC", "British Columbia"), ("MB", "Manitoba"),
                            ("NB", "New Brunswick"), ("NL", "Newfoundland and Labrador"),
                            ("NS", "Nova Scotia"), ("ON", "Ontario"), ("PE", "Prince Edward Island"),
                            ("QC", "Quebec"), ("SK", "Saskatchewan"), ("NT", "Northwest Territories"),
                            ("NU", "Nunavut"), ("YT", "Yukon")]
        form.gender.choices = [("Male", "Male"), ("Female", "Female"), ("Unspecified", "Unspecified")]
        if request.method == 'POST':
            client.firstname = form.firstname.data.title()
            client.lastname = form.lastname.data.title()
            client.dob = form.dob.data
            client.gender = form.gender.data.title()
            client.parentname = form.parentname.data.title()
            client.parentemail = form.parentemail.data
            client.parentcell = form.parentcell.data
            client.address1 = form.address1.data.title()
            client.address2 = form.address2.data.title()
            client.city = form.city.data
            client.state = form.state.data.title()
            client.zipcode = form.zipcode.data.upper()
            client.cost_supervision = form.cost_supervision.data or 0
            client.cost_therapy = form.cost_therapy.data or 0
            db.session.commit()
            return redirect(url_for('clients.list_clients'))
        return render_template('update.html', form=form, client=client)
    else:
        abort(403)

