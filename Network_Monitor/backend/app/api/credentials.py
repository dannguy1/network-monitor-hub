from flask import request, jsonify, url_for, current_app
from . import api
from .. import db
from ..models import Credential, Device
from sqlalchemy.exc import IntegrityError

# --- Credential CRUD --- 

@api.route('/credentials', methods=['POST'])
def create_credential():
    """Create a new SSH credential set."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    name = data.get('name')
    ssh_username = data.get('ssh_username')
    auth_type = data.get('auth_type', 'password') # Default to password
    password = data.get('password')
    private_key = data.get('private_key')

    if not name or not ssh_username:
        return jsonify({"error": "Missing required fields: name and ssh_username"}), 400

    if auth_type == 'password' and not password:
        return jsonify({"error": "Password is required for auth_type 'password'"}), 400
    if auth_type == 'key' and not private_key:
        return jsonify({"error": "Private key is required for auth_type 'key'"}), 400
    if auth_type not in ['password', 'key']:
        return jsonify({"error": "Invalid auth_type. Must be 'password' or 'key'"}), 400

    if Credential.query.filter_by(name=name).first():
        return jsonify({"error": f"Credential set with name '{name}' already exists"}), 409

    credential = Credential(name=name, ssh_username=ssh_username)
    if auth_type == 'password':
        credential.password = password
    else:
        credential.private_key = private_key

    db.session.add(credential)
    try:
        db.session.commit()
    except ValueError as e:
         # Handle potential issues from encryption (e.g., missing key)
        db.session.rollback()
        current_app.logger.error(f"Credential creation error: {e}")
        return jsonify({"error": "Failed to create credential due to configuration issue", "message": str(e)}), 500
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({"error": "Database integrity error", "message": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Credential creation failed: {e}")
        return jsonify({"error": "Failed to create credential", "message": str(e)}), 500

    response = jsonify(credential.to_dict())
    response.status_code = 201
    response.headers['Location'] = url_for('api.get_credential', id=credential.id)
    return response

@api.route('/credentials', methods=['GET'])
def get_credentials():
    """Get a list of all credential sets."""
    credentials = Credential.query.order_by(Credential.name).all()
    return jsonify([c.to_dict() for c in credentials])

@api.route('/credentials/<int:id>', methods=['GET'])
def get_credential(id):
    """Get a single credential set by ID."""
    credential = db.session.get(Credential, id)
    if credential is None:
        return jsonify({"error": "Credential set not found"}), 404
    return jsonify(credential.to_dict())

@api.route('/credentials/<int:id>', methods=['PUT'])
def update_credential(id):
    """Update an existing credential set."""
    credential = db.session.get(Credential, id)
    if credential is None:
        return jsonify({"error": "Credential set not found"}), 404

    data = request.get_json()
    if not data:
        return jsonify({"error": "No input data provided"}), 400

    # Check for name conflict if changing name
    new_name = data.get('name')
    if new_name and new_name != credential.name and Credential.query.filter_by(name=new_name).first():
         return jsonify({"error": f"Credential set with name '{new_name}' already exists"}), 409

    credential.name = new_name or credential.name
    credential.ssh_username = data.get('ssh_username', credential.ssh_username)

    # Handle password/key update - only update if explicitly provided
    new_password = data.get('password')
    new_private_key = data.get('private_key')
    new_auth_type = data.get('auth_type')

    if new_auth_type and new_auth_type not in ['password', 'key']:
        return jsonify({"error": "Invalid auth_type. Must be 'password' or 'key'"}), 400

    if new_auth_type == 'password' or (not new_auth_type and credential.auth_type == 'password'):
        if 'password' in data: # Check if key exists, even if empty, to allow clearing
            credential.password = new_password # Setter handles encryption and type change
    elif new_auth_type == 'key' or (not new_auth_type and credential.auth_type == 'key'):
         if 'private_key' in data: # Check if key exists
            credential.private_key = new_private_key # Setter handles encryption and type change

    try:
        db.session.commit()
    except ValueError as e:
        db.session.rollback()
        current_app.logger.error(f"Credential update error: {e}")
        return jsonify({"error": "Failed to update credential due to configuration issue", "message": str(e)}), 500
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Credential update failed: {e}")
        return jsonify({"error": "Failed to update credential", "message": str(e)}), 500

    return jsonify(credential.to_dict())

@api.route('/credentials/<int:id>', methods=['DELETE'])
def delete_credential(id):
    """Delete a credential set."""
    credential = db.session.get(Credential, id)
    if credential is None:
        return jsonify({"error": "Credential set not found"}), 404

    # Prevent deletion if currently associated with a device
    if credential.device:
        return jsonify({
            "error": "Credential set is currently associated with a device",
            "device_id": credential.device.id,
            "device_name": credential.device.name
        }), 409

    db.session.delete(credential)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Credential deletion failed: {e}")
        return jsonify({"error": "Failed to delete credential set", "message": str(e)}), 500

    return jsonify({"message": "Credential set deleted successfully"}), 200

# --- Credential Association --- 

@api.route('/devices/<int:device_id>/credential/<int:credential_id>', methods=['POST'])
def associate_credential(device_id, credential_id):
    """Associate a credential set with a device."""
    device = db.session.get(Device, device_id)
    if not device:
        return jsonify({"error": "Device not found"}), 404

    credential = db.session.get(Credential, credential_id)
    if not credential:
        return jsonify({"error": "Credential set not found"}), 404

    # Check if credential is used by another device (optional, depends on desired sharing policy)
    if credential.device and credential.device.id != device_id:
         return jsonify({"error": f"Credential set is already associated with device '{credential.device.name}'"}), 409

    device.credential = credential
    # device.credential_id = credential_id # Relationship assigns this automatically
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to associate credential {credential_id} with device {device_id}: {e}")
        return jsonify({"error": "Failed to associate credential", "message": str(e)}), 500

    return jsonify({"message": f"Credential '{credential.name}' associated with device '{device.name}'"}), 200

@api.route('/devices/<int:device_id>/credential', methods=['DELETE'])
def disassociate_credential(device_id):
    """Disassociate any credential set from a device."""
    device = db.session.get(Device, device_id)
    if not device:
        return jsonify({"error": "Device not found"}), 404

    if not device.credential:
        return jsonify({"message": "Device has no associated credential set"}), 200

    credential_name = device.credential.name
    device.credential = None
    device.credential_id = None
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Failed to disassociate credential from device {device_id}: {e}")
        return jsonify({"error": "Failed to disassociate credential", "message": str(e)}), 500

    return jsonify({"message": f"Credential '{credential_name}' disassociated from device '{device.name}'"}), 200

# --- Credential Verification (Placeholder) --- 

@api.route('/credentials/<int:id>/verify', methods=['POST'])
def verify_credential(id):
    """Verify SSH connection using this credential set against its associated device."""
    credential = db.session.get(Credential, id)
    if not credential:
        return jsonify({"error": "Credential set not found"}), 404

    if not credential.device:
        return jsonify({"error": "Credential set is not associated with any device"}), 400

    device = credential.device
    
    # Use the SSH Manager service
    from ..services.ssh_manager import verify_ssh_connection
    success, message = verify_ssh_connection(device, credential)

    # Placeholder response
    # success = True # Replace with actual result
    # message = "Verification successful (Placeholder)" # Replace with actual result

    if success:
        # Optionally update device status
        device.status = 'Verified'
        try:
            db.session.commit()
        except Exception:
            db.session.rollback() # Log error but proceed
        return jsonify({"status": "success", "message": message})
    else:
        return jsonify({"status": "failure", "message": message}), 400 