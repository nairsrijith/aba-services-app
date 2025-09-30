from app import create_app, db
from app.models import User, Designation, Activity
from werkzeug.security import generate_password_hash


def initialize_database():
    app = create_app()
    with app.app_context():
        db.create_all()

        # Check if admin user already exists
        admin_user = User.query.filter_by(email='admin@example.com').first()
        if not admin_user:
            # Create admin user
            hashed_password = generate_password_hash('Admin1!')
            super_admin = User(email='admin@example.com', password_hash=hashed_password, user_type="super", failed_attempt=3, activation_key="")
            db.session.add(super_admin)
            db.session.commit()
        
        # Check if default designations exist in the designation table
        designations = ["Behaviour Analyst", "Senior Therapist", "Therapist"]
        for designation in designations:
            existing_designation = Designation.query.filter_by(designation=designation).first()
            if not existing_designation:
                new_designation = Designation(designation=designation)
                db.session.add(new_designation)
                db.session.commit()

        # Check if default activities with respective category exist in the activity table
        default_activities = [
            ("Initial Assessment", "Supervision"),
            ("Parent Training", "Supervision"),
            ("Supervision", "Supervision"),
            ("Therapy", "Therapy")
        ]
        for activity_name, activity_category in default_activities:
            activity = Activity.query.filter_by(activity_name=activity_name, activity_category=activity_category).first()
            if not activity:
                new_activity = Activity(activity_name=activity_name, activity_category=activity_category)
                db.session.add(new_activity)
                db.session.commit()


if __name__ == '__main__':
    initialize_database()

