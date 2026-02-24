from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from app import db
from app.mileage.forms import MileageRateForm, MileageForm
from app.models import Employee, Client, MileageRate, Mileage
from flask_login import login_required, current_user
from datetime import date, datetime


mileage_bp = Blueprint('mileage', __name__, template_folder='templates')


@mileage_bp.route('/mileage-rates')
@login_required
def list_mileage_rates():
    """Display all mileage rates"""
    if not (current_user.is_authenticated and current_user.user_type in ['admin', 'super']):
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    pagination = MileageRate.query.order_by(MileageRate.effective_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    rates = pagination.items
    
    return render_template('list_mileage_rates.html', rates=rates, pagination=pagination, per_page=per_page)


@mileage_bp.route('/mileage-rates/add', methods=['GET', 'POST'])
@login_required
def add_mileage_rate():
    """Add a new mileage rate"""
    if not (current_user.is_authenticated and current_user.user_type in ['admin', 'super']):
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))
    
    
    form = MileageRateForm()
    
    if form.validate_on_submit():
        # Check if a rate already exists for this date
        existing_rate = MileageRate.query.filter_by(effective_date=form.effective_date.data).first()
        if existing_rate:
            flash(f'A mileage rate already exists for {form.effective_date.data.strftime("%B %d, %Y")}. Please update it instead.', 'warning')
        else:
            rate = MileageRate(
                rate=float(form.rate.data),
                effective_date=form.effective_date.data
            )
            db.session.add(rate)
            db.session.commit()
            flash(f'Mileage rate ${form.rate.data:.4f}/mile added successfully for {form.effective_date.data.strftime("%B %d, %Y")}', 'success')
            return redirect(url_for('mileage.list_mileage_rates'))
    
    return render_template('add_mileage_rate.html', form=form)


@mileage_bp.route('/mileage-rates/edit/<int:rate_id>', methods=['GET', 'POST'])
@login_required
def edit_mileage_rate(rate_id):
    """Edit an existing mileage rate"""
    if not (current_user.is_authenticated and current_user.user_type in ['admin', 'super']):
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))
    
    rate = MileageRate.query.get_or_404(rate_id)
    form = MileageRateForm()
    
    if form.validate_on_submit():
        # Check if another rate exists for this date
        existing_rate = MileageRate.query.filter(
            MileageRate.effective_date == form.effective_date.data,
            MileageRate.id != rate_id
        ).first()
        
        if existing_rate:
            flash(f'A mileage rate already exists for {form.effective_date.data.strftime("%B %d, %Y")}', 'warning')
        else:
            rate.rate = float(form.rate.data)
            rate.effective_date = form.effective_date.data
            db.session.commit()
            flash(f'Mileage rate updated successfully to ${form.rate.data:.4f}/mile', 'success')
            return redirect(url_for('mileage.list_mileage_rates'))
    
    elif request.method == 'GET':
        form.rate.data = rate.rate
        form.effective_date.data = rate.effective_date
    
    return render_template('edit_mileage_rate.html', form=form, rate=rate)


@mileage_bp.route('/mileage-rates/delete/<int:rate_id>', methods=['POST'])
@login_required
def delete_mileage_rate(rate_id):
    """Delete a mileage rate"""
    if not (current_user.is_authenticated and current_user.user_type in ['admin', 'super']):
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    rate = MileageRate.query.get_or_404(rate_id)
    
    # Check if any mileage entries use this rate
    count = Mileage.query.filter_by(mileage_rate_id=rate_id).count()
    if count > 0:
        return jsonify({'success': False, 'message': f'Cannot delete - {count} mileage entries use this rate'}), 400
    
    db.session.delete(rate)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Mileage rate deleted successfully'})


@mileage_bp.route('/mileages')
@login_required
def list_mileages():
    """Display all mileage entries"""
    # Admins and supers can view all entries; other authenticated users see their own
    if not current_user.is_authenticated:
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))
    
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    employee_id = request.args.get('employee', type=int)
    client_id = request.args.get('client', type=int)
    invoiced = request.args.get('invoiced', type=str)  # 'yes', 'no', or empty
    
    query = Mileage.query

    # Admins and top-level super can view all; supervisors can view mileages for clients they supervise;
    # other users (therapists) can view only their own mileage records.
    if current_user.user_type in ['admin', 'super']:
        if employee_id:
            query = query.filter_by(employee_id=employee_id)
    elif current_user.user_type == 'supervisor':
        # Supervisors see mileages for clients they supervise; optionally filter by employee
        if employee_id:
            query = query.filter_by(employee_id=employee_id).filter(Mileage.client.has(supervisor_id=current_user.id))
        else:
            query = query.filter(Mileage.client.has(supervisor_id=current_user.id))
    else:
        # assume current_user.id corresponds to Employee.id
        query = query.filter_by(employee_id=current_user.id)
    
    if client_id:
        query = query.filter_by(client_id=client_id)
    
    if invoiced == 'yes':
        query = query.filter_by(invoiced=True)
    elif invoiced == 'no':
        query = query.filter_by(invoiced=False)
    
    pagination = query.order_by(Mileage.date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    mileages = pagination.items
    
    # Get filter options
    employees = Employee.query.filter_by(is_active=True).order_by(Employee.firstname, Employee.lastname).all()
    clients = Client.query.filter_by(is_active=True).order_by(Client.firstname, Client.lastname).all()
    
    return render_template(
        'list_mileages.html',
        mileages=mileages,
        employees=employees,
        clients=clients,
        pagination=pagination,
        per_page=per_page,
        selected_employee=employee_id,
        selected_client=client_id,
        selected_invoiced=invoiced
    )


@mileage_bp.route('/mileages/add', methods=['GET', 'POST'])
@login_required
def add_mileage():
    """Add a new mileage entry or entries"""
    if not current_user.is_authenticated:
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))
    
    form = MileageForm()
    # Admins and supervisors can choose any employee (supervisors act on behalf of clients);
    # therapists are limited to themselves
    if current_user.user_type in ['admin', 'super', 'supervisor']:
        form.employee.choices = [(str(e.id), f"{e.firstname} {e.lastname}") for e in Employee.query.filter_by(is_active=True).order_by(Employee.firstname, Employee.lastname).all()]
    else:
        # limit to current user
        form.employee.choices = [(str(current_user.id), f"{current_user.firstname} {current_user.lastname}")]
        form.employee.data = str(current_user.id)

    # Client choices: admins see all; supervisors see only their supervised clients; others see all clients
    if current_user.user_type in ['admin', 'super']:
        client_q = Client.query.filter_by(is_active=True)
    elif current_user.user_type == 'supervisor':
        client_q = Client.query.filter_by(is_active=True, supervisor_id=current_user.id)
    else:
        client_q = Client.query.filter_by(is_active=True)

    form.client.choices = [(str(c.id), f"{c.firstname} {c.lastname}") for c in client_q.order_by(Client.firstname, Client.lastname).all()]
    
    if request.method == 'POST':
        # Check if this is a bulk submission from dynamic rows (mileage_row_count in form data)
        mileage_row_count = request.form.get('mileage_row_count')
        
        if mileage_row_count:
            # Bulk submission from dynamic table
            try:
                row_count = int(mileage_row_count)
                created_count = 0
                errors = []
                
                for i in range(row_count):
                    date_str = request.form.get(f'date_{i}')
                    distance_str = request.form.get(f'distance_{i}')
                    employee_id_str = request.form.get(f'employee_{i}')
                    client_id_str = request.form.get(f'client_{i}')
                    description = request.form.get(f'description_{i}') or None
                    
                    # Skip empty rows
                    if not date_str or not distance_str:
                        continue
                    
                    try:
                        # Parse date (expect YYYY-MM-DD format from datepicker)
                        mileage_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                        distance = float(distance_str)
                        employee_id = int(employee_id_str)
                        client_id = int(client_id_str)
                        
                        # Get the effective mileage rate for this date
                        rate = Mileage.get_effective_rate(mileage_date)
                        if not rate:
                            errors.append(f"Row {i+1}: No mileage rate configured for {mileage_date}")
                            continue
                        
                        # Check permissions: supervisors can only add for their supervised clients
                        if current_user.user_type == 'supervisor':
                            client = Client.query.get(client_id)
                            if not client or client.supervisor_id != current_user.id:
                                errors.append(f"Row {i+1}: You can only add mileage for clients you supervise")
                                continue
                        
                        mileage = Mileage(
                            employee_id=employee_id,
                            client_id=client_id,
                            date=mileage_date,
                            distance=distance,
                            mileage_rate_id=rate.id,
                            description=description
                        )
                        
                        db.session.add(mileage)
                        created_count += 1
                    
                    except (ValueError, TypeError) as e:
                        errors.append(f"Row {i+1}: {str(e)}")
                        continue
                
                db.session.commit()
                
                if created_count > 0:
                    flash(f'Successfully added {created_count} mileage entry/entries', 'success')
                
                if errors:
                    for error in errors:
                        flash(error, 'warning')
                
                if created_count > 0:
                    return redirect(url_for('mileage.list_mileages'))
            
            except Exception as e:
                db.session.rollback()
                flash(f'Error processing bulk submission: {str(e)}', 'danger')
        
        elif form.validate_on_submit():
            # Standard single form submission
            # Get the effective mileage rate for the date
            rate = Mileage.get_effective_rate(form.date.data)
            
            if not rate:
                flash('No mileage rate is configured for this date. Please set up a mileage rate first.', 'danger')
                return redirect(url_for('mileage.add_mileage'))
            
            mileage = Mileage(
                employee_id=int(form.employee.data),
                client_id=int(form.client.data),
                date=form.date.data,
                distance=float(form.distance.data),
                mileage_rate_id=rate.id,
                description=form.description.data if form.description.data else None
            )
            
            db.session.add(mileage)
            db.session.commit()
            
            flash(f'Mileage entry added: {form.distance.data} km @ ${rate.rate:.4f}/km = ${mileage.cost:.2f}', 'success')
            return redirect(url_for('mileage.list_mileages'))
    
    return render_template('add_mileage.html', form=form)


@mileage_bp.route('/mileages/edit/<int:mileage_id>', methods=['GET', 'POST'])
@login_required
def edit_mileage(mileage_id):
    """Edit an existing mileage entry"""
    if not current_user.is_authenticated:
        flash('Unauthorized', 'danger')
        return redirect(url_for('home'))
    
    mileage = Mileage.query.get_or_404(mileage_id)

    # Non-admin users may only edit their own non-invoiced mileage, supervisors may edit mileages
    # for clients they supervise
    if current_user.user_type in ['admin', 'super']:
        pass
    elif current_user.user_type == 'supervisor':
        if mileage.client and mileage.client.supervisor_id != current_user.id:
            flash('Unauthorized', 'danger')
            return redirect(url_for('mileage.list_mileages'))
    else:
        if mileage.employee_id != current_user.id:
            flash('Unauthorized', 'danger')
            return redirect(url_for('mileage.list_mileages'))

    if mileage.invoiced:
        flash('Cannot edit a mileage entry that has already been invoiced', 'warning')
        return redirect(url_for('mileage.list_mileages'))
    
    form = MileageForm()
    if current_user.user_type in ['admin', 'super', 'supervisor']:
        form.employee.choices = [(str(e.id), f"{e.firstname} {e.lastname}") for e in Employee.query.filter_by(is_active=True).order_by(Employee.firstname, Employee.lastname).all()]
    else:
        form.employee.choices = [(str(current_user.id), f"{current_user.firstname} {current_user.lastname}")]

    # Client choices: supervisors limited to their clients
    if current_user.user_type in ['admin', 'super']:
        client_q = Client.query.filter_by(is_active=True)
    elif current_user.user_type == 'supervisor':
        client_q = Client.query.filter_by(is_active=True, supervisor_id=current_user.id)
    else:
        client_q = Client.query.filter_by(is_active=True)

    form.client.choices = [(str(c.id), f"{c.firstname} {c.lastname}") for c in client_q.order_by(Client.firstname, Client.lastname).all()]
    
    if form.validate_on_submit():
        # Get the effective mileage rate for the new date
        rate = Mileage.get_effective_rate(form.date.data)
        
        if not rate:
            flash('No mileage rate is configured for this date.', 'danger')
            return redirect(url_for('mileage.edit_mileage', mileage_id=mileage_id))
        
        mileage.employee_id = int(form.employee.data)
        mileage.client_id = int(form.client.data)
        mileage.date = form.date.data
        mileage.distance = float(form.distance.data)
        mileage.mileage_rate_id = rate.id
        mileage.description = form.description.data if form.description.data else None
        # Recalculate cost
        mileage.cost = round(mileage.distance * rate.rate, 2)
        
        db.session.commit()
        
        flash(f'Mileage entry updated: {form.distance.data} km @ ${rate.rate:.4f}/km = ${mileage.cost:.2f}', 'success')
        return redirect(url_for('mileage.list_mileages'))
    
    elif request.method == 'GET':
        form.employee.data = str(mileage.employee_id)
        form.client.data = str(mileage.client_id)
        form.date.data = mileage.date
        form.distance.data = mileage.distance
        form.description.data = mileage.description
    
    return render_template('edit_mileage.html', form=form, mileage=mileage)


@mileage_bp.route('/mileages/delete/<int:mileage_id>', methods=['POST'])
@login_required
def delete_mileage(mileage_id):
    """Delete a mileage entry"""
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    mileage = Mileage.query.get_or_404(mileage_id)
    
    # Non-admins can only delete their own non-invoiced entries; supervisors can delete entries for their supervised clients
    if current_user.user_type in ['admin', 'super']:
        pass
    elif current_user.user_type == 'supervisor':
        if not (mileage.client and mileage.client.supervisor_id == current_user.id):
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    else:
        if mileage.employee_id != current_user.id:
            return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    if mileage.invoiced:
        return jsonify({'success': False, 'message': 'Cannot delete - this mileage entry has been invoiced'}), 400
    
    db.session.delete(mileage)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Mileage entry deleted successfully'})
