from flask import Blueprint, render_template, redirect, url_for, request, abort, flash, send_from_directory
from app import db, app, allowed_file
from app.models import Intervention, Client, Employee, Activity
from app.interventions.forms import AddInterventionForm, UpdateInterventionForm
from flask_login import login_required, current_user
import os
import json
from werkzeug.utils import secure_filename
import shutil


interventions_bp = Blueprint('interventions', __name__, template_folder='templates')

org_name = os.environ.get('ORG_NAME', 'My Organization')


# client_id is a foreign key to the Client model
# employee_id is a foreign key to the Employee model
@interventions_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_intervention():
    if current_user.is_authenticated and not current_user.user_type == "super":
        clients = Client.query.all()
        if not clients:
            flash('Please add clients before adding interventions.', 'warning')
            return redirect(url_for('clients.list_clients'))
        
        form = AddInterventionForm()
        form.client_id.choices = [(c.id, f"{c.firstname} {c.lastname}") for c in Client.query.filter_by(is_active=True).all()]
        if current_user.user_type == "admin":
            form.employee_id.choices = [(e.id, f"{e.firstname} {e.lastname}") for e in Employee.query.filter_by(is_active=True).all()]
        else:
            form.employee_id.choices = [(e.id, f"{e.firstname} {e.lastname}") for e in Employee.query.filter_by(email=current_user.email, is_active=True).all()]
        form.intervention_type.choices = [(a.activity_name, a.activity_name) for a in Activity.query.all()]

        if form.validate_on_submit():
            client_id = form.client_id.data
            client_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(client_id))
            os.makedirs(client_folder, exist_ok=True)
            filenames = []
            for file_storage in request.files.getlist(form.file_names.name):
                if file_storage and file_storage.filename and allowed_file(file_storage.filename):
                    filename = secure_filename(file_storage.filename)
                    file_storage.save(os.path.join(client_folder, filename))
                    filenames.append(filename)
                elif file_storage and file_storage.filename:
                    flash(f"File type not allowed: {file_storage.filename}", "danger")
            
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
            return redirect(url_for('interventions.list_interventions'))
        return render_template('add_int.html', form=form, org_name=org_name)
    else:
        abort(403)


@interventions_bp.route('/list', methods=['GET'])
@login_required
def list_interventions():
    if current_user.is_authenticated and not current_user.user_type == "super":
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Apply filters BEFORE paginating
        invoiced_filter = request.args.get('invoiced')
        query = Intervention.query.join(Employee)

        if current_user.user_type == "user":
            query = query.filter(Employee.email == current_user.email)

        if invoiced_filter == 'yes':
            query = query.filter(Intervention.invoiced == True)
        elif invoiced_filter == 'no':
            query = query.filter(Intervention.invoiced == False)
        
        client = request.args.get('client')
        
        if client:
            query = query.filter(
                (Client.firstname.ilike(f"%{client}%")) |
                (Client.lastname.ilike(f"%{client}%"))
            )

        date_from = request.args.get('date_from', '')
        if date_from:
            query = query.filter(Intervention.date >= date_from)

        date_to = request.args.get('date_to', '')
        if date_to:
            query = query.filter(Intervention.date <= date_to)

        intervention_type = request.args.get('intervention_type', '')
        if intervention_type:
            query = query.filter(Intervention.intervention_type == intervention_type)

        query = query.order_by(Intervention.date.desc(), Intervention.start_time.desc(), Intervention.end_time.asc())
        
        
        # Now paginate the filtered query
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        activities = Activity.query.order_by(Activity.activity_name).all()

        return render_template(
            'list_int.html',
            interventions=pagination.items,
            pagination=pagination,
            per_page=per_page,
            activities=activities,
            org_name=org_name
        )
    else:
        abort(403)


import os
import shutil
import json

@interventions_bp.route('/bulk_delete', methods=['POST'])
@login_required
def bulk_delete():
    if current_user.is_authenticated and not current_user.user_type == "super":
        ids = request.form.getlist('selected_ids')
        if ids:
            interventions = Intervention.query.filter(Intervention.id.in_(ids)).all()
            to_delete = []
            skipped = []
            for intervention in interventions:
                # Prevent deletion when invoiced or already paid
                if intervention.invoiced or intervention.is_paid:
                    skipped.append(intervention)
                else:
                    to_delete.append(intervention)

            if to_delete:
                for intervention in to_delete:
                    client_id = intervention.client_id
                    client_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(client_id))
                    deleted_folder = os.path.join(app.config['DELETE_FOLDER'], str(client_id))
                    os.makedirs(deleted_folder, exist_ok=True)
                    filenames = intervention.get_file_names()
                    for filename in filenames:
                        src = os.path.join(client_folder, filename)
                        dst = os.path.join(deleted_folder, filename)
                        if os.path.exists(src):
                            shutil.move(src, dst)
                    db.session.delete(intervention)
                db.session.commit()

            if skipped:
                # Inform the user which sessions were not deleted
                flash(f"{len(skipped)} selected session(s) were not deleted because they are invoiced or already paid.", "warning")
        return redirect(url_for('interventions.list_interventions'))
    else:
        abort(403)


@interventions_bp.route('/update/<int:intervention_id>', methods=['GET', 'POST'])
@login_required
def update_intervention(intervention_id):
    if current_user.is_authenticated and not current_user.user_type == "super":
        intervention = Intervention.query.get_or_404(intervention_id)

        # Disallow editing if the session is invoiced or already paid
        if intervention.invoiced or intervention.is_paid:
            flash('This session cannot be edited because it is either invoiced or already paid.', 'warning')
            return redirect(url_for('interventions.list_interventions'))
        form = UpdateInterventionForm(obj=intervention)
        # Include the current client and employee in choices even if inactive
        client_choices = [(c.id, f"{c.firstname} {c.lastname}") for c in Client.query.filter_by(is_active=True).all()]
        if intervention.client_id:
            client_choices.extend([(c.id, f"{c.firstname} {c.lastname} (Inactive)") 
                                 for c in Client.query.filter_by(id=intervention.client_id, is_active=False).all()])
        form.client_id.choices = client_choices

        if current_user.user_type == "admin":
            emp_choices = [(e.id, f"{e.firstname} {e.lastname}") for e in Employee.query.filter_by(is_active=True).all()]
            if intervention.employee_id:
                emp_choices.extend([(e.id, f"{e.firstname} {e.lastname} (Inactive)")
                                  for e in Employee.query.filter_by(id=intervention.employee_id, is_active=False).all()])
            form.employee_id.choices = emp_choices
        else:
            form.employee_id.choices = [(e.id, f"{e.firstname} {e.lastname}") 
                                      for e in Employee.query.filter_by(email=current_user.email, is_active=True).all()]
        form.intervention_type.choices = [(a.activity_name, a.activity_name) for a in Activity.query.all()]

        if request.method == 'POST':
            client_id = form.client_id.data
            client_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(client_id))
            deleted_folder = os.path.join(app.config['DELETE_FOLDER'], str(client_id))
            os.makedirs(client_folder, exist_ok=True)
            os.makedirs(deleted_folder, exist_ok=True)

            filenames = intervention.get_file_names()
            remove_files = request.form.getlist('remove_files')
            # Move removed files to deleted folder
            for filename in remove_files:
                src = os.path.join(client_folder, filename)
                dst = os.path.join(deleted_folder, filename)
                if os.path.exists(src):
                    shutil.move(src, dst)
            # Remove from filenames list
            filenames = [f for f in filenames if f not in remove_files]

            # Handle new uploads
            for file_storage in request.files.getlist(form.file_names.name):
                if file_storage and file_storage.filename and allowed_file(file_storage.filename):
                    filename = secure_filename(file_storage.filename)
                    file_storage.save(os.path.join(client_folder, filename))
                    filenames.append(filename)
                    flash(f"File added: {file_storage.filename}", "success")
                elif file_storage and file_storage.filename:
                    flash(f"File type not allowed: {file_storage.filename}", "danger")

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
            db.session.commit()
            return redirect(url_for('interventions.list_interventions'))
        return render_template('update_int.html', form=form, clients=Client.query.all(), employees=Employee.query.all(), org_name=org_name, intervention=intervention)
    else:
        abort(403)


@interventions_bp.route('/download/<int:client_id>/<filename>')
@login_required
def download_file(client_id, filename):
    client_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(client_id))
    return send_from_directory(client_folder, filename, as_attachment=True)
