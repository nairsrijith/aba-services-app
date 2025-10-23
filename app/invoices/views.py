from flask import Blueprint, render_template, redirect, url_for, request, flash, make_response, abort
from app import db
import json
import base64
import os
from app.models import Invoice, Intervention, Client, Activity, Employee
from app.invoices.forms import InvoiceClientSelectionForm
from datetime import date, timedelta, datetime
from sqlalchemy import and_
from flask_login import login_required, current_user
from weasyprint import HTML
import os

invoices_bp = Blueprint('invoices', __name__, template_folder='templates')


org_name = os.environ.get('ORG_NAME', 'My Organization')
org_address = os.environ.get('ORG_ADDRESS', 'Organization Address')
org_email = os.environ.get('ORG_EMAIL', 'email@org.com')
payment_email = os.environ.get('PAYMENT_EMAIL', 'payments@org.com')
org_phone = os.environ.get('ORG_PHONE', 'Org Phone')


def parse_date(val):
    if isinstance(val, str) and val:
        return datetime.strptime(val, "%Y-%m-%d").date()
    return val


@invoices_bp.route('/list', methods=['GET'])
@login_required
def list_invoices():
    if current_user.is_authenticated and current_user.user_type == "admin":
        invoices = Invoice.query.order_by(Invoice.invoiced_date.desc()).all()
        return render_template('list_invoices.html', invoices=invoices, org_name=org_name)
    else:
        abort(403)


@invoices_bp.route('/invoice_client_selection', methods=['GET', 'POST'])
@login_required
def invoice_client_select():
    if current_user.is_authenticated and current_user.user_type == "admin":
        interventions = Intervention.query.filter_by(invoiced=False).all()
        if not interventions:
            flash('No uninvoiced session available to create an invoice.', 'warning')
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
        
        return render_template('invoice_client_select.html', form=form, org_name=org_name)
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
        supervisor_rba_number = supervisor.rba_number if supervisor else "N/A"

        # Generate invoice number and dates
        invoice_number = Invoice.generate_invoice_number()
        invoice_date = date.today()
        payby_date = invoice_date + timedelta(days=7)

        # Prepare address and parent name
        parent_name = f"{client.parentname}"
        address = f"{client.address1}, "
        address += f"{client.address2}, " if client.address2 else ""
        address += f"{client.city}, {client.state} {client.zipcode}"

        status = "Pending"

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
            # Build a snapshot of invoice line items so future changes to client rates won't affect this invoice
            invoice_items = []
            for i in interventions:
                invoice_items.append({
                    'intervention_id': i.id,
                    'date': i.date.strftime('%Y-%m-%d'),
                    'activity': i.intervention_type,
                    'duration': float(i.duration) if i.duration is not None else 0,
                    'rate': float(i.rate) if hasattr(i, 'rate') and i.rate is not None else 0,
                    'cost': float(i.cost) if hasattr(i, 'cost') and i.cost is not None else 0
                })

            total_cost = sum(item['cost'] for item in invoice_items)
            # 1. Create Invoice record (no longer storing intervention_ids; snapshot stored in invoice_items)
            invoice = Invoice(
                client_id=client.id,
                invoice_number=invoice_number,
                invoiced_date=invoice_date,
                payby_date=payby_date,
                date_from=date_from,
                date_to=date_to,
                total_cost=total_cost,  # <-- store here
                status="Draft",
                paid_date=None,
                payment_comments="",
                invoice_items=json.dumps(invoice_items)
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
            parent_name=parent_name,
            billing_address=address,
            client=client,
            invoice_number=invoice_number,
            invoice_date=invoice_date.strftime('%Y-%m-%d'),
            payby_date=payby_date.strftime('%Y-%m-%d'),
            date_from=date_from.strftime('%Y-%m-%d'),
            date_to=date_to.strftime('%Y-%m-%d'),
            status=status,
            supervisor_name=supervisor_name,
            supervisor_rba_number=supervisor_rba_number,
            interventions=interventions,
            org_name=org_name
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

        # Use invoice_items snapshot if available; otherwise fall back to calculating from current rates
        import json
        if invoice.invoice_items:
            try:
                items = json.loads(invoice.invoice_items)
            except Exception:
                items = []
            # attach snapshot data to interventions by matching ids
            items_map = {item.get('intervention_id'): item for item in items}
            for i in interventions:
                item = items_map.get(i.id)
                if item:
                    i.rate = item.get('rate', 0)
                    i.cost = item.get('cost', 0)
                    i._snapshot = item
                else:
                    # fallback: compute from current client rates
                    from app.models import Activity
                    activity_map = {a.activity_name: a.activity_category for a in Activity.query.all()}
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
        supervisor_rba_number = supervisor.rba_number if supervisor else "N/A"

        status = "Pending" if invoice.status != "Paid" else invoice.status

        # Build logo context from deployment-time environment variables. Priority:
        # LOGO_BASE64 -> LOGO_URL -> LOGO_PATH -> fallback to static url
        logo_b64 = None
        logo_url = os.environ.get('LOGO_URL')
        logo_path_env = os.environ.get('LOGO_PATH')
        logo_base64_env = os.environ.get('LOGO_BASE64')

        if logo_base64_env:
            # If the env var contains raw base64 (without data: prefix), add prefix
            if logo_base64_env.strip().startswith('data:'):
                logo_b64 = logo_base64_env.strip()
            else:
                # assume png unless overridden; icon files may be x-icon
                # allow user to include mime if needed in env
                logo_b64 = f"data:image/png;base64,{logo_base64_env.strip()}"
        elif logo_url:
            # remote HTTP(S) URL
            pass
        elif logo_path_env:
            # file path inside container
            # normalize to absolute path
            logo_path_env = os.path.abspath(logo_path_env)

        html = render_template(
            'invoice_pdf.html',  # <-- use the new template!
            parent_name=parent_name,
            billing_address=address,
            client=client,
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoiced_date.strftime('%Y-%m-%d'),
            payby_date=invoice.payby_date.strftime('%Y-%m-%d'),
            date_from=invoice.date_from.strftime('%Y-%m-%d'),
            date_to=invoice.date_to.strftime('%Y-%m-%d'),
            supervisor_name=supervisor_name,
            supervisor_rba_number=supervisor_rba_number,
            status=status,
            paid_date=invoice.paid_date.strftime('%Y-%m-%d') if invoice.paid_date else '',
            payment_comments=invoice.payment_comments,
            interventions=interventions,
            org_name=org_name,
            org_address=org_address,
            org_email=org_email,
            payment_email=payment_email,
            org_phone=org_phone,
            logo_b64=logo_b64,
            logo_url=logo_url,
            logo_path=logo_path_env
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
        # Use invoice_items snapshot if available; otherwise compute
        import json
        if invoice.invoice_items:
            try:
                items = json.loads(invoice.invoice_items)
            except Exception:
                items = []
            items_map = {item.get('intervention_id'): item for item in items}
            for i in interventions:
                item = items_map.get(i.id)
                if item:
                    i.rate = item.get('rate', 0)
                    i.cost = item.get('cost', 0)
                    i._snapshot = item
                else:
                    from app.models import Activity
                    activity_map = {a.activity_name: a.activity_category for a in Activity.query.all()}
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
        supervisor_rba_number = supervisor.rba_number if supervisor else "N/A"

        status = "Pending" if invoice.status != "Paid" else invoice.status

        return render_template(
            'invoice_preview.html',
            parent_name=parent_name,
            billing_address=address,
            client=client,
            invoice_number=invoice.invoice_number,
            invoice_date=invoice.invoiced_date.strftime('%Y-%m-%d'),
            payby_date=invoice.payby_date.strftime('%Y-%m-%d'),
            date_from=invoice.date_from.strftime('%Y-%m-%d'),
            date_to=invoice.date_to.strftime('%Y-%m-%d'),
            status=status,
            supervisor_name=supervisor_name,
            supervisor_rba_number=supervisor_rba_number,
            interventions=interventions,
            total_cost=invoice.total_cost,
            org_name=org_name
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


@invoices_bp.route('/mark_sent/<invoice_number>', methods=['POST'])
@login_required
def mark_sent(invoice_number):
    if current_user.is_authenticated and current_user.user_type == "admin":
        invoice = Invoice.query.filter_by(invoice_number=invoice_number).first_or_404()
        invoice.status = 'Sent'
        db.session.commit()
        flash('Invoice marked as Sent.', 'success')
        return redirect(url_for('invoices.list_invoices'))
    else:
        abort(403)


@invoices_bp.route('/mark_draft/<invoice_number>', methods=['POST'])
@login_required
def mark_draft(invoice_number):
    if current_user.is_authenticated and current_user.user_type == "admin":
        invoice = Invoice.query.filter_by(invoice_number=invoice_number).first_or_404()
        invoice.status = 'Draft'
        invoice.paid_date = None
        invoice.payment_comments = ""
        db.session.commit()
        flash('Invoice sent back to Draft.', 'success')
        return redirect(url_for('invoices.list_invoices'))
    else:
        abort(403)


@invoices_bp.route('/mark_paid/<invoice_number>', methods=['POST'])
@login_required
def mark_paid(invoice_number):
    if current_user.is_authenticated and current_user.user_type == "admin":
        invoice = Invoice.query.filter_by(invoice_number=invoice_number).first_or_404()
        paid_date = datetime.strptime(request.form.get('paid_date'), '%Y-%m-%d').date()
        payment_comments = request.form.get('payment_comments')
        invoice.status = 'Paid'
        invoice.paid_date = paid_date
        invoice.payment_comments = payment_comments
        db.session.commit()
        flash('Invoice marked as Paid.', 'success')
        return redirect(url_for('invoices.list_invoices'))
    else:
        abort(403)