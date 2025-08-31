from flask import Blueprint, render_template, redirect, url_for, request, flash, make_response, abort
from app import db
from app.models import Invoice, Intervention, Client, Activity, Employee
from app.invoices.forms import InvoiceClientSelectionForm
from datetime import date, timedelta, datetime
from sqlalchemy import and_
from flask_login import login_required, current_user
from weasyprint import HTML


invoices_bp = Blueprint('invoices', __name__, template_folder='templates')


def parse_date(val):
    if isinstance(val, str) and val:
        return datetime.strptime(val, "%Y-%m-%d").date()
    return val


@invoices_bp.route('/list', methods=['GET'])
@login_required
def list_invoices():
    if current_user.is_authenticated and current_user.user_type == "admin":
        invoices = Invoice.query.order_by(Invoice.invoiced_date.desc()).all()
        return render_template('list_invoices.html', invoices=invoices)
    else:
        abort(403)


@invoices_bp.route('/invoice_client_selection', methods=['GET', 'POST'])
@login_required
def invoice_client_select():
    if current_user.is_authenticated and current_user.user_type == "admin":
        
        clients = Client.query.all()
        print(clients)
        if not clients:
            flash('Please add clients before creating invoices.', 'warning')
            return redirect(url_for('clients.list_clients'))
        
        interventions = Intervention.query.filter_by(invoiced=False).all()
        print(interventions)
        if not interventions:
            flash('No uninvoiced interventions available to create an invoice.', 'warning')
            return redirect(url_for('interventions.list_interventions'))
        
        form = InvoiceClientSelectionForm()
        form.client_id.choices = [(str(c.id), f"{c.firstname} {c.lastname}") for c in Client.query.all()]
        if form.validate_on_submit():
            interventions = Intervention.query.filter(and_(Intervention.invoiced == False, Intervention.client_id == form.client_id.data)).all()
            if not interventions:
                flash('No uninvoiced interventions found for the selected client.', 'warning')
                return redirect(url_for('interventions.list_interventions'))
            
            return redirect(url_for(
                'invoices.invoice_preview',
                ci=form.client_id.data,
                df=form.date_from.data,
                dt=form.date_to.data))
        
        return render_template('invoice_client_select.html', form=form)
    else:
        abort(403)


@invoices_bp.route('/invoice_preview', methods=['GET', 'POST'])
@login_required
def invoice_preview():
    if current_user.is_authenticated and current_user.user_type == "admin":
        client_id = request.args.get('ci')
        date_from = parse_date(request.args.get('df'))
        date_to = parse_date(request.args.get('dt'))

        client = Client.query.get(int(client_id))
        interventions = Intervention.query.filter(
            Intervention.client_id == int(client_id),
            Intervention.invoiced == False,
            Intervention.date >= date_from,
            Intervention.date <= date_to
            ).order_by(Intervention.date, Intervention.start_time).all()

        # Get the superivisor's name
        supervisor = Employee.query.get(client.supervisor_id) if client and client.supervisor_id else None
        supervisor_name = f"{supervisor.firstname} {supervisor.lastname}" if supervisor else "N/A"

        # Generate invoice number and dates
        invoice_number = Invoice.generate_invoice_number()
        invoice_date = date.today()
        payby_date = invoice_date + timedelta(days=7)

        # Prepare address and parent name
        parent_name = f"{client.parentname}"
        address = f"{client.address1}, "
        address += f"{client.address2}, " if client.address2 else ""
        address += f"{client.city}, {client.state} {client.zipcode}"

        # Fetch all activities for quick lookup
        activity_map = {a.activity_name: a.activity_category for a in Activity.query.all()}

        for i in interventions:
            # Determine category from activity name
            category = activity_map.get(i.intervention_type, '').lower()
            # Get the correct rate from client
            if category == 'therapy':
                rate = client.cost_therapy
            elif category == 'supervision':
                rate = client.cost_supervision
            else:
                rate = 0  # or a default rate
            i.rate = rate  # Store the rate in the intervention for later use
            
            try:
                # Assuming i.duration is in hours (as float or string)
                i.cost = float(i.duration) * float(rate)
            except Exception:
                i.cost = 0

        if request.method == 'POST':
            intervention_ids_str = ",".join(str(i.id) for i in interventions)
            
            total_cost = sum(i.cost for i in interventions)
            # 1. Create Invoice record
            invoice = Invoice(
                client_id=client.id,
                invoice_number=invoice_number,
                invoiced_date=invoice_date,
                payby_date=payby_date,
                date_from=date_from,
                date_to=date_to,
                intervention_ids=intervention_ids_str,
                total_cost=total_cost,  # <-- store here
                status="Draft",
                paid_date=None,
                payment_comments=""
            )
            db.session.add(invoice)
            db.session.flush()  # To get invoice.id if needed

            # 2. Update interventions
            for intervention in interventions:
                intervention.invoiced = True
                intervention.invoice_number = invoice_number
                db.session.add(intervention)

            db.session.commit()
            flash('Invoice created and sessions updated.', 'success')
            return redirect(url_for('invoices.list_invoices'))

        return render_template(
            'invoice_preview.html',
            org_name="1001256835 ONTARIO INC.",
            parent_name=parent_name,
            billing_address=address,
            client=client,
            invoice_number=invoice_number,
            invoice_date=invoice_date.strftime('%Y-%m-%d'),
            payby_date=payby_date.strftime('%Y-%m-%d'),
            date_from=date_from.strftime('%Y-%m-%d'),
            date_to=date_to.strftime('%Y-%m-%d'),
            supervisor_name=supervisor_name,
            interventions=interventions
        )
    else:
        abort(403)


@invoices_bp.route('/download_invoice/<invoice_number>', methods=['GET'])
@login_required
def download_invoice_pdf_by_number(invoice_number):
    if current_user.is_authenticated and current_user.user_type == "admin":
        invoice = Invoice.query.filter_by(invoice_number=invoice_number).first_or_404()
        client = invoice.client
        interventions = Intervention.query.filter_by(invoice_number=invoice_number).order_by(Intervention.date, Intervention.start_time).all()

        # Calculate cost for each intervention (if needed)
        from app.models import Activity
        activity_map = {a.activity_name: a.activity_category for a in Activity.query.all()}
        for i in interventions:
            category = activity_map.get(i.intervention_type, '').lower()
            if category == 'therapy':
                rate = client.cost_therapy
            elif category == 'supervision':
                rate = client.cost_supervision
            else:
                rate = 0
            i.rate = rate  # Store the rate in the intervention for later use

            try:
                i.cost = float(i.duration) * float(rate)
            except Exception:
                i.cost = 0

        parent_name = getattr(client, 'parent_name', '')
        address = f"{client.address1}{', ' + client.address2 if client.address2 else ''}<br>{client.city}, {client.state} {client.zipcode}"

        # Get the superivisor's name
        supervisor = Employee.query.get(client.supervisor_id) if client and client.supervisor_id else None
        supervisor_name = f"{supervisor.firstname} {supervisor.lastname}" if supervisor else "N/A"

        html = render_template(
            'invoice_pdf.html',  # <-- use the new template!
            org_name="1001256835 ONTARIO INC.",
            parent_name=parent_name,
            billing_address=address,
            client=client,
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoiced_date.strftime('%Y-%m-%d'),
            payby_date=invoice.payby_date.strftime('%Y-%m-%d'),
            date_from=invoice.date_from.strftime('%Y-%m-%d'),
            date_to=invoice.date_to.strftime('%Y-%m-%d'),
            supervisor_name=supervisor_name,
            interventions=interventions
        )

        pdf = HTML(string=html).write_pdf()
        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'attachment; filename={invoice.invoice_number}.pdf'
        return response
    else:
        abort(403)


@invoices_bp.route('/preview_invoice/<invoice_number>', methods=['GET'])
@login_required
def preview_invoice_by_number(invoice_number):
    if current_user.is_authenticated and current_user.user_type == "admin":
        invoice = Invoice.query.filter_by(invoice_number=invoice_number).first_or_404()
        client = invoice.client
        interventions = Intervention.query.filter_by(invoice_number=invoice_number).order_by(Intervention.date, Intervention.start_time).all()
        # Calculate cost/rate for each intervention as in your other views
        from app.models import Activity
        activity_map = {a.activity_name: a.activity_category for a in Activity.query.all()}
        for i in interventions:
            category = activity_map.get(i.intervention_type, '').lower()
            if category == 'therapy':
                rate = client.cost_therapy
            elif category == 'supervision':
                rate = client.cost_supervision
            else:
                rate = 0
            i.rate = rate
            try:
                i.cost = float(i.duration) * float(rate)
            except Exception:
                i.cost = 0
        parent_name = getattr(client, 'parent_name', '')
        address = f"{client.address1}{', ' + client.address2 if client.address2 else ''}<br>{client.city}, {client.state} {client.zipcode}"

        # Get the superivisor's name
        supervisor = Employee.query.get(client.supervisor_id) if client and client.supervisor_id else None
        supervisor_name = f"{supervisor.firstname} {supervisor.lastname}" if supervisor else "N/A"

        return render_template(
            'invoice_preview.html',
            org_name="1001256835 ONTARIO INC.",
            parent_name=parent_name,
            billing_address=address,
            client=client,
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoiced_date.strftime('%Y-%m-%d'),
            payby_date=invoice.payby_date.strftime('%Y-%m-%d'),
            date_from=invoice.date_from.strftime('%Y-%m-%d'),
            date_to=invoice.date_to.strftime('%Y-%m-%d'),
            supervisor_name=supervisor_name,
            interventions=interventions,
            total_cost=invoice.total_cost
        )
    else:
        abort(403)


@invoices_bp.route('/delete_invoice/<invoice_number>', methods=['POST'])
@login_required
def delete_invoice(invoice_number):
    if current_user.is_authenticated and current_user.user_type == "admin":
        invoice = Invoice.query.filter_by(invoice_number=invoice_number).first_or_404()
        interventions = Intervention.query.filter_by(invoice_number=invoice_number).all()
        for intervention in interventions:
            intervention.invoiced = False
            intervention.invoice_number = None
            db.session.add(intervention)
        db.session.delete(invoice)
        db.session.commit()
        flash('Invoice and related interventions updated.', 'success')
        return redirect(url_for('invoices.list_invoices'))
    else:
        abort(403)