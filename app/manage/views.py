from flask import Blueprint, render_template, redirect, url_for, abort, flash
from app import db
from app.models import Designation, Activity, Intervention, Employee
from app.manage.forms import DesignationForm, ActivityForm
from flask_login import login_required, current_user
import os

manage_bp = Blueprint('manage', __name__, template_folder='templates')

org_name = os.environ.get('ORG_NAME', 'My Organization')


@manage_bp.route('/designations', methods=['GET', 'POST'])
@login_required
def designations():
    if current_user.is_authenticated and current_user.user_type != "user":
        form = DesignationForm()
        if form.validate_on_submit():
            new_designation = Designation(designation=form.name.data.title())
            db.session.add(new_designation)
            db.session.commit()
            flash('Designation added successfully.', 'success')
            return redirect(url_for('manage.designations'))
        designations = Designation.query.all()
        allocated_designations = [a.position for a in Employee.query.with_entities(Employee.position).distinct()] # Fetch unique designations
        return render_template('designations.html', form=form, designations=designations, allocated_designations=allocated_designations, org_name=org_name)
    else:
        abort(403)


@manage_bp.route('/activities', methods=['GET', 'POST'])
@login_required
def activities():
    if current_user.is_authenticated and current_user.user_type != "user":
        form = ActivityForm()
        form.category.choices = [("Therapy", "Therapy"), ("Supervision", "Supervision")]
        if form.validate_on_submit():
            new_activity = Activity(activity_name=form.name.data.title(), activity_category=form.category.data.title())
            db.session.add(new_activity)
            db.session.commit()
            flash('Activity added successfully.', 'success')
            return redirect(url_for('manage.activities'))
        activities = Activity.query.all()
        allocated_activities = [a.intervention_type for a in Intervention.query.with_entities(Intervention.intervention_type).distinct()] # Fetch unique intervention types
        return render_template('activities.html', form=form, activities=activities, allocated_activities=allocated_activities, org_name=org_name)
    else:
        abort(403)


@manage_bp.route('/delete_activity/<string:activity_name>', methods=['POST'])
@login_required
def delete_activity(activity_name):
    if current_user.is_authenticated and current_user.user_type != "user":
        activity = Activity.query.filter_by(activity_name=activity_name).first()
        # make sure activity is not used in any schedules or other dependencies before deleting
        # still need to implement this check
        if activity:
            db.session.delete(activity)
            db.session.commit()
            flash('Activity deleted successfully.', 'success')
        else:
            flash('Activity not found.', 'danger')
        return redirect(url_for('manage.activities'))
    else:
        abort(403)


@manage_bp.route('/delete_designation/<string:designation_name>', methods=['POST'])
@login_required
def delete_designation(designation_name):
    if current_user.is_authenticated and current_user.user_type != "user":
        designation = Designation.query.filter_by(designation=designation_name).first()
        # make sure designation is not allocated to any employee or other dependencies before deleting
        # still need to implement this check
        if designation:
            db.session.delete(designation)
            db.session.commit()
            flash('Designation deleted successfully.', 'success')
        else:
            flash('Designation not found.', 'danger')
        return redirect(url_for('manage.designations'))
    else:
        abort(403)