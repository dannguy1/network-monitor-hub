from flask import Blueprint, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from .models import User
from . import db, limiter, login_manager

auth = Blueprint('auth', __name__)

# --- Add User Loader --- #
@login_manager.user_loader
def load_user(user_id):
    # user_id is typically the primary key as a string
    return User.query.get(int(user_id))
# --- End User Loader --- #

@auth.route('/login', methods=['POST'])
@limiter.limit("5 per minute")
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    remember = data.get('remember', False)

    # --- Add Debug Logging --- 
    current_app.logger.debug(f"Login attempt: Received username='{username}', password_present={password is not None}")
    # --- End Debug Logging ---

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    user = User.query.filter_by(username=username).first()

    # --- Add Debug Logging --- 
    if user:
        current_app.logger.debug(f"Login attempt: Found user object for '{username}'. ID: {user.id}")
        password_match = user.verify_password(password)
        current_app.logger.debug(f"Login attempt: Password verification result for '{username}': {password_match}")
    else:
        current_app.logger.debug(f"Login attempt: User object NOT found for username '{username}'")
    # --- End Debug Logging ---

    if user is None or not user.verify_password(password):
        # --- Add Debug Logging --- 
        current_app.logger.warning(f"Login failed for username '{username}'. User found: {user is not None}, Password verified: {user.verify_password(password) if user else 'N/A'}")
        # --- End Debug Logging ---
        return jsonify({"error": "Invalid username or password"}), 401

    # Log user in
    login_user(user, remember=remember)
    # --- Add Debug Logging ---
    current_app.logger.info(f"Login successful for user '{username}'.")
    # --- End Debug Logging ---
    # Return user info (without sensitive data)
    return jsonify({
        "id": user.id,
        "username": user.username
        # Add other non-sensitive fields if needed
    })

@auth.route('/logout', methods=['POST'])
@login_required # User must be logged in to log out
def logout():
    logout_user()
    return jsonify({"message": "Successfully logged out"}), 200

@auth.route('/status', methods=['GET'])
def status():
    """Check if a user is currently logged in."""
    if current_user.is_authenticated:
        return jsonify({
            "logged_in": True,
            "user": {
                "id": current_user.id,
                "username": current_user.username
            }
        })
    else:
        return jsonify({"logged_in": False}), 401 # Return 401 if not logged in

@auth.route('/change-password', methods=['POST'])
@login_required
def change_password():
    """Allows the currently logged-in user to change their password."""
    data = request.get_json()
    if not data or 'current_password' not in data or 'new_password' not in data:
        return jsonify({"error": "Missing current_password or new_password"}), 400

    current_password = data.get('current_password')
    new_password = data.get('new_password')

    # Basic validation for new password complexity (optional but recommended)
    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters long"}), 400
    # Add more complexity rules if desired (uppercase, number, symbol)

    user = current_user # Get the currently logged-in user from Flask-Login

    # Verify the current password
    if not user.verify_password(current_password):
        return jsonify({"error": "Incorrect current password"}), 401 # Unauthorized
    
    # Verify the new password is not the same as the old one
    if user.verify_password(new_password):
        return jsonify({"error": "New password cannot be the same as the old password"}), 400

    # Set the new password (the setter handles hashing)
    user.password = new_password
    
    try:
        db.session.commit()
        current_app.logger.info(f"User '{user.username}' successfully changed their password.")
        return jsonify({"message": "Password updated successfully"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error changing password for user '{user.username}': {e}", exc_info=True)
        return jsonify({"error": "Failed to update password"}), 500

# Optional: Add a route for creating the first user if none exist
# This should ideally be a CLI command for security.

# CLI command to create users (add this to cli.py)
# @click.command('create-user')
# @click.argument('username')
# @click.password_option()
# @with_appcontext
# def create_user_command(username, password):
#     """Creates a new user."""
#     from .models import User
#     from . import db
#     if User.query.filter_by(username=username).first():
#         click.echo(f'Error: User "{username}" already exists.')
#         return
#     user = User(username=username, password=password)
#     db.session.add(user)
#     db.session.commit()
#     click.echo(f'User "{username}" created successfully.') 