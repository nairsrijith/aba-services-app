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
        # Reset 2FA in case admin lost their device
        user.two_factor_enabled = False
        user.two_factor_secret = None
        db.session.commit()
        print(f"Password and 2FA has been reset for {user.email}. They can set it up again on next login.")