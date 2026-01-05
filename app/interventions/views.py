from flask import Blueprint, render_template, redirect, url_for, request, abort, flash, send_from_directory
from app import db, app, allowed_file
from app.models import Intervention, Client, Employee, Activity, PayStubItem
from app.interventions.forms import AddInterventionForm, UpdateInterventionForm
from flask_login import login_required, current_user
import os
from app.utils.settings_utils import get_org_settings
import json
from werkzeug.utils import secure_filename
import shutil
from datetime import datetime
import csv
import io


interventions_bp = Blueprint('interventions', __name__, template_folder='templates')
# org values resolved per-request via get_org_settings()


# client_id is a foreign key to the Client model
# employee_id is a foreign key to the Employee model
@interventions_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_intervention():
    # Allow admin, therapists and supervisors (but not 'super' system user) to add interventions
    if current_user.is_authenticated:
        # find employee record for current user (if any)
        emp = Employee.query.filter_by(email=current_user.email).first()

        # Ensure there are clients in the system
        clients = Client.query.filter_by(is_active=True).all()
        if not clients:
            flash('Warning: No active client records found.', 'warning')
            return redirect(url_for('interventions.list_interventions'))

        form = AddInterventionForm()
        # Pre-fill date if provided in query
        if request.args.get('date'):
            try:
                form.date.data = datetime.strptime(request.args.get('date'), '%Y-%m-%d').date()
            except ValueError:
                pass  # Ignore invalid date
        # Supervisor should only be able to pick from their supervised clients
        if current_user.user_type == 'supervisor' and emp:
            form.client_id.choices = [(c.id, f"{c.firstname} {c.lastname}") for c in Client.query.filter_by(supervisor_id=emp.id, is_active=True).all()]
        else:
            form.client_id.choices = [(c.id, f"{c.firstname} {c.lastname}") for c in Client.query.filter_by(is_active=True).all()]

        # Employee selection:
        if current_user.user_type in ["admin", "super"]:
            # Exclude Administrators (position) from the employee selection
            form.employee_id.choices = [(e.id, f"{e.firstname} {e.lastname}") 
                                      for e in Employee.query.filter(
                                          Employee.is_active==True,
                                          Employee.position!='Administrator'
                                      ).all()]
        elif current_user.user_type == 'supervisor':
            # supervisors can choose therapists, senior therapists, and themselves (position)
            current_employee = Employee.query.filter_by(email=current_user.email, is_active=True).first()
            employees = Employee.query.filter(
                (Employee.position.in_(['Therapist', 'Senior Therapist']) & Employee.is_active==True) |
                (Employee.id == current_employee.id if current_employee else False)
            ).all()
            form.employee_id.choices = [(e.id, f"{e.firstname} {e.lastname}") for e in employees]
        else:
            # therapists can only create sessions for themselves
            form.employee_id.choices = [(e.id, f"{e.firstname} {e.lastname}") for e in Employee.query.filter_by(email=current_user.email, is_active=True).all()]

        # Filter activities based on selected employee's position
        if 'employee_id' in request.form:
            selected_employee = Employee.query.get(request.form['employee_id'])
            if selected_employee:
                if selected_employee.position == 'Behaviour Analyst':
                    activities = Activity.query.filter_by(activity_category='Supervision').all()
                else:  # Therapist or Senior Therapist
                    activities = Activity.query.filter_by(activity_category='Therapy').all()
                form.intervention_type.choices = [(a.activity_name, a.activity_name) for a in activities]
        else:
            # No employee selected yet, show all activities
            form.intervention_type.choices = []

        if form.validate_on_submit():
            # Check for overlapping sessions first
            if not form.validate_session_time():
                settings = get_org_settings()
                return render_template('add_int.html', form=form, org_name=settings['org_name'])

            try:
                client_id = form.client_id.data
                client_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(client_id))
                filenames = []
                
                try:
                    # Create upload directory
                    os.makedirs(client_folder, exist_ok=True)
                except OSError as e:
                    flash('Error creating upload directory: ' + str(e), 'error')
                    return render_template('add_int.html', form=form, org_name=org_name)

                # Handle file uploads
                for file_storage in request.files.getlist(form.file_names.name):
                    if file_storage and file_storage.filename:
                        if allowed_file(file_storage.filename):
                            try:
                                filename = secure_filename(file_storage.filename)
                                file_path = os.path.join(client_folder, filename)
                                file_storage.save(file_path)
                                filenames.append(filename)
                                flash(f"File added: {file_storage.filename}", "success")
                            except Exception as e:
                                flash(f'Error uploading file {file_storage.filename}: {str(e)}', 'error')
                                continue
                        else:
                            flash(f"File type not allowed: {file_storage.filename}", "danger")
                
                # Create and save new intervention
                new_intervention = Intervention(
                    client_id=client_id,
                    employee_id=form.employee_id.data,
                    intervention_type=form.intervention_type.data,
                    date=form.date.data,
                    start_time=form.start_time.data,
                    end_time=form.end_time.data,
                    duration=round(float(form.duration.data), 2),
                    file_names=json.dumps(filenames)  # Save as JSON string
                )
                
                db.session.add(new_intervention)
                db.session.commit()
                flash('Intervention added successfully!', 'success')
                return redirect(url_for('interventions.list_interventions'))

            except Exception as e:
                db.session.rollback()
                flash('Error adding intervention: ' + str(e), 'error')
                settings = get_org_settings()
                return render_template('add_int.html', form=form, org_name=settings['org_name'])
            
        settings = get_org_settings()
        return render_template('add_int.html', form=form, org_name=settings['org_name'])
    else:
        abort(403)


@interventions_bp.route('/list', methods=['GET'])
@login_required
def list_interventions():
    if current_user.is_authenticated:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Apply filters BEFORE paginating
        invoiced_filter = request.args.get('invoiced')

        # Build a subquery that selects distinct Intervention IDs after applying all filters
        id_subq = db.session.query(Intervention.id).join(Employee, Intervention.employee_id == Employee.id).join(Client, Intervention.client_id == Client.id)

        # Role-based visibility filters applied to the subquery
        if current_user.user_type == "therapist":
            id_subq = id_subq.filter(Employee.email == current_user.email)
        elif current_user.user_type == 'supervisor':
            emp = Employee.query.filter_by(email=current_user.email).first()
            if emp:
                view_type = request.args.get('view_type', 'all')
                if view_type == 'own':
                    # Show only supervisor's own sessions
                    id_subq = id_subq.filter(Employee.email == current_user.email)
                else:
                    # Show all sessions for supervised clients (default)
                    id_subq = id_subq.filter(Client.supervisor_id == emp.id)  # This will include all sessions for supervised clients

        # invoiced filter
        if invoiced_filter == 'yes':
            id_subq = id_subq.filter(Intervention.invoiced == True)
        elif invoiced_filter == 'no':
            id_subq = id_subq.filter(Intervention.invoiced == False)

        # client name filter
        client = request.args.get('client')
        if client:
            id_subq = id_subq.filter(
                (Client.firstname.ilike(f"%{client}%")) |
                (Client.lastname.ilike(f"%{client}%"))
            )

        # date range filters
        date_from = request.args.get('date_from', '')
        if date_from:
            id_subq = id_subq.filter(Intervention.date >= date_from)

        date_to = request.args.get('date_to', '')
        if date_to:
            id_subq = id_subq.filter(Intervention.date <= date_to)

        # intervention type
        intervention_type = request.args.get('intervention_type', '')
        if intervention_type:
            id_subq = id_subq.filter(Intervention.intervention_type == intervention_type)

        # finalize subquery: distinct ids
        id_subq = id_subq.distinct(Intervention.id).subquery()

        # Main query: retrieve Intervention objects for the filtered ids and order them
        main_query = Intervention.query.filter(Intervention.id.in_(id_subq)).order_by(Intervention.date.desc(), Intervention.start_time.desc(), Intervention.end_time.asc())

        # Paginate the main query
        pagination = main_query.paginate(page=page, per_page=per_page, error_out=False)

        activities = Activity.query.order_by(Activity.activity_name).all()

        settings = get_org_settings()
        return render_template(
            'list_int.html',
            interventions=pagination.items,
            pagination=pagination,
            per_page=per_page,
            activities=activities,
            org_name=settings['org_name']
        )
    else:
        abort(403)


import os
import shutil
import json

@interventions_bp.route('/bulk_delete', methods=['POST'])
@login_required
def bulk_delete():
    if current_user.is_authenticated:
        ids = request.form.getlist('selected_ids')
        if ids:
            interventions = Intervention.query.filter(Intervention.id.in_(ids)).all()
            to_delete = []
            skipped = []
            for intervention in interventions:
                # Check for invoice and payment status
                if intervention.invoiced or intervention.is_paid:
                    skipped.append(intervention)
                    continue
                
                # Check for PayStubItem association
                pay_stub_item = PayStubItem.query.filter_by(intervention_id=intervention.id).first()
                if pay_stub_item:
                    skipped.append(intervention)
                    flash(f'Session {intervention.id} has associated pay stub entries and cannot be deleted.', 'danger')
                    continue
                
                to_delete.append(intervention)

            if to_delete:
                try:
                    for intervention in to_delete:
                        client_id = intervention.client_id
                        client_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(client_id))
                        deleted_folder = os.path.join(app.config['DELETE_FOLDER'], str(client_id))
                        os.makedirs(deleted_folder, exist_ok=True)
                        
                        # Move associated files to deleted folder
                        filenames = intervention.get_file_names()
                        for filename in filenames:
                            src = os.path.join(client_folder, filename)
                            dst = os.path.join(deleted_folder, filename)
                            if os.path.exists(src):
                                shutil.move(src, dst)
                                
                        db.session.delete(intervention)
                    
                    db.session.commit()
                    flash(f"Successfully deleted {len(to_delete)} session(s).", "success")
                except Exception as e:
                    db.session.rollback()
                    flash('Error occurred while deleting sessions. Please try again.', 'danger')
                    return redirect(url_for('interventions.list_interventions'))

            if skipped:
                # Inform the user which sessions were not deleted
                flash(f"{len(skipped)} selected session(s) were not deleted due to dependencies (invoiced, paid, or in pay stubs).", "warning")
                
        return redirect(url_for('interventions.list_interventions'))
    else:
        abort(403)


@interventions_bp.route('/update/<int:intervention_id>', methods=['GET', 'POST'])
@login_required
def update_intervention(intervention_id):
    if current_user.is_authenticated:
        intervention = Intervention.query.get_or_404(intervention_id)

        # enforce edit permissions for therapists and supervisors
        if current_user.user_type == 'therapist':
            if not intervention.employee or intervention.employee.email != current_user.email:
                abort(403)
        if current_user.user_type == 'supervisor':
            emp = Employee.query.filter_by(email=current_user.email).first()
            if not emp or (not intervention.client or intervention.client.supervisor_id != emp.id):
                abort(403)

        # Disallow editing if the session is invoiced or already paid
        if intervention.invoiced or intervention.is_paid:
            flash('This session cannot be edited because it is either invoiced or already paid.', 'warning')
            return redirect(url_for('interventions.list_interventions'))

        # Pass intervention_id to the form so validators (like overlap check) have access
        form = UpdateInterventionForm(obj=intervention, intervention_id=intervention_id)
        # Include the current client and employee in choices even if inactive
        client_choices = [(c.id, f"{c.firstname} {c.lastname}") for c in Client.query.filter_by(is_active=True).all()]
        if intervention.client_id:
            client_choices.extend([(c.id, f"{c.firstname} {c.lastname} (Inactive)") 
                                 for c in Client.query.filter_by(id=intervention.client_id, is_active=False).all()])
        form.client_id.choices = client_choices

        if current_user.user_type in ["admin", "super"]:
            # Exclude super users from the employee selection
            emp_choices = [(e.id, f"{e.firstname} {e.lastname}") 
                          for e in Employee.query.filter(
                              Employee.is_active==True,
                              Employee.position!='Administrator'
                          ).all()]
            if intervention.employee_id:
                emp_choices.extend([(e.id, f"{e.firstname} {e.lastname} (Inactive)")
                                  for e in Employee.query.filter(
                                      Employee.id==intervention.employee_id,
                                      Employee.is_active==False,
                                      Employee.user_type!='super'
                                  ).all()])
            form.employee_id.choices = emp_choices
        elif current_user.user_type == 'supervisor':
            # supervisors can reassign to therapists, senior therapists, and themselves
            current_employee = Employee.query.filter_by(email=current_user.email, is_active=True).first()
            employees = Employee.query.filter(
                (Employee.position.in_(['Therapist', 'Senior Therapist']) & Employee.is_active==True) |
                (Employee.id == current_employee.id if current_employee else False)
            ).all()
            form.employee_id.choices = [(e.id, f"{e.firstname} {e.lastname}") for e in employees]
            # Include the current intervention's employee if inactive
            if intervention.employee_id:
                form.employee_id.choices.extend([(e.id, f"{e.firstname} {e.lastname} (Inactive)") 
                                              for e in Employee.query.filter_by(id=intervention.employee_id, is_active=False).all()])
        else:
            form.employee_id.choices = [(e.id, f"{e.firstname} {e.lastname}") 
                                      for e in Employee.query.filter_by(email=current_user.email, is_active=True).all()]

        # Filter activities based on selected employee's position
        if request.method == 'GET':
            selected_employee = intervention.employee
        else:
            selected_employee = Employee.query.get(request.form['employee_id']) if 'employee_id' in request.form else None

        if selected_employee:
            if selected_employee.position == 'Behaviour Analyst':
                activities = Activity.query.filter_by(activity_category='Supervision').all()
            else:  # Therapist or Senior Therapist
                activities = Activity.query.filter_by(activity_category='Therapy').all()
            form.intervention_type.choices = [(a.activity_name, a.activity_name) for a in activities]
        else:
            form.intervention_type.choices = []

        # Handle POST submission
        if request.method == 'POST' and form.validate():
            # Check for overlapping sessions first
            if not form.validate_session_time():
                settings = get_org_settings()
                return render_template('update_int.html', form=form, 
                                    clients=Client.query.all(), 
                                    employees=Employee.query.all(), 
                                    org_name=settings['org_name'],
                                    intervention=intervention)
            try:
                client_id = form.client_id.data
                client_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(client_id))
                deleted_folder = os.path.join(app.config['DELETE_FOLDER'], str(client_id))
                os.makedirs(client_folder, exist_ok=True)
                os.makedirs(deleted_folder, exist_ok=True)
            except OSError as e:
                flash('Error creating directories: ' + str(e), 'error')
                settings = get_org_settings()
                return render_template('update_int.html', form=form,
                                    clients=Client.query.all(),
                                    employees=Employee.query.all(),
                                    org_name=settings['org_name'],
                                    intervention=intervention)

            try:
                filenames = intervention.get_file_names()
                remove_files = request.form.getlist('remove_files')
                # Move removed files to deleted folder
                for filename in remove_files:
                    try:
                        src = os.path.join(client_folder, filename)
                        dst = os.path.join(deleted_folder, filename)
                        if os.path.exists(src):
                            shutil.move(src, dst)
                    except OSError as e:
                        flash(f'Error moving file {filename}: {str(e)}', 'warning')
                        continue

                # Remove from filenames list
                filenames = [f for f in filenames if f not in remove_files]

                # Handle new uploads
                for file_storage in request.files.getlist(form.file_names.name):
                    if file_storage and file_storage.filename:
                        if allowed_file(file_storage.filename):
                            try:
                                filename = secure_filename(file_storage.filename)
                                file_path = os.path.join(client_folder, filename)
                                file_storage.save(file_path)
                                filenames.append(filename)
                                flash(f"File added: {file_storage.filename}", "success")
                            except Exception as e:
                                flash(f'Error uploading file {file_storage.filename}: {str(e)}', 'error')
                                continue
                        else:
                            flash(f"File type not allowed: {file_storage.filename}", "danger")

                # Update intervention
                intervention.client_id = client_id
                intervention.employee_id = form.employee_id.data
                intervention.intervention_type = form.intervention_type.data
                intervention.date = form.date.data
                intervention.start_time = form.start_time.data
                intervention.end_time = form.end_time.data
                intervention.duration = round(float(form.duration.data), 2)
                intervention.invoiced = form.invoiced.data
                intervention.invoice_number = form.invoice_number.data
                intervention.file_names = json.dumps(filenames)

                try:
                    db.session.commit()
                    flash('Intervention updated successfully!', 'success')
                    return redirect(url_for('interventions.list_interventions'))
                except Exception as e:
                    db.session.rollback()
                    flash('Database error: ' + str(e), 'error')
                    settings = get_org_settings()
                    return render_template('update_int.html', form=form,
                                        clients=Client.query.all(),
                                        employees=Employee.query.all(),
                                        org_name=settings['org_name'],
                                        intervention=intervention)

            except Exception as e:
                db.session.rollback()
                flash('Unexpected error: ' + str(e), 'error')
                return render_template('update_int.html', form=form,
                                    clients=Client.query.all(),
                                    employees=Employee.query.all(),
                                    org_name=org_name,
                                    intervention=intervention)
        # If POST but validation failed, surface the form errors to the user
        if request.method == 'POST' and not form.validate():
            for field_name, field_errors in form.errors.items():
                field = getattr(form, field_name, None)
                label = getattr(field, 'label', None)
                label_text = label.text if label else field_name
                for err in field_errors:
                    flash(f"{label_text}: {err}", 'danger')

        settings = get_org_settings()
        return render_template('update_int.html', form=form, clients=Client.query.all(), employees=Employee.query.all(), org_name=settings['org_name'], intervention=intervention)
    else:
        abort(403)


@interventions_bp.route('/calendar')
@login_required
def calendar_view():
    # Allow viewing calendar for authorized users
    if not current_user.is_authenticated:
        abort(403)
    
    # Get filter parameters
    view_type = request.args.get('view_type', 'client')  # 'client' or 'employee'
    entity_id = request.args.get('entity_id', type=int)
    view_mode = request.args.get('view', 'month')  # 'month' or 'week'
    
    # Get available clients and employees for dropdowns
    clients = []
    employees = []
    
    if current_user.user_type in ['admin', 'super']:
        clients = Client.query.filter_by(is_active=True).all()
        employees = Employee.query.filter(Employee.is_active==True, Employee.position!='Administrator').all()
    elif current_user.user_type == 'supervisor':
        emp = Employee.query.filter_by(email=current_user.email).first()
        if emp:
            clients = Client.query.filter_by(supervisor_id=emp.id, is_active=True).all()
            # Supervisors can see their own sessions and sessions of their supervised clients
            employees = Employee.query.filter(
                db.or_(
                    Employee.id == emp.id,
                    Employee.id.in_([c.supervisor_id for c in clients if c.supervisor_id])
                ),
                Employee.is_active==True
            ).all()
    elif current_user.user_type == 'therapist':
        emp = Employee.query.filter_by(email=current_user.email).first()
        if emp:
            # Therapists can only see their own calendar
            employees = [emp]
            clients = Client.query.filter_by(is_active=True).all()
    
    settings = get_org_settings()
    return render_template('calendar.html', 
                         clients=clients, 
                         employees=employees, 
                         view_type=view_type,
                         entity_id=entity_id,
                         view_mode=view_mode,
                         org_name=settings['org_name'])


@interventions_bp.route('/api/calendar_events')
@login_required
def calendar_events():
    # API endpoint to get calendar events in JSON format
    if not current_user.is_authenticated:
        abort(403)
    
    # Get parameters
    start = request.args.get('start')
    end = request.args.get('end')
    view_type = request.args.get('view_type', 'client')
    entity_id = request.args.get('entity_id', type=int)
    
    if not entity_id:
        return app.response_class(
            response=json.dumps([]),
            status=200,
            mimetype='application/json'
        )
    
    # Build query based on view_type
    query = Intervention.query.join(Client).join(Employee)
    
    if view_type == 'client':
        query = query.filter(Intervention.client_id == entity_id)
    elif view_type == 'employee':
        query = query.filter(Intervention.employee_id == entity_id)
    
    # Apply role-based filters
    if current_user.user_type == 'therapist':
        emp = Employee.query.filter_by(email=current_user.email).first()
        if emp:
            query = query.filter(Intervention.employee_id == emp.id)
    elif current_user.user_type == 'supervisor':
        emp = Employee.query.filter_by(email=current_user.email).first()
        if emp:
            if view_type == 'client':
                query = query.filter(Client.supervisor_id == emp.id)
            else:
                # For employee view, allow viewing own and supervised employees
                supervised_client_ids = [c.id for c in Client.query.filter_by(supervisor_id=emp.id).all()]
                query = query.filter(
                    db.or_(
                        Intervention.employee_id == emp.id,
                        Intervention.client_id.in_(supervised_client_ids)
                    )
                )
    
    # Filter by date range if provided
    if start:
        query = query.filter(Intervention.date >= start)
    if end:
        query = query.filter(Intervention.date < end)
    
    interventions = query.all()
    
    # Convert to calendar events
    events = []
    for intv in interventions:
        # Combine date and time for start/end
        start_datetime = f"{intv.date}T{intv.start_time}"
        end_datetime = f"{intv.date}T{intv.end_time}"
        
        # Format times for display
        start_time_formatted = intv.start_time.strftime('%I:%M %p').lstrip('0')
        end_time_formatted = intv.end_time.strftime('%I:%M %p').lstrip('0')
        time_range = f"{start_time_formatted} - {end_time_formatted}"
        
        # Create title with time on first line, details on second line
        if view_type == 'client':
            details = f"{intv.employee.firstname} {intv.employee.lastname} - {intv.intervention_type}"
        else:  # employee view
            details = f"{intv.client.firstname} {intv.client.lastname} - {intv.intervention_type}"
        
        title = f"{time_range}<br>{details}"
        
        # Determine color based on invoice status
        if intv.invoice:
            inv_status = intv.invoice.status
            if inv_status == 'Draft':
                bg_color = '#0dcaf0'  # Bootstrap info color
                class_name = 'invoice-draft'
            elif inv_status == 'Sent':
                bg_color = '#ffc107'  # Bootstrap warning color
                class_name = 'invoice-sent'
            elif inv_status == 'Paid':
                bg_color = '#198754'  # Bootstrap success color
                class_name = 'invoice-paid'
            else:
                bg_color = '#6c757d'  # Bootstrap secondary color
                class_name = 'invoice-other'
        else:
            bg_color = '#6c757d'  # Bootstrap secondary color for not invoiced
            class_name = 'not-invoiced'
        
        events.append({
            'id': intv.id,
            'title': title,
            'start': start_datetime,
            'end': end_datetime,
            'backgroundColor': bg_color,
            'borderColor': bg_color,
            'textColor': '#ffffff',
            'className': class_name,
            'extendedProps': {
                'client': f"{intv.client.firstname} {intv.client.lastname}",
                'employee': f"{intv.employee.firstname} {intv.employee.lastname}",
                'type': intv.intervention_type,
                'duration': intv.duration,
                'invoiced': intv.invoiced
            }
        })
    
    return app.response_class(
        response=json.dumps(events),
        status=200,
        mimetype='application/json'
    )


@interventions_bp.route('/get_activities/<int:employee_id>')
@login_required
def get_activities(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    activities = []
    
    if employee.position == 'Behaviour Analyst':
        activities = Activity.query.filter_by(activity_category='Supervision').all()
    else:  # Therapist or Senior Therapist
        activities = Activity.query.filter_by(activity_category='Therapy').all()
    
    return app.response_class(
        response=json.dumps([{'name': a.activity_name, 'id': a.activity_name} for a in activities]),
        status=200,
        mimetype='application/json'
    )

@interventions_bp.route('/download/<int:client_id>/<filename>')
@login_required
def get_file(client_id, filename):
    client_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(client_id))
    return send_from_directory(client_folder, filename, as_attachment=True)


@interventions_bp.route('/download_template')
@login_required
def download_template():
    # Create CSV template
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Client Name', 'Employee Name', 'Intervention Type', 'Date', 'Start Time', 'End Time'])
    # Add a sample row
    writer.writerow(['John Doe', 'Jane Smith', 'Therapy', '2023-10-01', '09:00', '10:00'])
    
    output.seek(0)
    return app.response_class(
        output.getvalue(),
        mimetype='text/csv',
        headers={'Content-Disposition': 'attachment; filename=intervention_template.csv'}
    )


@interventions_bp.route('/bulk_upload', methods=['POST'])
@login_required
def bulk_upload():
    if current_user.is_authenticated:
        # Check permissions - only admin, super, or supervisors can bulk upload
        if current_user.user_type not in ['admin', 'super', 'supervisor']:
            flash('You do not have permission to perform bulk uploads.', 'danger')
            return redirect(url_for('interventions.list_interventions'))
        
        file = request.files.get('bulk_file')
        skip_errors = request.form.get('skip_errors') == 'on'
        
        if not file or file.filename == '':
            flash('No file selected.', 'danger')
            return redirect(url_for('interventions.list_interventions'))
        
        if not file.filename.endswith('.csv'):
            flash('Only CSV files are allowed.', 'danger')
            return redirect(url_for('interventions.list_interventions'))
        
        # Read CSV
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_reader = csv.DictReader(stream)
        
        success_count = 0
        error_count = 0
        errors = []
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 since row 1 is header
            try:
                # Parse row
                client_name = row.get('Client Name', '').strip()
                employee_name = row.get('Employee Name', '').strip()
                intervention_type = row.get('Intervention Type', '').strip()
                date_str = row.get('Date', '').strip()
                start_time_str = row.get('Start Time', '').strip()
                end_time_str = row.get('End Time', '').strip()
                
                # Validate required fields
                if not all([client_name, employee_name, intervention_type, date_str, start_time_str, end_time_str]):
                    raise ValueError("Missing required fields")
                
                # Parse date and times
                try:
                    date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    start_time = datetime.strptime(start_time_str, '%H:%M').time()
                    end_time = datetime.strptime(end_time_str, '%H:%M').time()
                except ValueError:
                    raise ValueError("Invalid date or time format")
                
                # Calculate duration
                start_dt = datetime.combine(date, start_time)
                end_dt = datetime.combine(date, end_time)
                if end_dt <= start_dt:
                    raise ValueError("End time must be after start time")
                duration = (end_dt - start_dt).total_seconds() / 3600
                
                # Find client
                name_parts = client_name.split()
                if len(name_parts) < 2:
                    raise ValueError("Client name must have at least first and last name")
                
                client = None
                # Try different ways to split the name for matching
                for i in range(1, len(name_parts)):
                    potential_firstname = ' '.join(name_parts[:i])
                    potential_lastname = ' '.join(name_parts[i:])
                    client = Client.query.filter(
                        db.func.lower(Client.firstname) == potential_firstname.lower(),
                        db.func.lower(Client.lastname) == potential_lastname.lower(),
                        Client.is_active == True
                    ).first()
                    if client:
                        break
                
                if not client:
                    raise ValueError(f"Client '{client_name}' not found or inactive")
                
                # Find employee
                emp_parts = employee_name.split()
                if len(emp_parts) < 2:
                    raise ValueError("Employee name must have at least first and last name")
                
                employee = None
                # Try different ways to split the name for matching
                for i in range(1, len(emp_parts)):
                    potential_firstname = ' '.join(emp_parts[:i])
                    potential_lastname = ' '.join(emp_parts[i:])
                    employee = Employee.query.filter(
                        db.func.lower(Employee.firstname) == potential_firstname.lower(),
                        db.func.lower(Employee.lastname) == potential_lastname.lower(),
                        Employee.is_active == True
                    ).first()
                    if employee:
                        break
                
                if not employee:
                    raise ValueError(f"Employee '{employee_name}' not found or inactive")
                
                # Check intervention type exists and matches employee position
                intervention_type_clean = ' '.join(intervention_type.strip().split())  # Normalize whitespace and strip
                activity = Activity.query.filter(
                    Activity.activity_name.ilike(intervention_type_clean)
                ).first()
                if not activity:
                    # Get all available activities for better error message
                    all_activities = [a.activity_name for a in Activity.query.all()]
                    raise ValueError(f"Intervention type '{intervention_type}' not found. Available types: {', '.join(all_activities)}")
                
                # Check if activity category matches employee position
                if employee.position.lower() == 'behaviour analyst' and activity.activity_category.lower() != 'supervision':
                    raise ValueError(f"Behaviour Analyst can only perform Supervision activities")
                elif employee.position.lower() in ['therapist', 'senior therapist'] and activity.activity_category.lower() != 'therapy':
                    raise ValueError(f"{employee.position} can only perform Therapy activities")
                
                # Check permissions based on user type
                if current_user.user_type == 'supervisor':
                    emp = Employee.query.filter_by(email=current_user.email).first()
                    if not emp or client.supervisor_id != emp.id:
                        raise ValueError("Supervisor can only upload sessions for their clients")
                
                # Check for overlapping sessions
                if Intervention.has_overlap(employee.id, date, start_time, end_time):
                    raise ValueError(f"Schedule conflict for {employee_name} on {date_str}")
                
                # Create intervention
                new_intervention = Intervention(
                    client_id=client.id,
                    employee_id=employee.id,
                    intervention_type=activity.activity_name,
                    date=date,
                    start_time=start_time,
                    end_time=end_time,
                    duration=round(duration, 2),
                    invoiced=False,
                    invoice_number=None,
                    file_names=json.dumps([])
                )
                
                db.session.add(new_intervention)
                success_count += 1
                
            except Exception as e:
                error_msg = f"Row {row_num}: {str(e)}"
                errors.append(error_msg)
                error_count += 1
                if not skip_errors:
                    db.session.rollback()
                    flash(f'Error processing row {row_num}: {str(e)}', 'danger')
                    return redirect(url_for('interventions.list_interventions'))
        
        if success_count > 0:
            db.session.commit()
            flash(f'Successfully uploaded {success_count} sessions.', 'success')
        if error_count > 0:
            flash(f'Failed to process {error_count} rows: ' + '; '.join(errors[:5]), 'warning')  # Show first 5 errors
        
        return redirect(url_for('interventions.list_interventions'))
    else:
        abort(403)
