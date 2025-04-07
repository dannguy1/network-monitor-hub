import paramiko
import io
from flask import current_app
import socket
import time
import re

DEFAULT_SSH_TIMEOUT = 10 # seconds
DEFAULT_SSH_PORT = 22

def _create_ssh_client(device, credential):
    """Helper function to create and configure a Paramiko SSH client."""
    client = None # Initialize client to None for finally block
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ssh_port = DEFAULT_SSH_PORT # Could make this configurable per device later
        timeout = current_app.config.get('SSH_TIMEOUT', DEFAULT_SSH_TIMEOUT)

        connection_args = {
            'hostname': device.ip_address,
            'port': ssh_port,
            'username': credential.ssh_username,
            'timeout': timeout,
            'allow_agent': False,
            'look_for_keys': False
        }

        if credential.auth_type == 'password':
            password = credential.password
            if not password or password == "<DECRYPTION_ERROR>":
                current_app.logger.error(f"SSH Connection failed for {device.ip_address}: Password missing or decryption failed for credential ID {credential.id}")
                raise ValueError("Password required but missing or failed to decrypt.")
            connection_args['password'] = password
        elif credential.auth_type == 'key':
            private_key_str = credential.private_key
            if not private_key_str or private_key_str == "<DECRYPTION_ERROR>":
                current_app.logger.error(f"SSH Connection failed for {device.ip_address}: Private key missing or decryption failed for credential ID {credential.id}")
                raise ValueError("Private key required but missing or failed to decrypt.")
            
            key_file = None
            pkey = None
            last_exception = None
            try:
                key_file = io.StringIO(private_key_str)
                key_types = [paramiko.Ed25519Key, paramiko.ECDSAKey, paramiko.RSAKey, paramiko.DSSKey] # Order preference
                
                for key_type in key_types:
                    try:
                        key_file.seek(0)
                        pkey = key_type.from_private_key(key_file)
                        current_app.logger.debug(f"Loaded private key as {key_type.__name__} for {device.ip_address}")
                        break
                    except paramiko.SSHException:
                        continue # Try next key type
                    except Exception as inner_e: # Catch other potential errors during key loading
                        last_exception = inner_e
                        continue
                
                if pkey is None:
                    log_msg = f"Failed to load private key for {device.ip_address} (cred ID: {credential.id}). Tried types: {[k.__name__ for k in key_types]}."
                    if last_exception:
                        log_msg += f" Last error: {last_exception}"
                    current_app.logger.error(log_msg)
                    raise paramiko.SSHException("Failed to load private key from string (unsupported format or corrupted?).")
                
                connection_args['pkey'] = pkey
            except Exception as e:
                # Catch potential errors from io.StringIO or other unexpected issues
                current_app.logger.error(f"Unexpected error processing private key string for {device.ip_address} (cred ID: {credential.id}): {e}")
                raise ValueError(f"Failed processing private key string: {e}")
            finally:
                 # Although StringIO doesn't strictly need closing, it's good practice if file handling were used
                 if key_file:
                     pass # key_file.close() if it were a real file
        else:
            current_app.logger.error(f"Unsupported authentication type '{credential.auth_type}' for {device.ip_address} (cred ID: {credential.id})")
            raise ValueError(f"Unsupported authentication type: {credential.auth_type}")

        current_app.logger.info(f"Attempting SSH connection to {device.ip_address}:{ssh_port} as {credential.ssh_username} (timeout: {timeout}s)")
        client.connect(**connection_args)
        current_app.logger.info(f"SSH connection established successfully to {device.ip_address}")
        return client
    except Exception as e:
         # Ensure client is closed if partially created before raising
         if client:
             client.close()
         # Re-raise the exception after logging or handling
         current_app.logger.error(f"_create_ssh_client failed for {device.ip_address}: {e}")
         raise # Re-raise the original exception

def verify_ssh_connection(device, credential):
    """Attempts to establish an SSH connection to verify credentials."""
    client = None
    start_time = time.time()
    log_prefix = f"SSH Verify for {device.ip_address} (CredID: {credential.id}):"
    try:
        client = _create_ssh_client(device, credential)
        stdin, stdout, stderr = client.exec_command('echo hello', timeout=5)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        duration = time.time() - start_time

        if exit_status == 0 and output == 'hello':
            current_app.logger.info(f"{log_prefix} Success in {duration:.2f}s")
            return True, f"Connection successful in {duration:.2f}s"
        else:
            error_message = f"Command execution failed. Exit={exit_status}, Out='{output}', Err='{err}'"
            current_app.logger.warning(f"{log_prefix} Failed. {error_message}")
            return False, error_message

    except paramiko.AuthenticationException as e:
        current_app.logger.warning(f"{log_prefix} Auth failed: {e}")
        return False, f"Authentication failed: {e}"
    except (paramiko.SSHException, socket.timeout, socket.error) as e:
        # Catch specific connection/protocol errors
        current_app.logger.warning(f"{log_prefix} Connection/SSH error: {e}")
        return False, f"Connection/SSH error: {e}"
    except ValueError as e:
        # Catch errors from _create_ssh_client related to creds/keys
        current_app.logger.error(f"{log_prefix} Configuration error: {e}")
        return False, f"Configuration error: {e}"
    except Exception as e:
        # Catch any other unexpected errors
        current_app.logger.error(f"{log_prefix} Unexpected error: {e}", exc_info=True) # Log traceback
        return False, f"Unexpected error during verification: {e}"
    finally:
        if client:
            client.close()

def execute_ssh_command(device, credential, command, timeout=15):
    """Executes a single command on the remote device via SSH."""
    client = None
    start_time = time.time()
    try:
        client = _create_ssh_client(device, credential)
        current_app.logger.info(f"Executing command on {device.ip_address}: '{command}'")
        stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
        exit_status = stdout.channel.recv_exit_status() # Wait for command to finish
        output = stdout.read().decode()
        error = stderr.read().decode()
        duration = time.time() - start_time
        current_app.logger.info(f"Command execution on {device.ip_address} finished in {duration:.2f}s. Exit status: {exit_status}")
        return {
            "success": exit_status == 0,
            "exit_status": exit_status,
            "stdout": output,
            "stderr": error,
            "duration_seconds": duration
        }
    except Exception as e:
        duration = time.time() - start_time
        current_app.logger.error(f"SSH command execution failed for {device.ip_address} (user: {credential.ssh_username}): {e}")
        return {
            "success": False,
            "exit_status": -1,
            "stdout": "",
            "stderr": f"Failed to execute command: {e}",
            "duration_seconds": duration
        }
    finally:
        if client:
            client.close()

def apply_uci_commands(device, credential, uci_commands):
    """Applies a list of UCI commands and commits them."""
    if not isinstance(uci_commands, list):
        return {"success": False, "stderr": "uci_commands must be a list of strings"}
    if not uci_commands:
        return {"success": True, "stdout": "No commands to apply.", "stderr": ""}

    # Combine UCI commands and add commit
    # Ensure proper quoting/escaping if necessary, though UCI usually handles simple values well.
    full_command = " && ".join(uci_commands) + " && uci commit"

    # Optional: Add service restart if needed, e.g.:
    # full_command += " && /etc/init.d/network restart" # Example

    result = execute_ssh_command(device, credential, full_command)

    if not result["success"]:
         current_app.logger.error(f"UCI apply failed for {device.ip_address}. Command: '{full_command}'. Error: {result['stderr']}")
         # Attempt to discard changes if commit might have failed mid-way or if earlier commands failed
         discard_result = execute_ssh_command(device, credential, "uci revert")
         current_app.logger.info(f"Attempted UCI revert for {device.ip_address} after failure. Result: {discard_result}")
         result["stderr"] += "\nAttempted to revert changes due to error."

    return result

def get_uci_option(device, credential, option_path):
    """Gets a single UCI option value from the remote device."""
    # Basic validation of option path format (prevent injection)
    if not re.match(r'^[a-zA-Z0-9_@.\[\]-]+$', option_path):
        raise ValueError(f"Invalid UCI option path format: {option_path}")
    
    command = f"uci get {option_path}"
    result = execute_ssh_command(device, credential, command, timeout=5) # Short timeout for get

    if result["success"]:
        # Return the standard output, stripped of whitespace (especially trailing newline)
        return result["stdout"].strip()
    else:
        # Check stderr for common "not found" errors
        if "Entry not found" in result["stderr"] or "No such section" in result["stderr"]:
            current_app.logger.debug(f"UCI option '{option_path}' not found on {device.ip_address}")
            return None # Option not set or doesn't exist
        else:
            # Log other errors but raise an exception to indicate failure
            current_app.logger.error(
                f"Failed to get UCI option '{option_path}' from {device.ip_address}. "
                f"Exit={result['exit_status']}, Stderr: {result['stderr']}"
            )
            raise RuntimeError(f"Failed to get UCI option: {result['stderr'] or 'Unknown error'}")

# --- Reboot Function ---
def reboot_device(device, credential):
    """Sends a reboot command to the specified device."""
    command = "reboot" # Standard reboot command
    # Use a short timeout as the connection will likely drop after the command succeeds
    result = execute_ssh_command(device, credential, command, timeout=5)

    # For reboot, success often means the command was issued, even if stderr has messages
    # or the connection drops before status is fully returned.
    # We consider it 'sent' if no immediate exception occurred and exit status isn't clearly an error.
    # Paramiko might raise an exception if the channel closes abruptly after reboot starts.
    
    # If an exception occurred during execute_ssh_command, result['success'] will be False.
    if not result.get("success", False) and result.get("stderr"):
         # Check for specific errors like 'command not found' or permission issues
         if "not found" in result["stderr"] or "permission denied" in result["stderr"]:
              current_app.logger.error(f"Reboot command failed on {device.ip_address}: {result['stderr']}")
              return {"success": False, "message": f"Reboot command failed: {result['stderr']}"}
         else:
            # Could be a connection drop due to reboot starting - might be okay
            current_app.logger.warning(f"Reboot command on {device.ip_address} potentially succeeded but connection closed or stderr received: {result['stderr']}")
            # We can consider this potentially successful if no critical error message is obvious
            return {"success": True, "message": f"Reboot command sent to {device.ip_address}, but confirmation unclear (stderr: {result['stderr']})."}

    elif result.get("exit_status", -1) != 0 and result.get("exit_status", -1) != -1 : # -1 is our internal error indicator
        current_app.logger.error(f"Reboot command failed on {device.ip_address} with exit status {result['exit_status']}. Stderr: {result.get('stderr','')}")
        return {"success": False, "message": f"Reboot command failed with exit status {result['exit_status']}."}
    else:
        # Assume success if execute_ssh_command reported success or if stderr is empty/connection dropped
        current_app.logger.info(f"Reboot command successfully sent to {device.ip_address}.")
        return {"success": True, "message": f"Reboot command sent successfully to {device.ip_address}."} 