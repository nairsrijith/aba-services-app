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
