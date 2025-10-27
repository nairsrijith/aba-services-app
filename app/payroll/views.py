from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from app import db
from app.payroll.forms import PayPeriodForm, PayRateForm
from app.models import Employee, Intervention, PayRate, PayStub, PayStubItem, Client
from sqlalchemy import extract
from flask_login import login_required, current_user
from datetime import date
from weasyprint import HTML
import tempfile
import os

payroll_bp = Blueprint('payroll', __name__, template_folder='templates')


@payroll_bp.route('/paystubs')
@login_required
def list_paystubs():
    if not (current_user.is_authenticated and current_user.user_type == 'admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))
    
    # Get filters
    employee_id = request.args.get('employee', type=int)
    month = request.args.get('month', '')
    
    # Build query
    query = PayStub.query
    
    if employee_id:
        query = query.filter_by(employee_id=employee_id)
        
    if month:  # format: YYYY-MM
        year, month = map(int, month.split('-'))
        query = query.filter(
            extract('year', PayStub.period_start) == year,
            extract('month', PayStub.period_start) == month
        )
        
    # Get results
    paystubs = query.order_by(PayStub.generated_date.desc()).all()
    # Include both active and employees with paystubs
    employee_ids = set(ps.employee_id for ps in paystubs)
    employees = Employee.query.filter(
        (Employee.is_active == True) | (Employee.id.in_(employee_ids))
    ).order_by(Employee.firstname, Employee.lastname).all()
    
    return render_template('list_paystubs.html', paystubs=paystubs, employees=employees)


@payroll_bp.route('/payrates')
@login_required
def list_payrates():
    if not (current_user.is_authenticated and current_user.user_type == 'admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))
    payrates = PayRate.query.order_by(PayRate.employee_id, PayRate.client_id).all()
    return render_template('list_payrates.html', payrates=payrates)


@payroll_bp.route('/payrates/add', methods=['GET', 'POST'])
@login_required
def add_payrate():
    if not (current_user.is_authenticated and current_user.user_type == 'admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))
    
    form = PayRateForm()
    form.employee.choices = [(str(e.id), f"{e.firstname} {e.lastname}") for e in Employee.query.filter_by(is_active=True).order_by(Employee.firstname, Employee.lastname).all()]
    # Add a 'Base Rate (All Clients)' option for client_id=None
    client_choices = [("", "Base Rate (All Clients)")]
    client_choices += [(str(c.id), f"{c.firstname} {c.lastname}") for c in Client.query.filter_by(is_active=True).order_by(Client.firstname, Client.lastname).all()]
    form.client.choices = client_choices
    
    if form.validate_on_submit():
        # If client is blank, treat as base rate (client_id=None)
        client_id = int(form.client.data) if form.client.data else None
        payrate = PayRate(
            employee_id=int(form.employee.data),
            client_id=client_id,
            rate=form.rate.data,
            effective_date=form.effective_date.data
        )
        db.session.add(payrate)
        db.session.commit()
        flash('Pay rate added successfully', 'success')
        return redirect(url_for('payroll.list_payrates'))
    
    return render_template('edit_payrate.html', form=form, payrate=None)


@payroll_bp.route('/payrates/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_payrate(id):
    if not (current_user.is_authenticated and current_user.user_type == 'admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))
    
    payrate = PayRate.query.get_or_404(id)
    form = PayRateForm()
    
    # Get current employee and client for this payrate
    current_employee = Employee.query.get(payrate.employee_id)
    current_client = Client.query.get(payrate.client_id) if payrate.client_id else None

    # Get all active employees plus the current employee if inactive
    employee_choices = [(str(e.id), f"{e.firstname} {e.lastname}") 
                     for e in Employee.query.filter_by(is_active=True).order_by(Employee.firstname, Employee.lastname).all()]
    if current_employee and not current_employee.is_active:
        employee_choices.append((str(current_employee.id), f"{current_employee.firstname} {current_employee.lastname} (Inactive)"))
    form.employee.choices = employee_choices

    # Get all active clients plus the current client if inactive
    client_choices = [("", "Base Rate (All Clients)")]
    client_choices += [(str(c.id), f"{c.firstname} {c.lastname}") 
                      for c in Client.query.filter_by(is_active=True).order_by(Client.firstname, Client.lastname).all()]
    if current_client and not current_client.is_active:
        client_choices.append((str(current_client.id), f"{current_client.firstname} {current_client.lastname} (Inactive)"))
    form.client.choices = client_choices
    
    if form.validate_on_submit():
        payrate.employee_id = int(form.employee.data)
        payrate.client_id = int(form.client.data) if form.client.data else None
        payrate.rate = form.rate.data
        payrate.effective_date = form.effective_date.data
        db.session.commit()
        flash('Pay rate updated successfully', 'success')
        return redirect(url_for('payroll.list_payrates'))
    elif request.method == 'GET':
        form.employee.data = str(payrate.employee_id)
        form.client.data = str(payrate.client_id) if payrate.client_id is not None else ""
        form.rate.data = payrate.rate
        form.effective_date.data = payrate.effective_date
    
    return render_template('edit_payrate.html', form=form, payrate=payrate)


@payroll_bp.route('/payrates/<int:id>/delete', methods=['POST'])
@login_required
def delete_payrate(id):
    if not (current_user.is_authenticated and current_user.user_type == 'admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))
    
    payrate = PayRate.query.get_or_404(id)
    db.session.delete(payrate)
    db.session.commit()
    flash('Pay rate deleted successfully', 'success')
    return redirect(url_for('payroll.list_payrates'))


@payroll_bp.route('/paystubs/<int:id>')
@login_required
def view_paystub(id):
    if not (current_user.is_authenticated and current_user.user_type == 'admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))
    
    paystub = PayStub.query.get_or_404(id)
    return render_template('view_paystub.html', paystub=paystub)


@payroll_bp.route('/paystubs/<int:id>/pdf')
@login_required
def export_paystub_pdf(id):
    try:
        if not (current_user.is_authenticated and current_user.user_type == 'admin'):
            flash('Unauthorized', 'danger')
            return redirect(url_for('home'))
        
        paystub = PayStub.query.get_or_404(id)
        
        # Get logo path or base64 data. Prefer configured LOGO_PATH (or env var),
        # otherwise fall back to app static favicon as a base64-embedded image.
        logo_b64 = None
        logo_path = None
        try:
            # check configuration first (support both config and environment variable)
            configured_logo = current_app.config.get('LOGO_PATH') or os.environ.get('LOGO_PATH')
            configured_logo_url = current_app.config.get('LOGO_URL') or os.environ.get('LOGO_URL')

            if configured_logo:
                # if relative path, resolve against app root
                lp = configured_logo
                if not os.path.isabs(lp):
                    lp = os.path.join(current_app.root_path, lp)
                if os.path.exists(lp):
                    logo_path = lp
            elif configured_logo_url:
                # provide a URL to the template if present
                logo_url = configured_logo_url
            else:
                # fallback to static favicon embedded as base64
                static_logo = os.path.join(current_app.static_folder, 'images', 'favicon.ico')
                if os.path.exists(static_logo):
                    import base64
                    with open(static_logo, 'rb') as f:
                        logo_b64 = f'data:image/x-icon;base64,{base64.b64encode(f.read()).decode()}'
        except Exception as e:
            current_app.logger.warning(f'Logo loading failed: {str(e)}')

        # Get organization details from config or environment (support ORG_* names in .env)
        org_name = current_app.config.get('ORG_NAME') or current_app.config.get('ORGANIZATION_NAME') or os.environ.get('ORG_NAME') or 'ABA Services'
        org_phone = current_app.config.get('ORG_PHONE') or current_app.config.get('ORGANIZATION_PHONE') or os.environ.get('ORG_PHONE') or ''
        org_email = current_app.config.get('ORG_EMAIL') or current_app.config.get('ORGANIZATION_EMAIL') or os.environ.get('ORG_EMAIL') or ''
        org_address = current_app.config.get('ORG_ADDRESS') or current_app.config.get('ORGANIZATION_ADDRESS') or os.environ.get('ORG_ADDRESS') or ''
        
        # Generate PDF using WeasyPrint with the new template
        # render the template from this blueprint's templates folder
        html = render_template('paystub_pdf.html',
                           paystub=paystub,
                           logo_b64=logo_b64,
                           logo_path=logo_path if 'logo_path' in locals() else None,
                           logo_url=locals().get('logo_url', None),
                           org_name=org_name,
                           org_phone=org_phone,
                           org_email=org_email,
                           org_address=org_address)
        
        # Create a temporary file for the PDF
        temp_dir = tempfile.mkdtemp()
        pdf_path = os.path.join(temp_dir, f'paystub_{id}.pdf')
        
        # Generate PDF from HTML with custom styles
        HTML(string=html, base_url=request.url_root).write_pdf(pdf_path)
        
        # Send the PDF file
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f'paystub_{paystub.period_start.strftime("%Y%m%d")}_{paystub.employee.lastname}.pdf'
        )
    except Exception as e:
        current_app.logger.error(f'PDF generation failed: {str(e)}')
        flash('Error generating PDF. Please try again or contact support.', 'danger')
        return redirect(url_for('payroll.view_paystub', id=id))


@payroll_bp.route('/paystubs/<int:id>/delete', methods=['POST'])
@login_required
def delete_paystub(id):
    if not (current_user.is_authenticated and current_user.user_type == 'admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))

    paystub = PayStub.query.get_or_404(id)
    
    # Get all interventions associated with this paystub through paystub items
    for item in paystub.items:
        # Unmark the intervention as paid
        if item.intervention:
            item.intervention.is_paid = False
    
    # deleting paystub will cascade to PayStubItem because of relationship cascade
    db.session.delete(paystub)
    db.session.commit()
    flash('Paystub deleted successfully', 'success')
    return redirect(url_for('payroll.list_paystubs'))


@payroll_bp.route('/paystubs/create', methods=['GET', 'POST'])
@login_required
def create_paystub():
    if not (current_user.is_authenticated and current_user.user_type == 'admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))

    form = PayPeriodForm()
    # populate employee choices
    form.employee.choices = [(str(e.id), f"{e.firstname} {e.lastname}") for e in Employee.query.filter_by(is_active=True).order_by(Employee.firstname, Employee.lastname).all()]

    preview = None
    missing_rates = []

    if form.validate_on_submit():
        emp_id = int(form.employee.data)
        start = form.start_date.data
        end = form.end_date.data
        if start > end:
            flash('Start date must be before end date', 'danger')
            return render_template('create_paystub.html', form=form)

        sessions = Intervention.query.filter(Intervention.employee_id == emp_id, Intervention.date >= start, Intervention.date <= end).order_by(Intervention.date).all()

        lines = []
        total_hours = 0.0
        total_amount = 0.0
        for s in sessions:
            # 1. Try to find latest client-specific rate for employee-client pair
            rate = None
            payrates = PayRate.query.filter_by(employee_id=emp_id, client_id=s.client_id).order_by(PayRate.effective_date.desc()).all()
            if payrates:
                for pr in payrates:
                    if pr.effective_date is None or pr.effective_date <= s.date:
                        rate = pr.rate
                        break
                if rate is None:
                    rate = payrates[0].rate

            # 2. If no client-specific rate, use latest base rate (client_id is None)
            if rate is None:
                base_rates = PayRate.query.filter_by(employee_id=emp_id, client_id=None).order_by(PayRate.effective_date.desc()).all()
                if base_rates:
                    for br in base_rates:
                        if br.effective_date is None or br.effective_date <= s.date:
                            rate = br.rate
                            break
                    if rate is None:
                        rate = base_rates[0].rate

            # 3. If still no rate, mark as missing
            if rate is None:
                missing_rates.append((s.client_id, s.id))
                continue

            amount = round(rate * (s.duration or 0), 2)
            lines.append({'intervention': s, 'client': s.client, 'rate': rate, 'hours': s.duration, 'amount': amount})
            total_hours += s.duration or 0
            total_amount += amount

        preview = {'lines': lines, 'total_hours': round(total_hours, 2), 'total_amount': round(total_amount, 2), 'start': start, 'end': end, 'employee': Employee.query.get(emp_id)}

        if 'save' in request.form and preview and not missing_rates:
            # save paystub and items
            ps = PayStub(employee_id=emp_id, period_start=start, period_end=end, generated_date=date.today(), total_hours=preview['total_hours'], total_amount=preview['total_amount'])
            db.session.add(ps)
            db.session.flush()  # get ps.id
            for ln in preview['lines']:
                # Create paystub item
                item = PayStubItem(paystub_id=ps.id, intervention_id=ln['intervention'].id, client_id=ln['client'].id, rate=ln['rate'], hours=ln['hours'], amount=ln['amount'])
                db.session.add(item)
                # Mark intervention as paid
                ln['intervention'].is_paid = True
            db.session.commit()
            flash('Paystub saved successfully', 'success')
            return redirect(url_for('payroll.list_paystubs'))

        if missing_rates:
            flash('Missing pay rates for some client(s). Please add pay rates before saving.', 'danger')

    return render_template('create_paystub.html', form=form, preview=preview, missing_rates=missing_rates)
