from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import db
from app.payroll.forms import PayPeriodForm, PayRateForm
from app.models import Employee, Intervention, PayRate, PayStub, PayStubItem, Client
from sqlalchemy import extract
from flask_login import login_required, current_user
from datetime import date
from weasyprint import HTML
import tempfile
import os
from flask import send_file

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
    employees = Employee.query.order_by(Employee.firstname, Employee.lastname).all()
    
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
    form.employee.choices = [(str(e.id), f"{e.firstname} {e.lastname}") for e in Employee.query.order_by(Employee.firstname, Employee.lastname).all()]
    form.client.choices = [(str(c.id), f"{c.firstname} {c.lastname}") for c in Client.query.order_by(Client.firstname, Client.lastname).all()]
    
    if form.validate_on_submit():
        payrate = PayRate(
            employee_id=int(form.employee.data),
            client_id=int(form.client.data),
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
    
    form.employee.choices = [(str(e.id), f"{e.firstname} {e.lastname}") for e in Employee.query.order_by(Employee.firstname, Employee.lastname).all()]
    form.client.choices = [(str(c.id), f"{c.firstname} {c.lastname}") for c in Client.query.order_by(Client.firstname, Client.lastname).all()]
    
    if form.validate_on_submit():
        payrate.employee_id = int(form.employee.data)
        payrate.client_id = int(form.client.data)
        payrate.rate = form.rate.data
        payrate.effective_date = form.effective_date.data
        db.session.commit()
        flash('Pay rate updated successfully', 'success')
        return redirect(url_for('payroll.list_payrates'))
    elif request.method == 'GET':
        form.employee.data = str(payrate.employee_id)
        form.client.data = str(payrate.client_id)
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
    if not (current_user.is_authenticated and current_user.user_type == 'admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))
    
    paystub = PayStub.query.get_or_404(id)
    
    # Generate PDF using WeasyPrint
    html = render_template('view_paystub.html', paystub=paystub)
    
    # Create a temporary file for the PDF
    temp_dir = tempfile.mkdtemp()
    pdf_path = os.path.join(temp_dir, f'paystub_{id}.pdf')
    
    # Generate PDF from HTML
    HTML(string=html, base_url=request.url_root).write_pdf(pdf_path)
    
    # Send the PDF file
    return send_file(
        pdf_path,
        as_attachment=True,
        download_name=f'paystub_{paystub.period_start.strftime("%Y%m%d")}_{paystub.employee.lastname}.pdf'
    )


@payroll_bp.route('/paystubs/create', methods=['GET', 'POST'])
@login_required
def create_paystub():
    if not (current_user.is_authenticated and current_user.user_type == 'admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))

    form = PayPeriodForm()
    # populate employee choices
    form.employee.choices = [(str(e.id), f"{e.firstname} {e.lastname}") for e in Employee.query.order_by(Employee.firstname, Employee.lastname).all()]

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
            # find pay rate for employee-client pair (choose latest effective_date <= session.date)
            rate = None
            payrates = PayRate.query.filter_by(employee_id=emp_id, client_id=s.client_id).order_by(PayRate.effective_date.desc()).all()
            if payrates:
                # choose first where effective_date is None or <= s.date
                for pr in payrates:
                    if pr.effective_date is None or pr.effective_date <= s.date:
                        rate = pr.rate
                        break
                if rate is None:
                    rate = payrates[0].rate

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
