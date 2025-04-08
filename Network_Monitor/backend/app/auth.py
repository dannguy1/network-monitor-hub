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
    print(f"DEBUG: Login request data: {data}")
    username = data.get('username')
    password = data.get('password')
    print(f"DEBUG: Login username: {username}, Password provided: {bool(password)}")
    remember = data.get('remember', False)

    if not username or not password:
        print("DEBUG: Failing login due to missing username or password.")
        return jsonify({"error": "Username and password required"}), 400

    user = User.query.filter_by(username=username).first()

    if user is None or not user.verify_password(password):
        return jsonify({"error": "Invalid username or password"}), 401

    # Log user in
    login_user(user, remember=remember)
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