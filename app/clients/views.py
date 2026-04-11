from flask import Blueprint, render_template, redirect, url_for, abort, flash, request
from app import db
from app.models import Client, Employee, Intervention, Invoice, PayRate, PayStubItem
from app.clients.forms import AddClientForm, UpdateClientForm
from flask_login import login_required, current_user
from app.utils.settings_utils import get_org_settings
from datetime import date, datetime
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
            # Normalize phone numbers to digits-only before storing
            normalized_parent_cell = re.sub(r'\D', '', (form.parent_cell.data or ''))
            normalized_parent2_cell = re.sub(r'\D', '', (form.parent2_cell.data or '')) if form.parent2_cell.data else ''

            # Create legacy parentname for backward compatibility
            legacy_parentname = f"{form.parent_firstname.data.title()} {form.parent_lastname.data.title()}".strip()

            new_client = Client(
                firstname=form.firstname.data.title(),
                lastname=form.lastname.data.title(),
                dob=form.dob.data,
                gender=form.gender.data.title(),
                parent_firstname=form.parent_firstname.data.title(),
                parent_lastname=form.parent_lastname.data.title() if form.parent_lastname.data else '',
                parent_email=form.parent_email.data,
                parent_cell=normalized_parent_cell,
                parent2_firstname=form.parent2_firstname.data.title() if form.parent2_firstname.data else None,
                parent2_lastname=form.parent2_lastname.data.title() if form.parent2_lastname.data else None,
                parent2_email=form.parent2_email.data if form.parent2_email.data else None,
                parent2_cell=normalized_parent2_cell if normalized_parent2_cell else None,
                address1=form.address1.data.title(),
                address2=form.address2.data.title() if form.address2.data else '',
                city=form.city.data.title(),
                state=form.state.data,
                zipcode=form.zipcode.data.upper(),
                supervisor_id=form.supervisor_id.data,
                cost_supervision=form.cost_supervision.data or 0.0,
                cost_therapy=form.cost_therapy.data or 0.0,
                # Legacy fields for backward compatibility
                parentname=legacy_parentname,
                parentemail=form.parent_email.data,
                parentemail2=form.parent2_email.data if form.parent2_email.data else None,
                parentcell=normalized_parent_cell
            )
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
        # Get selected client ID if provided
        selected_client_id = request.args.get('client_id', None, type=int)
        
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
        
        # Fetch selected client info if available
        selected_client_data = None
        if selected_client_id:
            client = Client.query.get(selected_client_id)
            if client:
                from datetime import date
                
                all_sessions = Intervention.query.filter_by(client_id=client.id).order_by(Intervention.date.desc()).all()
                total_sessions = len(all_sessions)
                total_session_hours = round(sum([s.duration or 0 for s in all_sessions]), 2)

                today = date.today()
                year_start = date(today.year, 1, 1)
                month_start = date(today.year, today.month, 1)

                sessions_year = [s for s in all_sessions if s.date and s.date >= year_start]
                sessions_month = [s for s in all_sessions if s.date and s.date >= month_start]

                def session_stats(session_list):
                    count = len(session_list)
                    hours = round(sum([s.duration or 0 for s in session_list]), 2)
                    return count, hours

                sessions_overall_count, sessions_overall_hours = session_stats(all_sessions)
                sessions_year_count, sessions_year_hours = session_stats(sessions_year)
                sessions_month_count, sessions_month_hours = session_stats(sessions_month)

                upcoming_sessions = Intervention.query.filter(
                    Intervention.client_id == client.id,
                    Intervention.date >= date.today()
                ).order_by(Intervention.date.asc(), Intervention.start_time.asc()).limit(5).all()

                next_session = upcoming_sessions[0] if upcoming_sessions else None

                # Upcoming birthday event
                birth_date = client.dob
                if birth_date:
                    this_year_birthday = None
                    try:
                        this_year_birthday = date(date.today().year, birth_date.month, birth_date.day)
                    except ValueError:
                        # Handle Feb 29 birthdays non-leap-year by assigning Feb 28
                        this_year_birthday = date(date.today().year, 2, 28)

                    if birth_date.month == date.today().month and this_year_birthday >= date.today():
                        next_birthday = this_year_birthday
                    else:
                        next_birthday = None
                else:
                    next_birthday = None

                upcoming_events = []
                if next_birthday:
                    upcoming_events.append({
                        'type': 'Birthday',
                        'date': next_birthday,
                        'description': ""
                    })
                if next_session:
                    upcoming_events.append({
                        'type': 'Next Session',
                        'date': next_session.date,
                        'description': f"{next_session.intervention_type} with {next_session.employee.firstname} {next_session.employee.lastname}"
                    })

                invoices = Invoice.query.filter_by(client_id=client.id).all()

                def compute_stats(invoice_list):
                    invoiced = round(sum([inv.total_cost or 0.0 for inv in invoice_list]), 2)
                    paid = round(sum([inv.total_cost or 0.0 for inv in invoice_list if inv.status and inv.status.lower() == 'paid']), 2)
                    pending = round(max(invoiced - paid, 0.0), 2)
                    return invoiced, paid, pending

                today = date.today()
                year_start = date(today.year, 1, 1)
                month_start = date(today.year, today.month, 1)

                invoices_month = [inv for inv in invoices if inv.invoiced_date and inv.invoiced_date >= month_start]
                invoices_year = [inv for inv in invoices if inv.invoiced_date and inv.invoiced_date >= year_start]

                invoiced_overall, paid_overall, pending_overall = compute_stats(invoices)
                invoiced_year, paid_year, pending_year = compute_stats(invoices_year)
                invoiced_month, paid_month, pending_month = compute_stats(invoices_month)

                selected_client_data = {
                    'client': client,
                    'total_sessions': total_sessions,
                    'total_session_hours': total_session_hours,
                    'all_sessions': all_sessions,
                    'upcoming_sessions': upcoming_sessions,
                    'upcoming_events': upcoming_events,
                    'invoices': invoices,
                    'invoice_stats': {
                        'overall': {'invoiced': invoiced_overall, 'paid': paid_overall, 'pending': pending_overall},
                        'year': {'invoiced': invoiced_year, 'paid': paid_year, 'pending': pending_year},
                        'month': {'invoiced': invoiced_month, 'paid': paid_month, 'pending': pending_month}
                    },
                    'session_stats': {
                        'overall': {'sessions': sessions_overall_count, 'hours': sessions_overall_hours},
                        'year': {'sessions': sessions_year_count, 'hours': sessions_year_hours},
                        'month': {'sessions': sessions_month_count, 'hours': sessions_month_hours}
                    }
                }
        
        return render_template(
            'client_list_info.html',
            clients=clients_pagination.items,
            pagination=clients_pagination,
            per_page=per_page,
            selected_client_id=selected_client_id,
            selected_client_data=selected_client_data,
            org_name=settings['org_name']
        )
    else:
        abort(403)


@clients_bp.route('/info/<int:client_id>', methods=['GET'])
@login_required
def client_info(client_id):
    if current_user.is_authenticated and current_user.user_type in ["admin", "super"]:
        client = Client.query.get_or_404(client_id)

        all_sessions = Intervention.query.filter_by(client_id=client.id).order_by(Intervention.date.desc()).all()
        total_sessions = len(all_sessions)
        total_session_hours = round(sum([s.duration or 0 for s in all_sessions]), 2)

        today = date.today()
        year_start = date(today.year, 1, 1)
        month_start = date(today.year, today.month, 1)

        sessions_year = [s for s in all_sessions if s.date and s.date >= year_start]
        sessions_month = [s for s in all_sessions if s.date and s.date >= month_start]

        def session_stats(session_list):
            count = len(session_list)
            hours = round(sum([s.duration or 0 for s in session_list]), 2)
            return count, hours

        sessions_overall_count, sessions_overall_hours = session_stats(all_sessions)
        sessions_year_count, sessions_year_hours = session_stats(sessions_year)
        sessions_month_count, sessions_month_hours = session_stats(sessions_month)

        upcoming_sessions = Intervention.query.filter(
            Intervention.client_id == client.id,
            Intervention.date >= date.today()
        ).order_by(Intervention.date.asc(), Intervention.start_time.asc()).limit(5).all()

        next_session = upcoming_sessions[0] if upcoming_sessions else None

        # Upcoming birthday event
        birth_date = client.dob
        if birth_date:
            this_year_birthday = None
            try:
                this_year_birthday = date(date.today().year, birth_date.month, birth_date.day)
            except ValueError:
                # Handle Feb 29 birthdays non-leap-year by assigning Feb 28
                this_year_birthday = date(date.today().year, 2, 28)

            if birth_date.month == date.today().month and this_year_birthday >= date.today():
                next_birthday = this_year_birthday
            else:
                next_birthday = None
        else:
            next_birthday = None

        upcoming_events = []
        if next_birthday:
            upcoming_events.append({
                'type': 'Birthday',
                'date': next_birthday,
                'description': ""
            })
        if next_session:
            upcoming_events.append({
                'type': 'Next Session',
                'date': next_session.date,
                'description': f"{next_session.intervention_type} with {next_session.employee.firstname} {next_session.employee.lastname}"
            })

        invoices = Invoice.query.filter_by(client_id=client.id).all()

        def compute_stats(invoice_list):
            invoiced = round(sum([inv.total_cost or 0.0 for inv in invoice_list]), 2)
            paid = round(sum([inv.total_cost or 0.0 for inv in invoice_list if inv.status and inv.status.lower() == 'paid']), 2)
            pending = round(max(invoiced - paid, 0.0), 2)
            return invoiced, paid, pending

        today = date.today()
        year_start = date(today.year, 1, 1)
        month_start = date(today.year, today.month, 1)

        invoices_month = [inv for inv in invoices if inv.invoiced_date and inv.invoiced_date >= month_start]
        invoices_year = [inv for inv in invoices if inv.invoiced_date and inv.invoiced_date >= year_start]

        invoiced_overall, paid_overall, pending_overall = compute_stats(invoices)
        invoiced_year, paid_year, pending_year = compute_stats(invoices_year)
        invoiced_month, paid_month, pending_month = compute_stats(invoices_month)

        return render_template(
            'client_info.html',
            client=client,
            total_sessions=total_sessions,
            total_session_hours=total_session_hours,
            all_sessions=all_sessions,
            upcoming_sessions=upcoming_sessions,
            upcoming_events=upcoming_events,
            invoices=invoices,
            invoice_stats={
                'overall': {'invoiced': invoiced_overall, 'paid': paid_overall, 'pending': pending_overall},
                'year': {'invoiced': invoiced_year, 'paid': paid_year, 'pending': pending_year},
                'month': {'invoiced': invoiced_month, 'paid': paid_month, 'pending': pending_month}
            },
            session_stats={
                'overall': {'sessions': sessions_overall_count, 'hours': sessions_overall_hours},
                'year': {'sessions': sessions_year_count, 'hours': sessions_year_hours},
                'month': {'sessions': sessions_month_count, 'hours': sessions_month_hours}
            },
            org_name=get_org_settings()['org_name']
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
        
        if request.method == 'GET':
            # Populate form with existing data, handling both new and legacy fields
            form.parent_firstname.data = client.parent_firstname or (
                client.parentname.split(maxsplit=1)[0] if client.parentname else ''
            )
            form.parent_lastname.data = client.parent_lastname or (
                client.parentname.split(maxsplit=1)[1] if client.parentname and ' ' in client.parentname else ''
            )
            form.parent_email.data = client.parent_email or client.parentemail or ''
            form.parent_cell.data = client.parent_cell or client.parentcell or ''
            form.parent2_firstname.data = client.parent2_firstname or ''
            form.parent2_lastname.data = client.parent2_lastname or ''
            form.parent2_email.data = client.parent2_email or ''
            form.parent2_cell.data = client.parent2_cell or ''
        
        if request.method == 'POST':
            # Normalize phone numbers
            normalized_parent_cell = re.sub(r'\D', '', (form.parent_cell.data or ''))
            normalized_parent2_cell = re.sub(r'\D', '', (form.parent2_cell.data or '')) if form.parent2_cell.data else ''
            
            # Create legacy parentname for full backward compatibility
            legacy_parentname = f"{form.parent_firstname.data.title()} {form.parent_lastname.data.title()}".strip()
            
            # Update client with new fields
            client.firstname = form.firstname.data.title()
            client.lastname = form.lastname.data.title()
            client.dob = form.dob.data
            client.gender = form.gender.data.title()
            
            # Update parent 1 fields
            client.parent_firstname = form.parent_firstname.data.title()
            client.parent_lastname = form.parent_lastname.data.title() if form.parent_lastname.data else ''
            client.parent_email = form.parent_email.data
            client.parent_cell = normalized_parent_cell
            
            # Update parent 2 fields
            client.parent2_firstname = form.parent2_firstname.data.title() if form.parent2_firstname.data else None
            client.parent2_lastname = form.parent2_lastname.data.title() if form.parent2_lastname.data else None
            client.parent2_email = form.parent2_email.data if form.parent2_email.data else None
            client.parent2_cell = normalized_parent2_cell if normalized_parent2_cell else None
            
            # Update legacy fields for backward compatibility
            client.parentname = legacy_parentname
            client.parentemail = form.parent_email.data
            client.parentemail2 = form.parent2_email.data if form.parent2_email.data else None
            client.parentcell = normalized_parent_cell
            
            # Update address and other fields
            client.address1 = form.address1.data.title()
            client.address2 = form.address2.data.title() if form.address2.data else ''
            client.city = form.city.data.title()
            client.state = form.state.data
            client.zipcode = form.zipcode.data.upper()
            client.supervisor_id = form.supervisor_id.data
            client.cost_supervision = form.cost_supervision.data or 0
            client.cost_therapy = form.cost_therapy.data or 0
            db.session.commit()
            flash('Client record updated successfully.', 'success')
            return redirect(url_for('clients.list_clients'))
        settings = get_org_settings()
        return render_template('update.html', form=form, client=client, org_name=settings['org_name'])
    else:
        abort(403)

