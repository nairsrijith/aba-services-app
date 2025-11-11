from app import create_app, db
from app.models import Employee

NEW_PASSWORD = "Admin1!"   # change to a secure password
ADMIN_EMAIL = "admin@example.com"     # change if different

app = create_app()

with app.app_context():
    user = Employee.query.filter_by(email=ADMIN_EMAIL).first()
    if not user:
        print(f"No user found with email {ADMIN_EMAIL}")
    else:
        user.set_password(NEW_PASSWORD)
        # optionally ensure login is enabled
        user.login_enabled = True
        db.session.commit()
        print(f"Password reset for {user.email}")