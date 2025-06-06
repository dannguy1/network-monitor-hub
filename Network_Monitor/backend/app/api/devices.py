from flask import request, jsonify, url_for, current_app
from flask_login import login_required
from . import api
from .. import db
from ..models import Device, Credential
from sqlalchemy.exc import IntegrityError
from ..services.controllers import get_device_controller
import datetime
from ..services.ssh_manager import verify_ssh_connection
import os # Import os module

@api.route('/devices', methods=['POST'])
@login_required
def create_device():
    """Create a new device and its required credential."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    # --- Device Fields (Required) --- #
    name = data.get('name')
    ip_address = data.get('ip_address')
    description = data.get('description')
    control_method = data.get('control_method', 'ssh')

    # --- Credential Fields (Required) --- #
    cred_ssh_username = data.get('credential_ssh_username')
    cred_auth_type = data.get('credential_auth_type') # 'password' or 'key'
    cred_password = data.get('credential_password')
    cred_private_key = data.get('credential_private_key')

    # --- Validation (All fields now required, except cred_name) --- #
    required_device_fields = {'name': name, 'ip_address': ip_address}
    required_cred_fields = {'credential_ssh_username': cred_ssh_username, 'credential_auth_type': cred_auth_type}
    
    missing_fields = [k for k, v in required_device_fields.items() if not v]
    missing_fields.extend([k for k, v in required_cred_fields.items() if not v])

    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400

    if cred_auth_type not in ['password', 'key']:
        return jsonify({"error": "Invalid credential_auth_type. Must be 'password' or 'key'"}), 400
    if cred_auth_type == 'password' and not cred_password:
         return jsonify({"error": "Missing credential_password for password auth type"}), 400
    if cred_auth_type == 'key' and not cred_private_key:
         return jsonify({"error": "Missing credential_private_key for key auth type"}), 400

    # --- Uniqueness Checks --- #
    if Device.query.filter_by(name=name).first():
         return jsonify({"error": f"Device with name '{name}' already exists"}), 409
    if Device.query.filter_by(ip_address=ip_address).first():
         return jsonify({"error": f"Device with IP address '{ip_address}' already exists"}), 409

    # --- Create Objects (within transaction) --- #
    device = Device(
        name=name,
        ip_address=ip_address,
        description=description,
        control_method=control_method
    )
    credential = Credential(
        ssh_username=cred_ssh_username,
        auth_type=cred_auth_type
    )
    if cred_auth_type == 'password':
        credential.password = cred_password
    else:
        credential.private_key = cred_private_key
    
    device.credential = credential 

    try:
        db.session.add(credential) 
        db.session.add(device)    
        db.session.commit()
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"DB Integrity Error creating device {name}: {e}", exc_info=True)
        return jsonify({"error": "Database integrity error", "message": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating device {name}: {e}", exc_info=True)
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
    """Delete a device and its associated logs via cascade."""
    device = db.session.get(Device, id)
    if device is None:
        return jsonify({"error": "Device not found"}), 404

    # No need to manually unlink credential, cascade should handle if needed?
    # Actually, the Credential relationship is nullable and doesn't have cascade by default.
    # Unlinking might still be desired if we want to keep orphaned credentials.
    # If credential should ALSO be deleted if it's only used by this device, more logic is needed.
    # For now, just deleting the device (and its logs via cascade).
    
    # REMOVED: Check for existing logs, as cascade delete handles this now.
    # if device.logs.first(): 
    #    return jsonify({"error": "Cannot delete device with associated logs..."}), 409

    db.session.delete(device)
    try:
        db.session.commit()
        current_app.logger.info(f"Deleted device {device.name} (ID: {id}) and associated logs via cascade.")
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting device {id}: {e}", exc_info=True)
        return jsonify({"error": "Failed to delete device", "message": str(e)}), 500

    return jsonify({"message": "Device and associated logs deleted successfully"}), 200

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
    """Enable or disable remote logging on the device."""
    device = db.session.get(Device, id)
    if not device:
        return jsonify({"error": "Device not found"}), 404

    data = request.get_json()
    if not data or 'enable' not in data or not isinstance(data['enable'], bool):
        return jsonify({"error": "Missing or invalid 'enable' field (must be boolean)"}), 400

    enable_logging = data['enable']

    # --- Ensure we have SSH controller and credential --- #
    if device.control_method != 'ssh':
         return jsonify({"error": f"Remote log configuration only supported via SSH, not '{device.control_method}'."}), 501
    if not device.credential:
        return jsonify({"error": "Device has no associated credential for SSH access."}), 400

    # --- Determine Target IP for logging --- #
    target_ip = os.environ.get('SYSLOG_SERVER_IP')
    if enable_logging and not target_ip:
         current_app.logger.error("Cannot enable remote logging: SYSLOG_SERVER_IP is not configured in the backend environment.")
         return jsonify({"error": "Backend SYSLOG_SERVER_IP configuration missing."}), 500
    
    # Read port directly from environment or use default
    target_port_str = os.environ.get('SYSLOG_UDP_PORT', '514')
    try:
        target_port = int(target_port_str)
    except ValueError:
        current_app.logger.warning(f"Invalid SYSLOG_UDP_PORT '{target_port_str}' in environment, using default 514.")
        target_port = 514

    # --- Build UCI commands --- #
    uci_commands = []
    section = LOGD_CONFIG['section'] # e.g., 'system.@system[0]'
    config_file_name = section.split('.')[0] # e.g., 'system'
    opt_ip = LOGD_CONFIG['option_log_ip']
    opt_port = LOGD_CONFIG['option_log_port']
    opt_proto = LOGD_CONFIG['option_log_proto']

    if enable_logging:
        uci_commands.extend([
            f"uci set {section}.{opt_ip}='{target_ip}'",
            f"uci set {section}.{opt_port}='{target_port}'",
            f"uci set {section}.{opt_proto}='udp'",
            f"uci commit {config_file_name}"
        ])
    else:
        uci_commands.extend([
            f"uci delete {section}.{opt_ip}",
            f"uci delete {section}.{opt_port}",
            f"uci delete {section}.{opt_proto}",
            f"uci commit {config_file_name}"
        ])

    # Reload logd service to apply changes
    restart_command = "/etc/init.d/log reload"
    uci_commands.append(restart_command)

    # --- Execute using Controller --- #
    try:
        controller = get_device_controller(device)

        if not hasattr(controller, 'execute_commands'):
             return jsonify({"error": "Internal error: Controller does not support command execution."}), 500

        current_app.logger.info(f"Attempting to {'enable' if enable_logging else 'disable'} remote logging on {device.name} ({device.ip_address})")
        execution_result = controller.execute_commands(uci_commands)

        if execution_result.get('error'):
            current_app.logger.error(f"Failed to apply log config changes to {device.name}: {execution_result['error']}")
            return jsonify({"error": "Failed to execute commands on device", "details": execution_result['error']}), 500
        
        # Consider checking execution_result['output'] for specific UCI or service errors if needed
        current_app.logger.info(f"Log config commands executed on {device.name}. Output:\n{execution_result.get('output')}")

        # --- Verify the actual state AFTER applying --- #
        current_app.logger.info(f"Verifying log config state on {device.name} after applying changes.")
        config_key_to_check = f"{section}.{opt_ip}"
        verify_result = controller.get_config(config_key_to_check)

        final_enabled_state = False
        final_target_ip = None
        if verify_result.get("success"):
            retrieved_ip = verify_result.get("value")
            # Check if the retrieved IP is non-empty
            if retrieved_ip and isinstance(retrieved_ip, str) and retrieved_ip.strip():
                final_enabled_state = True
                final_target_ip = retrieved_ip.strip()
            current_app.logger.info(f"Verification result for {device.name}: Success, log_ip='{final_target_ip}' -> Enabled={final_enabled_state}")
        else:
            # If verification failed, log it, but proceed cautiously.
            # Assume the operation succeeded if SSH execution didn't report an error.
            current_app.logger.warning(f"Verification of log config failed for {device.name} after applying changes. Error: {verify_result.get('message')}. Assuming intended state.")
            final_enabled_state = enable_logging
            final_target_ip = target_ip if enable_logging else None

        # --- Return the Correct JSON Structure --- #
        return jsonify({
            "remote_logging_enabled": final_enabled_state,
            "remote_log_target": final_target_ip
        }), 200

    except (ValueError, TypeError, NotImplementedError) as e:
        current_app.logger.error(f"Controller error setting log config for {device.name}: {e}")
        return jsonify({"error": f"Configuration error: {e}"}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error setting log config for {device.name}: {e}", exc_info=True)
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
        except DatabaseError as db_e:
            db.session.rollback()
            # Log the specific error db_e here
            error_message = f"Verification attempt resulted in message {check_result.get('message')}, but failed to save status update: {db_e}"
            return jsonify({
                "error": "Database error during status update after verification.",
                "message": error_message
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

# --- Credential Verification (Moved to Device) --- #

@api.route('/devices/<int:id>/verify_credential', methods=['POST'])
@login_required
def post_verify_device_credential(id):
    """Verify the SSH connection for the credential associated with this device."""
    device = db.session.get(Device, id)
    if not device:
        return jsonify({"error": "Device not found"}), 404
    
    if not device.credential:
        return jsonify({"error": "Device has no associated credential to verify"}), 400
        
    credential = device.credential
    
    # Use the existing SSH Manager service logic
    success, message = verify_ssh_connection(device, credential)

    # Update device status based on verification result?
    original_status = device.status
    status_changed = False
    if success:
        if device.status != 'Online': # Update only if not already Online
            device.status = 'Online' 
            device.last_seen = datetime.datetime.utcnow()
            status_changed = True
    else:
        if device.status != 'Offline': # Update only if not already Offline
             device.status = 'Offline'
             status_changed = True

    if status_changed:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"DB error updating status after verification for device {id}: {e}")
            # Proceed to return verification result even if DB update failed

    if success:
        return jsonify({"status": "success", "message": message})
    else:
        # Return 400 Bad Request on verification failure, including the reason
        return jsonify({"status": "failure", "message": message}), 400

# --- End Credential Verification --- # 