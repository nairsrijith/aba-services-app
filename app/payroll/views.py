from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from app import db
from app.payroll.forms import PayPeriodForm, PayRateForm
from app.models import Employee, Intervention, PayRate, PayStub, PayStubItem, Client
from sqlalchemy import extract
from flask_login import login_required, current_user
from datetime import date, datetime
from weasyprint import HTML
import tempfile, os
from app.utils.email_utils import queue_email_with_pdf
from app.utils.settings_utils import get_org_settings


payroll_bp = Blueprint('payroll', __name__, template_folder='templates')


@payroll_bp.route('/paystubs')
@login_required
def list_paystubs():
    if not current_user.is_authenticated:
        flash('Please log in to view paystubs.', 'danger')
        return redirect(url_for('home'))
    
    # Get filters
    month = request.args.get('month', '')
    
    # Build query based on user role
    query = PayStub.query
    
    if current_user.user_type in ['admin', 'super']:
        # Admins can see all paystubs and filter by employee
        employee_id = request.args.get('employee', type=int)
        if employee_id:
            query = query.filter_by(employee_id=employee_id)
    else:
        # Regular users can only see their own paystubs
        emp = Employee.query.filter_by(email=current_user.email).first()
        if not emp:
            flash('No employee record found for your account.', 'danger')
            return redirect(url_for('home'))
        query = query.filter_by(employee_id=emp.id)
        
    if month:  # format: YYYY-MM
        year, month = map(int, month.split('-'))
        query = query.filter(
            extract('year', PayStub.period_start) == year,
            extract('month', PayStub.period_start) == month
        )
        
    # Get results
    paystubs = query.order_by(PayStub.generated_date.desc()).all()
    
    # Get employee list for filter (only for admin/super)
    if current_user.user_type in ['admin', 'super']:
        employee_ids = set(ps.employee_id for ps in paystubs)
        employees = Employee.query.filter(
            (Employee.is_active == True) | (Employee.id.in_(employee_ids))
        ).order_by(Employee.firstname, Employee.lastname).all()
    else:
        employees = None
    
    return render_template('list_paystubs.html', paystubs=paystubs, employees=employees)


@payroll_bp.route('/payrates')
@login_required
def list_payrates():
    if not (current_user.is_authenticated and current_user.user_type in ['admin', 'super']):
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))
    payrates = PayRate.query.order_by(PayRate.employee_id, PayRate.client_id).all()
    return render_template('list_payrates.html', payrates=payrates)


@payroll_bp.route('/payrates/add', methods=['GET', 'POST'])
@login_required
def add_payrate():
    if not (current_user.is_authenticated and current_user.user_type in ['admin', 'super']):
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
    if not (current_user.is_authenticated and current_user.user_type in ['admin', 'super']):
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
    if not (current_user.is_authenticated and current_user.user_type in ['admin', 'super']):
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
    if not current_user.is_authenticated:
        flash('Please log in to view paystubs.', 'danger')
        return redirect(url_for('home'))
    
    paystub = PayStub.query.get_or_404(id)
    
    # Check if user has permission to view this paystub
    if current_user.user_type not in ['admin', 'super']:
        emp = Employee.query.filter_by(email=current_user.email).first()
        if not emp or emp.id != paystub.employee_id:
            flash('Unauthorized access.', 'danger')
            return redirect(url_for('home'))
    
    return render_template('view_paystub.html', paystub=paystub)


@payroll_bp.route('/paystubs/<int:id>/pdf')
@login_required
def export_paystub_pdf(id):
    try:
        if not current_user.is_authenticated:
            flash('Please log in to download paystubs.', 'danger')
            return redirect(url_for('home'))
        
        paystub = PayStub.query.get_or_404(id)
        
        # Check if user has permission to download this paystub
        if current_user.user_type not in ['admin', 'super']:
            emp = Employee.query.filter_by(email=current_user.email).first()
            if not emp or emp.id != paystub.employee_id:
                flash('Unauthorized access.', 'danger')
                return redirect(url_for('home'))
        
        # Resolve org settings and logo using AppSettings -> env -> defaults
        settings = get_org_settings()
        logo_b64 = settings.get('logo_b64')
        logo_file_uri = settings.get('logo_file_uri')
        logo_web_path = settings.get('logo_web_path')
        logo_url = settings.get('logo_url')
        org_name = settings.get('org_name')
        org_phone = settings.get('org_phone')
        org_email = settings.get('org_email')
        org_address = settings.get('org_address')
        
        
        # Get current timestamp for download time
        download_time = datetime.now()
        formatted_time = download_time.strftime('%Y/%m/%d %H:%M:%S')
        filename_time = download_time.strftime('%Y%m%d%H%M%S')
        
        # Generate PDF using WeasyPrint with the new template
        # render the template from this blueprint's templates folder
        html = render_template('paystub_pdf.html',
               paystub=paystub,
               logo_b64=logo_b64,
               # For PDF rendering prefer a file:// URI; fall back to web path
               logo_path=logo_file_uri or logo_web_path,
               logo_url=logo_url,
               org_name=org_name,
               org_phone=org_phone,
               org_email=org_email,
               org_address=org_address,
               download_time=formatted_time)
        
        # Create a temporary file for the PDF
        temp_dir = tempfile.mkdtemp()
        pdf_path = os.path.join(temp_dir, f'paystub_{id}.pdf')
        
        # Generate PDF from HTML with custom styles
        HTML(string=html, base_url=request.url_root).write_pdf(pdf_path)
        try:
            size = os.path.getsize(pdf_path)
        except Exception:
            size = None
        
        # Send the PDF file
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f'paystub_{paystub.period_start.strftime("%Y%m%d")}-{paystub.period_end.strftime("%Y%m%d")}_{paystub.employee.firstname}_{paystub.employee.lastname}_{filename_time}.pdf'
        )
    except Exception as e:
        current_app.logger.error(f'PDF generation failed: {str(e)}')
        flash('Error generating PDF. Please try again or contact support.', 'danger')
        return redirect(url_for('payroll.view_paystub', id=id))


@payroll_bp.route('/paystubs/<int:id>/email', methods=['POST'])
@login_required
def email_paystub(id):
    if not current_user.is_authenticated:
        flash('Please log in to email paystubs.', 'danger')
        return redirect(url_for('home'))
    
    paystub = PayStub.query.get_or_404(id)
    
    # Check if user has permission to email this paystub
    if current_user.user_type not in ['admin', 'super']:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('home'))
    
    try:
        # Resolve org settings and logo
        settings = get_org_settings()
        logo_b64 = settings.get('logo_b64')
        logo_file_uri = settings.get('logo_file_uri')
        logo_web_path = settings.get('logo_web_path')
        logo_url = settings.get('logo_url')
        org_name = settings.get('org_name')
        
        # Generate PDF
        html = render_template('paystub_pdf.html',
               paystub=paystub,
               logo_b64=logo_b64,
               logo_path=logo_file_uri or logo_web_path,
               logo_url=logo_url,
               org_name=org_name,
               download_time=datetime.now().strftime('%Y/%m/%d %H:%M:%S'))
        
        pdf_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        HTML(string=html, base_url=request.url_root).write_pdf(pdf_temp.name)
        pdf_temp.close()
        
        with open(pdf_temp.name, 'rb') as f:
            pdf_bytes = f.read()
        
        # Clean up temp file
        os.unlink(pdf_temp.name)
        
        # Prepare email
        filename = f"paystub_{paystub.period_start.strftime('%Y%m%d')}-{paystub.period_end.strftime('%Y%m%d')}_{paystub.employee.firstname}_{paystub.employee.lastname}.pdf"
        body_text = render_template('email/paystub_email.txt', paystub=paystub, org_name=org_name)
        body_html = render_template('email/paystub_email.html', paystub=paystub, org_name=org_name)
        
        # Resolve recipients and honor testing override
        recipients = paystub.employee.email
        try:
            appsettings_obj = settings.get('appsettings')
            if appsettings_obj and getattr(appsettings_obj, 'testing_mode', False) and getattr(appsettings_obj, 'testing_email', None):
                test_addr = appsettings_obj.testing_email
                recipients = test_addr
        except Exception:
            pass
        
        sent = queue_email_with_pdf(recipients=recipients, subject=f"Paystub {paystub.period_start} - {paystub.period_end}", body_text=body_text, body_html=body_html, pdf_bytes=pdf_bytes, filename=filename)
        
        if sent:
            flash('Paystub emailed to employee.', 'success')
        else:
            flash('Failed to enqueue paystub email.', 'warning')
        
    except Exception as e:
        current_app.logger.error(f'Email sending failed: {str(e)}')
        flash('Error sending email. Please try again or contact support.', 'danger')
    
    return redirect(url_for('payroll.list_paystubs'))


@payroll_bp.route('/paystubs/<int:id>/delete', methods=['POST'])
@login_required
def delete_paystub(id):
    # Only admin/super users can delete paystubs
    if not (current_user.is_authenticated and current_user.user_type in ['admin', 'super']):
        flash('Unauthorized. Only administrators can delete paystubs.', 'danger')
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
    if not (current_user.is_authenticated and current_user.user_type in ['admin', 'super']):
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

        # Query sessions within date range, regardless of invoice status
        # Get list of interventions that are already in paystubs
        existing_paystub_sessions = db.session.query(PayStubItem.intervention_id).all()
        existing_session_ids = [id[0] for id in existing_paystub_sessions]

        # Query sessions within date range, excluding those already in paystubs
        sessions = Intervention.query.filter(
            Intervention.employee_id == emp_id,
            Intervention.date >= start,
            Intervention.date <= end,
            ~Intervention.id.in_(existing_session_ids) if existing_session_ids else True
        ).order_by(Intervention.date).all()
        
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
            # Attempt to generate PDF and email to employee
            try:
                paystub = ps
                # Resolve org settings for paystub rendering and email
                settings = get_org_settings()
                html = render_template('paystub_pdf.html', paystub=paystub, org_name=settings['org_name'], logo_b64=settings.get('logo_b64'), logo_url=settings.get('logo_url'), logo_path=(settings.get('logo_file_uri') or settings.get('logo_web_path')), download_time=datetime.now().strftime('%Y/%m/%d %H:%M:%S'))
                pdf_temp = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
                HTML(string=html, base_url=request.url_root).write_pdf(pdf_temp.name)
                pdf_temp.close()
                with open(pdf_temp.name, 'rb') as f:
                    pdf_bytes = f.read()
                
                filename = f"paystub_{paystub.period_start.strftime('%Y%m%d')}-{paystub.period_end.strftime('%Y%m%d')}_{paystub.employee.firstname}_{paystub.employee.lastname}.pdf"
                body_text = render_template('email/paystub_email.txt', paystub=paystub, org_name=settings['org_name'])
                body_html = render_template('email/paystub_email.html', paystub=paystub, org_name=settings['org_name'])
                # Resolve recipients and honor testing override in AppSettings at call site
                recipients = paystub.employee.email
                try:
                    appsettings_obj = settings.get('appsettings')
                    if appsettings_obj and getattr(appsettings_obj, 'testing_mode', False) and getattr(appsettings_obj, 'testing_email', None):
                        recipients = appsettings_obj.testing_email
                except Exception:
                    pass

                sent = queue_email_with_pdf(recipients=recipients, subject=f"Paystub {paystub.period_start} - {paystub.period_end}", body_text=body_text, body_html=body_html, pdf_bytes=pdf_bytes, filename=filename)
                try:
                    os.unlink(pdf_temp.name)
                except Exception:
                    pass
                if sent:
                    flash('Paystub saved and emailed to employee.', 'success')
                else:
                    flash('Paystub saved but failed to email to employee.', 'warning')
            except Exception as e:
                flash(f'Paystub saved but failed to generate/email PDF: {str(e)}', 'warning')
            return redirect(url_for('payroll.list_paystubs'))

        if missing_rates:
            flash('Missing pay rates for some client(s). Please add pay rates before saving.', 'danger')

    return render_template('create_paystub.html', form=form, preview=preview, missing_rates=missing_rates)
