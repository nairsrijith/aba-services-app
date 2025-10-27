from app.models import User
from app import db


def manage_user_for_employee(email, position, existing_user=None):
    """
    Creates or updates a user account based on employee information.
    If the employee already has a user account (existing_user), it will update the role
    unless the user is an admin.
    
    Args:
        email (str): Employee's email address
        position (str): Employee's position
        existing_user (User, optional): Existing user account if any. Defaults to None.
    
    Returns:
        User: The created or updated user account
    """
    # Determine role based on position
    if position == 'Behaviour Analyst':
        role = 'supervisor'
    else:
        role = 'therapist'
    
    if existing_user:
        # Don't downgrade admin users
        if existing_user.user_type != 'admin':
            existing_user.user_type = role
            db.session.commit()
        return existing_user
    else:
        # Create new user with generated activation code
        from app.users.views import generate_activation_code
        new_user = User(
            email=email,
            password_hash="",
            user_type=role,
            locked_until=None,
            failed_attempt=0,
            activation_key=generate_activation_code(8)
        )
        db.session.add(new_user)
        db.session.commit()
        return new_user