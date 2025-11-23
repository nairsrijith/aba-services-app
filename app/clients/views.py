from flask import Blueprint, render_template, redirect, url_for, abort, flash, request
from app import db
from app.models import Client, Employee, Intervention, Invoice, PayRate, PayStubItem
from app.clients.forms import AddClientForm, UpdateClientForm
from flask_login import login_required, current_user
from app.utils.settings_utils import get_org_settings
import os
import re

clients_bp = Blueprint('clients', __name__, template_folder='templates')



@clients_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_client():
    if current_user.is_authenticated and current_user.user_type in ["admin", "super"]:
        
        supervisor = Employee.query.filter_by(position='Behaviour Analyst', is_active=True).first()
        if not supervisor:
            flash('Warning: No active Behaviour Analyst available to add a client record.', 'warning')
            return redirect(url_for('employees.list_employees'))

        form = AddClientForm()
        form.state.choices = [("AB", "Alberta"), ("BC", "British Columbia"), ("MB", "Manitoba"),
                            ("NB", "New Brunswick"), ("NL", "Newfoundland and Labrador"),
                            ("NS", "Nova Scotia"), ("ON", "Ontario"), ("PE", "Prince Edward Island"),
                            ("QC", "Quebec"), ("SK", "Saskatchewan"), ("NT", "Northwest Territories"),
                            ("NU", "Nunavut"), ("YT", "Yukon")]
        form.gender.choices = [("Male", "Male"), ("Female", "Female"), ("Unspecified", "Unspecified")]
        form.supervisor_id.choices = [(e.id, f"{e.firstname} {e.lastname}") for e in Employee.query.filter_by(position='Behaviour Analyst', is_active=True).all()]
        if form.validate_on_submit():
            # Normalize parent phone number to digits-only before storing
            normalized_parentcell = re.sub(r'\D', '', (form.parentcell.data or ''))

            new_client = Client(firstname=form.firstname.data.title(),
                                lastname=form.lastname.data.title(),
                                dob=form.dob.data,
                                gender=form.gender.data.title(),
                                parentname=form.parentname.data.title(),
                                parentemail=form.parentemail.data,
                                parentemail2=form.parentemail2.data,
                                parentcell=normalized_parentcell,
                                address1=form.address1.data.title(),
                                address2=form.address2.data.title(),
                                city=form.city.data.title(),
                                state=form.state.data,
                                zipcode=form.zipcode.data.upper(),
                                supervisor_id=form.supervisor_id.data,
                                cost_supervision=form.cost_supervision.data or 0.0,
                                cost_therapy=form.cost_therapy.data or 0.0)
            db.session.add(new_client)
            db.session.commit()
            return redirect(url_for('clients.list_clients'))
        settings = get_org_settings()
        return render_template('add.html', form=form, org_name=settings['org_name'])
    else:
        abort(403)


@clients_bp.route('/deactivate/<int:client_id>', methods=['POST'])
@login_required
def deactivate_client(client_id):
    if current_user.is_authenticated and current_user.user_type in ["admin", "super"]:
        client = Client.query.get_or_404(client_id)
        # Check for open/pending invoices before deactivating
        open_invoices = Invoice.query.filter_by(client_id=client.id).filter(Invoice.status != 'Paid').all()
        if open_invoices:
            flash('Cannot deactivate client with unpaid invoices. Please resolve all invoices first.', 'danger')
            return redirect(url_for('clients.list_clients'))
            
        client.is_active = False
        db.session.commit()
        flash('Client has been deactivated.', 'success')
        return redirect(url_for('clients.list_clients'))
    else:
        abort(403)


@clients_bp.route('/reactivate/<int:client_id>', methods=['POST'])
@login_required
def reactivate_client(client_id):
    if current_user.is_authenticated and current_user.user_type in ["admin", "super"]:
        client = Client.query.get_or_404(client_id)
        # Check if supervisor is still active before reactivating
        if client.supervisor_id and not client.supervisor.is_active:
            flash('Cannot reactivate client as their supervisor is inactive. Please assign an active supervisor first.', 'warning')
            return redirect(url_for('clients.update_client', client_id=client.id))
            
        client.is_active = True
        db.session.commit()
        flash('Client has been reactivated.', 'success')
        return redirect(url_for('clients.list_clients'))
    else:
        abort(403)


@clients_bp.route('/list', methods=['GET', 'POST'])
@login_required
def list_clients():
    if current_user.is_authenticated and current_user.user_type in ["admin", "super"]:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)  # default to 10
        # Search query (client name or parent name/email)
        q = request.args.get('q', '').strip()
        # Respect the `show_inactive` toggle: when not set, only show active clients.
        show_inactive = request.args.get('show_inactive', '0')
        # Build base query depending on show_inactive
        if show_inactive == '1':
            # include both active and inactive, active first
            query = Client.query
        else:
            # only active clients
            query = Client.query.filter_by(is_active=True)

        # Apply search filter if present
        if q:
            like_q = f"%{q}%"
            query = query.filter(
                db.or_(
                    Client.firstname.ilike(like_q),
                    Client.lastname.ilike(like_q),
                    Client.parentname.ilike(like_q),
                    Client.parentemail.ilike(like_q),
                    Client.parentemail2.ilike(like_q),
                    Client.city.ilike(like_q)
                )
            )

        # Always order results for consistent pagination
        query = query.order_by(Client.is_active.desc(), Client.firstname, Client.lastname)
        clients_pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        settings = get_org_settings()
        return render_template(
            'list.html',
            clients=clients_pagination.items,
            pagination=clients_pagination,
            per_page=per_page,
            org_name=settings['org_name']
        )
    else:
        abort(403)


@clients_bp.route('/delete/<int:client_id>', methods=['GET', 'POST'])
@login_required
def delete_client(client_id):
    if current_user.is_authenticated and current_user.user_type in ["admin", "super"]:
        client = Client.query.get_or_404(client_id)
        
        # Check for interventions
        interventions = Intervention.query.filter_by(client_id=client.id).all()
        if interventions:
            flash('Cannot delete client with associated interventions. Please delete interventions first.', 'danger')
            return redirect(url_for('clients.list_clients'))
        
        # Check for invoices
        invoices = Invoice.query.filter_by(client_id=client.id).all()
        if invoices:
            flash('Cannot delete client with associated invoices. Please delete invoices first.', 'danger')
            return redirect(url_for('clients.list_clients'))
            
        # Check for pay rates
        pay_rates = PayRate.query.filter_by(client_id=client.id).all()
        if pay_rates:
            flash('Cannot delete client with associated pay rates. Please delete pay rates first.', 'danger')
            return redirect(url_for('clients.list_clients'))
            
        # Check for pay stub items
        pay_stub_items = PayStubItem.query.filter_by(client_id=client.id).all()
        if pay_stub_items:
            flash('Cannot delete client with associated pay stubs. Please delete pay stubs first.', 'danger')
            return redirect(url_for('clients.list_clients'))

        # If no dependencies found, proceed with deletion
        try:
            db.session.delete(client)
            db.session.commit()
            flash("Client deleted successfully.", "success")
        except Exception as e:
            db.session.rollback()
            flash('Error deleting client. Please try again.', 'danger')
            
        return redirect(url_for('clients.list_clients'))
    else:
        abort(403)


@clients_bp.route('/update/<int:client_id>', methods=['GET', 'POST'])
@login_required
def update_client(client_id):
    if current_user.is_authenticated and current_user.user_type in ["admin", "super"]:
        client = Client.query.get_or_404(client_id)
        form = UpdateClientForm(obj=client)
        form.state.choices = [("AB", "Alberta"), ("BC", "British Columbia"), ("MB", "Manitoba"),
                            ("NB", "New Brunswick"), ("NL", "Newfoundland and Labrador"),
                            ("NS", "Nova Scotia"), ("ON", "Ontario"), ("PE", "Prince Edward Island"),
                            ("QC", "Quebec"), ("SK", "Saskatchewan"), ("NT", "Northwest Territories"),
                            ("NU", "Nunavut"), ("YT", "Yukon")]
        form.gender.choices = [("Male", "Male"), ("Female", "Female"), ("Unspecified", "Unspecified")]
        
        # Include the current supervisor in choices even if inactive
        supervisor_choices = [(e.id, f"{e.firstname} {e.lastname}") 
                         for e in Employee.query.filter_by(position='Behaviour Analyst', is_active=True).all()]
        if client.supervisor_id:
            supervisor_choices.extend([(e.id, f"{e.firstname} {e.lastname} (Inactive)") 
                                 for e in Employee.query.filter_by(id=client.supervisor_id, is_active=False).all()])
        form.supervisor_id.choices = supervisor_choices
        
        if request.method == 'POST':
            client.firstname = form.firstname.data.title()
            client.lastname = form.lastname.data.title()
            client.dob = form.dob.data
            client.gender = form.gender.data.title()
            client.parentname = form.parentname.data.title()
            client.parentemail = form.parentemail.data
            client.parentemail2 = form.parentemail2.data
            client.parentcell = re.sub(r'\D', '', (form.parentcell.data or ''))
            client.address1 = form.address1.data.title()
            client.address2 = form.address2.data.title()
            client.city = form.city.data
            client.state = form.state.data
            client.zipcode = form.zipcode.data.upper()
            client.supervisor_id = form.supervisor_id.data
            client.cost_supervision = form.cost_supervision.data or 0
            client.cost_therapy = form.cost_therapy.data or 0
            db.session.commit()
            return redirect(url_for('clients.list_clients'))
        settings = get_org_settings()
        return render_template('update.html', form=form, client=client, org_name=settings['org_name'])
    else:
        abort(403)

