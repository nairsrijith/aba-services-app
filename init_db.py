from app import create_app, db
from app.models import User
from werkzeug.security import generate_password_hash

def initialize_database():
    app = create_app()
    with app.app_context():
        db.create_all()

        # Check if admin user already exists
        admin_user = User.query.filter_by(email='admin@admin.com').first()
        if not admin_user:
            # Create admin user
            hashed_password = generate_password_hash('Admin123$%^')
            new_admin = User(email='admin@admin.com', password_hash=hashed_password, user_type="super", locked=False, activation_key="")
            db.session.add(new_admin)
            db.session.commit()


if __name__ == '__main__':
    initialize_database()

