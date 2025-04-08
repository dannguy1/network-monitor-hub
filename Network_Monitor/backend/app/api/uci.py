from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required
from .. import db
from ..models import Device
from ..services.controllers import get_device_controller, SSHController

# Define the Blueprint
bp = Blueprint('uci', __name__)

@bp.route('/devices/<int:id>/apply', methods=['POST'])
@login_required
def apply_uci_commands(id):
    """Apply arbitrary commands (typically UCI) to a specific device."""
    device = db.session.get(Device, id)
    if not device:
        return jsonify({"error": "Device not found"}), 404

    data = request.get_json()
    if not data or 'commands' not in data or not isinstance(data['commands'], list):
        return jsonify({"error": "Missing or invalid 'commands' field (must be a list of strings)"}), 400

    commands = data['commands']
    if not commands:
         return jsonify({"error": "'commands' list cannot be empty"}), 400

    try:
        controller = get_device_controller(device)
        
        # Ensure controller supports execute_commands (or is SSHController)
        if not isinstance(controller, SSHController) or not hasattr(controller, 'execute_commands'):
             return jsonify({"error": f"Device controller ({type(controller).__name__}) does not support arbitrary command execution."}), 501

        # Call the new execute_commands method
        result = controller.execute_commands(commands)
        
        # Return the output directly, always with 200 OK if connection worked
        if result['error']:
             # If connection failed, return 500
             return jsonify({"error": "SSH connection or execution failed", "details": result['error']}), 500
        else:
             # Return captured output
             return jsonify({"output": result['output']}), 200

    except (ValueError, TypeError, NotImplementedError) as e:
        current_app.logger.error(f"Controller error preparing UCI for {device.name}: {e}")
        return jsonify({"error": f"Configuration error: {e}"}), 400 # Or 501 if NotImplemented
    except Exception as e:
        current_app.logger.error(f"Unexpected error applying UCI to {device.name}: {e}", exc_info=True)
        return jsonify({"error": "An unexpected internal error occurred"}), 500 