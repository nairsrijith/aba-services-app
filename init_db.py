from app import create_app, db
from app.models import User, Designation, Activity
from werkzeug.security import generate_password_hash
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

        # Check if admin user already exists
        logger.info("Checking for admin user admin@example.com")
        admin_user = User.query.filter_by(email='admin@example.com').first()
        if not admin_user:
            logger.info("Admin not found — creating admin user")
            hashed_password = generate_password_hash('Admin1!')
            super_admin = User(email='admin@example.com', password_hash=hashed_password, user_type="super", failed_attempt=3, activation_key="")
            db.session.add(super_admin)
            safe_commit()
            logger.info("Admin user created")
        else:
            logger.info("Admin user already exists")

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
            user_count = User.query.count()
            desig_count = Designation.query.count()
            act_count = Activity.query.count()
            logger.info("Row counts -> User: %s, Designation: %s, Activity: %s", user_count, desig_count, act_count)
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

