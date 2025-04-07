from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from .. import db # Import db for health check

api = Blueprint('api', __name__)

# --- Public Health Check --- 
@api.route('/healthz')
def health_check():
    try:
        # Perform a simple query to check DB connection
        db.session.execute(db.text('SELECT 1'))
        return jsonify({"status": "ok", "database": "connected"}), 200
    except Exception as e:
        # Log the error for internal diagnosis
        # current_app.logger.error(f"Health check failed: DB connection error: {e}")
        return jsonify({"status": "error", "database": "disconnected", "error": str(e)}), 503 # Service Unavailable

# --- Protected API Routes --- 
@api.before_request
@login_required # Require login for all API routes *except* healthz (due to ordering)
def before_request():
    """Protect all API endpoints."""
    # This runs *after* the health_check route is defined, so health_check remains public
    pass

# Example: Add an endpoint to get current user info
@api.route('/me')
@login_required
def get_current_user():
    return jsonify({
        "id": current_user.id,
        "username": current_user.username,
        # Add other non-sensitive fields if needed
    })

# Import the routes to register them with the blueprint
from . import devices, credentials, logs # Add other route files here as they are created 