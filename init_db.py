from app import create_app, db
from app.models import Employee, Designation, Activity, PayRate
from werkzeug.security import generate_password_hash
from datetime import date
import logging
import sys
from sqlalchemy import inspect

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

def initialize_database():
    logger.info("Creating Flask app and entering app context")
    app = create_app()

    # Print configured DB URI so you can verify which DB file/server is being used
    try:
        logger.info("App SQLALCHEMY_DATABASE_URI: %s", app.config.get("SQLALCHEMY_DATABASE_URI"))
    except Exception as e:
        logger.warning("Could not read SQLALCHEMY_DATABASE_URI: %s", e)

    with app.app_context():
        # Enable SQL echo on the engine to see SQL statements (helps confirm commits run)
        try:
            engine = db.get_engine(app)
            logger.info("Engine URL: %s", getattr(engine, "url", "<unknown>"))
            engine.echo = True
        except Exception as e:
            logger.warning("Could not enable engine echo: %s", e)

        inspector = inspect(db.engine)
        logger.info("Pre-create_all() tables: %s", inspector.get_table_names())

        logger.info("Calling db.create_all()")
        db.create_all()
        inspector = inspect(db.engine)
        logger.info("Post-create_all() tables: %s", inspector.get_table_names())

        # Helper to commit with logging
        def safe_commit():
            try:
                db.session.commit()
                logger.info("Commit succeeded")
            except Exception as e:
                logger.exception("Commit failed: %s", e)
                db.session.rollback()
                raise

        # First ensure we have the required designation
        logger.info("Ensuring admin designation exists")
        admin_designation = "Administrator"
        existing_designation = Designation.query.filter_by(designation=admin_designation).first()
        if not existing_designation:
            logger.info("Creating admin designation")
            new_designation = Designation(designation=admin_designation)
            db.session.add(new_designation)
            safe_commit()

        # Create super admin employee if they don't exist
        logger.info("Checking for admin employee admin@example.com")
        admin = Employee.query.filter_by(email='admin@example.com').first()
        if not admin:
            logger.info("Admin employee not found — creating")
            try:
                Employee.create_super_admin('admin@example.com', 'Admin1!')
                logger.info("Admin employee created successfully")
            except Exception as e:
                logger.exception("Failed to create admin employee: %s", e)
                raise
        else:
            logger.info("Admin employee already exists")

        # Check designations
        designations = ["Behaviour Analyst", "Senior Therapist", "Therapist"]
        for designation in designations:
            logger.info("Checking designation: %s", designation)
            existing_designation = Designation.query.filter_by(designation=designation).first()
            if not existing_designation:
                logger.info("Creating designation: %s", designation)
                new_designation = Designation(designation=designation)
                db.session.add(new_designation)
                safe_commit()
                logger.info("Created designation: %s", designation)
            else:
                logger.info("Designation exists: %s", designation)

        # Check activities
        default_activities = [
            ("Initial Assessment", "Supervision"),
            ("Parent Training", "Supervision"),
            ("Supervision", "Supervision"),
            ("Therapy", "Therapy")
        ]
        for activity_name, activity_category in default_activities:
            logger.info("Checking activity: %s (%s)", activity_name, activity_category)
            activity = Activity.query.filter_by(activity_name=activity_name, activity_category=activity_category).first()
            if not activity:
                logger.info("Creating activity: %s (%s)", activity_name, activity_category)
                new_activity = Activity(activity_name=activity_name, activity_category=activity_category)
                db.session.add(new_activity)
                safe_commit()
                logger.info("Created activity: %s", activity_name)
            else:
                logger.info("Activity exists: %s", activity_name)

        # Final counts to confirm rows exist in the same DB connection
        try:
            emp_count = Employee.query.count()
            desig_count = Designation.query.count()
            act_count = Activity.query.count()
            payrate_count = PayRate.query.count()
            logger.info("Row counts -> Employee: %s, Designation: %s, Activity: %s, PayRate: %s",
                       emp_count, desig_count, act_count, payrate_count)
        except Exception:
            logger.exception("Failed to read row counts")

if __name__ == '__main__':
    try:
        logger.info("Starting DB initialization script")
        initialize_database()
        logger.info("DB initialization completed successfully")
    except Exception:
        logger.exception("Initialization failed")
        sys.exit(1)

