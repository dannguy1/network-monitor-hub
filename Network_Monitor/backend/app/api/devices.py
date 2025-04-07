from flask import request, jsonify, url_for, current_app
from flask_login import login_required
from . import api
from .. import db
from ..models import Device
from sqlalchemy.exc import IntegrityError
from ..services.controllers import get_device_controller
import datetime

@api.route('/devices', methods=['POST'])
def create_device():
    """Create a new device."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    name = data.get('name')
    ip_address = data.get('ip_address')

    if not name or not ip_address:
        return jsonify({"error": "Missing required fields: name and ip_address"}), 400

    if Device.query.filter_by(name=name).first():
         return jsonify({"error": f"Device with name '{name}' already exists"}), 409
    if Device.query.filter_by(ip_address=ip_address).first():
         return jsonify({"error": f"Device with IP address '{ip_address}' already exists"}), 409

    device = Device(
        name=name,
        ip_address=ip_address,
        description=data.get('description'),
        control_method=data.get('control_method', 'ssh'),
        # status will default to 'Unknown'
    )
    db.session.add(device)
    try:
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "Database integrity error", "message": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create device", "message": str(e)}), 500

    response = jsonify(device.to_dict())
    response.status_code = 201
    response.headers['Location'] = url_for('api.get_device', id=device.id)
    return response

@api.route('/devices', methods=['GET'])
def get_devices():
    """Get a list of all devices."""
    devices = Device.query.order_by(Device.name).all()
    return jsonify([device.to_dict() for device in devices])

@api.route('/devices/<int:id>', methods=['GET'])
def get_device(id):
    """Get a single device by ID."""
    device = db.session.get(Device, id)
    if device is None:
        return jsonify({"error": "Device not found"}), 404
    return jsonify(device.to_dict())

@api.route('/devices/<int:id>', methods=['PUT'])
def update_device(id):
    """Update an existing device."""
    device = db.session.get(Device, id)
    if device is None:
        return jsonify({"error": "Device not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    # Check for potential conflicts if name or IP are being changed
    new_name = data.get('name')
    if new_name and new_name != device.name and Device.query.filter_by(name=new_name).first():
        return jsonify({"error": f"Device with name '{new_name}' already exists"}), 409

    new_ip = data.get('ip_address')
    if new_ip and new_ip != device.ip_address and Device.query.filter_by(ip_address=new_ip).first():
        return jsonify({"error": f"Device with IP address '{new_ip}' already exists"}), 409

    # Update fields if provided in the request
    device.name = new_name or device.name
    device.ip_address = new_ip or device.ip_address
    device.description = data.get('description', device.description)
    device.status = data.get('status', device.status)
    # Update control method if provided
    new_control_method = data.get('control_method')
    if new_control_method and new_control_method in ['ssh', 'rest']: # Validate
        device.control_method = new_control_method
    elif new_control_method:
        return jsonify({"error": f"Invalid control_method '{new_control_method}'. Must be 'ssh' or 'rest'"}), 400
    # credential_id update might be handled separately or via credential endpoints

    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update device", "message": str(e)}), 500

    return jsonify(device.to_dict())

@api.route('/devices/<int:id>', methods=['DELETE'])
@login_required
def delete_device(id):
    """Delete a device."""
    device = db.session.get(Device, id)
    if device is None:
        return jsonify({"error": "Device not found"}), 404

    # Consider implications: What happens to associated logs or credentials?
    # Option 1: Delete logs (cascade delete in model or manual delete here)
    # Option 2: Keep logs but disassociate (set device_id to null if allowed)
    # Option 3: Prevent deletion if logs exist
    # For now, let's assume we delete the device only. Need to handle FK constraints.
    # If credentials have FK constraint, they might need to be deleted or unlinked first.
    if device.credential:
         # Simple approach: unlink credential association first
         device.credential_id = None
         device.credential = None
         db.session.add(device) # stage the change
         # Note: This does NOT delete the credential itself, just the link.
         # You might want a different strategy (e.g., delete credential if not used elsewhere)

    # Similar consideration for logs. If LogEntry.device_id cannot be NULL,
    # deletion will fail unless logs are deleted first or handled by cascade.
    # Assuming cascade delete is NOT set for logs for now.
    if device.logs.first(): # Check if any logs exist for this device
        return jsonify({"error": "Cannot delete device with associated logs. Please delete logs first or implement log deletion logic."}), 409

    db.session.delete(device)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to delete device", "message": str(e)}), 500

    return jsonify({"message": "Device deleted successfully"}), 200

# --- Device Control Endpoints (Refactored to use Controller) ---

@api.route('/devices/<int:id>/apply_config', methods=['POST'])
@login_required
def apply_device_config(id):
    """Apply configuration to a specific device using its control method."""
    device = db.session.get(Device, id)
    if not device:
        return jsonify({"error": "Device not found"}), 404

    data = request.get_json()
    # Config data format might vary based on controller (e.g., list for SSH, dict for REST)
    if not data or 'config_data' not in data: 
        return jsonify({"error": "Missing 'config_data' in request body"}), 400

    config_data = data['config_data']
    restart_requested_service = data.get('restart_service') # Optional: e.g., {'service': 'log'}

    try:
        controller = get_device_controller(device)
        result = controller.apply_config(config_data)
        
        # If apply succeeded and a restart was requested, attempt it
        if result.get("success") and restart_requested_service and isinstance(restart_requested_service, dict):
            service_name = restart_requested_service.get('service')
            if service_name:
                current_app.logger.info(f"Config applied, now attempting restart of '{service_name}' for {device.name}")
                restart_result = controller.restart_service(service_name)
                # Append restart status to the original message/result
                result["message"] = (result.get("message", "") + f" | Service '{service_name}' Restart: {restart_result.get('message')}").strip(" | ")
                if not restart_result.get("success"):
                     result["stderr"] = (result.get("stderr", "") + f"\nRestart Error: {restart_result.get('stderr', 'Unknown')}").strip()
                     # Keep overall success as True from apply_config, but indicate restart issue

        status_code = 200 if result.get("success") else 500 # Base status on apply_config result
        return jsonify(result), status_code
    except (ValueError, TypeError, NotImplementedError) as e: # Catch factory/controller errors
        current_app.logger.error(f"Controller error applying config to {device.name}: {e}")
        return jsonify({"error": f"Configuration error: {e}"}), 400 # Or 501 if NotImplemented
    except Exception as e:
        current_app.logger.error(f"Unexpected error applying config to {device.name}: {e}", exc_info=True)
        return jsonify({"error": "An unexpected internal error occurred"}), 500

# Define standard UCI paths for OpenWRT logd (still useful for SSHController logic)
LOGD_CONFIG = {
    'section': 'system.@system[0]', # Default logd settings are often here
    'option_log_ip': 'log_ip',      # Remote syslog IP target
    'option_log_port': 'log_port',    # Remote syslog port
    'option_log_proto': 'log_proto', # Protocol (udp/tcp)
    'option_log_size': 'log_size',    # Local buffer size (optional to check)
    'option_log_level': 'conloglevel' # Console/kernel log level (optional)
}

@api.route('/devices/<int:id>/log_config', methods=['GET'])
@login_required
def get_device_log_config(id):
    """Get current remote logging configuration from the device using its controller."""
    device = db.session.get(Device, id)
    if not device:
        return jsonify({"error": "Device not found"}), 404

    # The specific config key depends on the underlying implementation (UCI path for SSH)
    # We might need a way to map generic keys to specific ones per controller type,
    # or the frontend needs to know which key to ask for based on control_method.
    # For now, assuming SSH and using the UCI path directly.
    if device.control_method != 'ssh':
         return jsonify({"error": f"Log config retrieval not implemented for '{device.control_method}' method."}), 501

    config_key = f"{LOGD_CONFIG['section']}.{LOGD_CONFIG['option_log_ip']}"

    try:
        controller = get_device_controller(device)
        result = controller.get_config(config_key)

        if result.get("success"):
            remote_ip = result.get("value")
            is_logging_remote = bool(remote_ip)
            return jsonify({
                "device_id": id,
                "remote_logging_enabled": is_logging_remote,
                "remote_log_target": remote_ip,
            }), 200
        else:
             # Propagate error message from controller
             return jsonify({"error": result.get("message", "Failed to retrieve log config")}), 500

    except (ValueError, TypeError, NotImplementedError) as e: # Catch factory/controller errors
        current_app.logger.error(f"Controller error getting log config for {device.name}: {e}")
        return jsonify({"error": f"Configuration error: {e}"}), 400 # Or 501 if NotImplemented
    except Exception as e:
         current_app.logger.error(f"Unexpected error getting log config for device {id}: {e}", exc_info=True)
         return jsonify({"error": "An unexpected internal error occurred"}), 500

@api.route('/devices/<int:id>/log_config', methods=['POST'])
@login_required
def set_device_log_config(id):
    """Enable or disable remote logging to this server using the device controller."""
    device = db.session.get(Device, id)
    if not device:
        return jsonify({"error": "Device not found"}), 404

    data = request.get_json()
    if not data or 'enable' not in data or not isinstance(data['enable'], bool):
        return jsonify({"error": "Missing or invalid required field: 'enable' (boolean)"}), 400

    # Specific config generation logic remains here for now, but could be moved
    # into the SSH controller or a helper service if it gets complex.
    if device.control_method != 'ssh':
         return jsonify({"error": f"Log config setting not implemented for '{device.control_method}' method."}), 501

    enable_logging = data['enable']
    target_ip = request.host.split(':')[0] # Still potentially fragile
    target_port = 514
    target_proto = 'udp'

    uci_commands = []
    section = LOGD_CONFIG['section']
    log_ip_option = LOGD_CONFIG['option_log_ip']
    log_port_option = LOGD_CONFIG['option_log_port']
    log_proto_option = LOGD_CONFIG['option_log_proto']

    if enable_logging:
        uci_commands.extend([
            f"uci set {section}.{log_ip_option}={target_ip}",
            f"uci set {section}.{log_port_option}={target_port}",
            f"uci set {section}.{log_proto_option}={target_proto}"
        ])
    else:
        uci_commands.extend([
            f"uci delete {section}.{log_ip_option}",
            f"uci delete {section}.{log_port_option}",
            f"uci delete {section}.{log_proto_option}"
        ])

    if not uci_commands:
         return jsonify({"message": "No changes needed."}), 200

    try:
        controller = get_device_controller(device) 
        # Pass the generated UCI commands as config_data for SSHController
        result = controller.apply_config(uci_commands) 
        
        # Use the controller's restart_service method
        if result.get("success"):
             current_app.logger.info(f"Log config applied, now attempting restart of 'log' service for {device.name}")
             restart_result = controller.restart_service('log') # Use the controller method
             # Append restart status to the original message/result
             result["message"] = (result.get("message", "") + f" | Service 'log' Restart: {restart_result.get('message')}").strip(" | ")
             if not restart_result.get("success"):
                 result["stderr"] = (result.get("stderr", "") + f"\nRestart Error: {restart_result.get('stderr', 'Unknown')}").strip()
                 # Keep overall success as True from apply_config, but indicate restart issue

        status_code = 200 if result.get("success") else 500 # Base status on apply_config result
        return jsonify(result), status_code

    except (ValueError, TypeError, NotImplementedError) as e: # Catch factory/controller errors
        current_app.logger.error(f"Controller error setting log config for {device.name}: {e}")
        return jsonify({"error": f"Configuration error: {e}"}), 400 # Or 501 if NotImplemented
    except Exception as e:
         current_app.logger.error(f"Unexpected error setting log config for device {id}: {e}", exc_info=True)
         return jsonify({"error": "An unexpected internal error occurred"}), 500

# --- Reboot Device --- 
@api.route('/devices/<int:id>/reboot', methods=['POST'])
@login_required
def post_reboot_device(id):
    """Trigger a reboot on the specified device using its controller."""
    device = db.session.get(Device, id)
    if not device:
        return jsonify({"error": "Device not found"}), 404
    
    try:
        controller = get_device_controller(device)
        result = controller.reboot()
        status_code = 200 if result.get("success") else 500
        return jsonify(result), status_code
    except (ValueError, TypeError, NotImplementedError) as e: # Catch factory/controller errors
        current_app.logger.error(f"Controller error rebooting {device.name}: {e}")
        return jsonify({"error": f"Reboot error: {e}"}), 400 # Or 501 if NotImplemented
    except Exception as e:
        current_app.logger.error(f"Unexpected error triggering reboot for device {id}: {e}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred during reboot trigger"}), 500

# --- Refresh Device Status --- 
@api.route('/devices/<int:id>/refresh_status', methods=['POST'])
@login_required
def refresh_device_status(id):
    """Attempt to check device status using its controller and update DB."""
    device = db.session.get(Device, id)
    if not device:
        return jsonify({"error": "Device not found"}), 404
    
    current_app.logger.info(f"Attempting to refresh status for device {device.name} ({device.ip_address}) using {device.control_method}")
    
    try:
        controller = get_device_controller(device)
        check_result = controller.check_status()
        
        # Update device status in DB based *only* on controller result
        original_status = device.status
        # Use status and last_seen directly from the controller's response
        device.status = check_result.get("status")
        device.last_seen = check_result.get("last_seen") # Will be None if check failed

        status_changed = device.status != original_status or (device.last_seen is not None and original_status != check_result.get("status"))

        try:
            db.session.commit()
            current_app.logger.info(f"Status refresh DB update for {device.name} complete. New Status: {device.status}, Changed: {status_changed}")
            # Return info from the check and DB update
            return jsonify({ 
                "success": True, # Overall operation success (check + db update)
                "message": check_result.get("message", "Status check completed."), 
                "device_status": device.status, 
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
                "status_changed": status_changed
            }), 200
        except Exception as db_e:
            db.session.rollback()
            current_app.logger.error(f"Failed to update device status after refresh for {device.name}: {db_e}")
            # Return info about the check, but indicate DB error
            return jsonify({ 
                "success": False, # Overall operation failed (db update)
                "message": f"Verification attempt resulted in message '{check_result.get("message")}', but failed to save status update: {db_e}", 
                "error": "Database update failed" 
            }), 500
            
    except (ValueError, TypeError, NotImplementedError) as e: # Catch factory/controller errors
        current_app.logger.error(f"Controller error checking status for {device.name}: {e}")
        # Update status to reflect error? Maybe 'Controller Error'?
        # device.status = 'Controller Error'
        # db.session.commit() # Commit the error status? Risky if it loops.
        return jsonify({"error": f"Status check error: {e}"}), 400 # Or 501 if NotImplemented
    except Exception as e:
        current_app.logger.error(f"Unexpected error refreshing status for device {id}: {e}", exc_info=True)
        return jsonify({"error": "An unexpected internal error occurred during status refresh"}), 500 