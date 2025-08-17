from flask import Blueprint, render_template, redirect, url_for, request
from app import db
from app.models import Intervention, Client, Employee, Activity
from app.interventions.forms import AddInterventionForm, UpdateInterventionForm
from flask_login import login_required, current_user
from sqlalchemy import or_, and_, desc

interventions_bp = Blueprint('interventions', __name__, template_folder='templates')


# client_id is a foreign key to the Client model
# employee_id is a foreign key to the Employee model
@interventions_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add_intervention():
    if current_user.is_authenticated and not current_user.user_type == "super":
        form = AddInterventionForm()
        form.client_id.choices = [(c.id, f"{c.firstname} {c.lastname}") for c in Client.query.all()]
        form.employee_id.choices = [(e.id, f"{e.firstname} {e.lastname}") for e in Employee.query.all()]
        form.intervention_type.choices = [(a.activity_name, a.activity_name) for a in Activity.query.all()]

        if form.validate_on_submit():
            new_intervention = Intervention(client_id=form.client_id.data,
                                            employee_id=form.employee_id.data,
                                            intervention_type=form.intervention_type.data,
                                            date=form.date.data,
                                            start_time=form.start_time.data,
                                            end_time=form.end_time.data,
                                            duration=round(float(form.duration.data), 2))
            db.session.add(new_intervention)
            db.session.commit()
            return redirect(url_for('interventions.list_interventions'))
        return render_template('add_int.html', form=form)
    else:
        return redirect(url_for('index'))


@interventions_bp.route('/list', methods=['GET'])
@login_required
def list_interventions():
    if current_user.is_authenticated and not current_user.user_type == "super":
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)

        # Start with base query
        query = Intervention.query.join(Client).join(Employee)

        # Apply filters BEFORE paginating
        invoiced_filter = request.args.get('invoiced')
        query = Intervention.query

        if invoiced_filter == 'yes':
            query = query.filter(Intervention.invoiced == True)
        elif invoiced_filter == 'no':
            query = query.filter(Intervention.invoiced == False)
        
        client = request.args.get('client', '').strip()
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
            activities=activities
        )
    else:
        return redirect(url_for('index'))


@interventions_bp.route('/bulk_delete', methods=['POST'])
@login_required
def bulk_delete():
    if current_user.is_authenticated and not current_user.user_type == "super":
        ids = request.form.getlist('selected_ids')
        if ids:
            Intervention.query.filter(Intervention.id.in_(ids)).delete(synchronize_session=False)
            db.session.commit()
        return redirect(url_for('interventions.list_interventions'))
    else:
        return redirect(url_for('index'))


@interventions_bp.route('/update/<int:intervention_id>', methods=['GET', 'POST'])
@login_required
def update_intervention(intervention_id):
    if current_user.is_authenticated and not current_user.user_type == "user":
        intervention = Intervention.query.get_or_404(intervention_id)
        form = UpdateInterventionForm(obj=intervention)
        form.client_id.choices = [(c.id, f"{c.firstname} {c.lastname}") for c in Client.query.all()]
        form.employee_id.choices = [(e.id, f"{e.firstname} {e.lastname}") for e in Employee.query.all()]
        form.intervention_type.choices = [(a.activity_name, a.activity_name) for a in Activity.query.all()]

        if request.method == 'POST':
            intervention.client_id = form.client_id.data
            intervention.employee_id = form.employee_id.data
            intervention.intervention_type = form.intervention_type.data
            intervention.date = form.date.data
            intervention.start_time = form.start_time.data
            intervention.end_time = form.end_time.data
            intervention.duration = round(float(form.duration.data), 2)
            intervention.invoiced = form.invoiced.data
            intervention.invoice_number = form.invoice_number.data
            db.session.commit()
            return redirect(url_for('interventions.list_interventions'))
        return render_template('update_int.html', form=form, clients=Client.query.all(), employees=Employee.query.all())
    else:
        return redirect(url_for('index'))
