import abc
from flask import current_app
from ..models import Device, Credential
from . import ssh_manager
import datetime

class DeviceController(abc.ABC):
    """Abstract base class for controlling a device."""

    def __init__(self, device: Device, credential: Credential = None):
        if not device:
            raise ValueError("Device instance is required for a controller.")
        self.device = device
        # Credentials might not be needed for all methods or controllers (e.g., REST with token auth stored elsewhere)
        # But SSH controller definitely needs them.
        self.credential = credential 

    @abc.abstractmethod
    def apply_config(self, config_data) -> dict:
        """Apply configuration to the device. 
        
        Args:
            config_data: Configuration details (format depends on implementation, 
                         e.g., list of UCI commands for SSH, dict/JSON for REST).

        Returns:
            dict: {"success": bool, "message": str, "stdout": str, "stderr": str}
        """
        pass

    @abc.abstractmethod
    def get_config(self, config_key: str) -> dict:
        """Get a specific configuration value from the device.

        Args:
            config_key: Identifier for the configuration to retrieve (e.g., UCI path).
        
        Returns:
            dict: {"success": bool, "message": str, "value": any}
        """
        pass

    @abc.abstractmethod
    def reboot(self) -> dict:
        """Reboot the device.

        Returns:
            dict: {"success": bool, "message": str}
        """
        pass

    @abc.abstractmethod
    def check_status(self) -> dict:
        """Check the device's status.

        Returns:
            dict: {"success": bool, "message": str, "status": str, "last_seen": datetime | None}
                  The 'last_seen' field should be a datetime object if successful, None otherwise.
                  The 'status' field indicates the determined status (e.g., 'Verified', 'Verification Failed').
        """
        pass

    # Optional method for restarting services
    def restart_service(self, service_name: str) -> dict:
        """(Optional) Restart a specific service on the device.
        
        Args:
            service_name: The name of the service to restart (e.g., 'log', 'network').
            
        Returns:
            dict: {"success": bool, "message": str, "stdout": str, "stderr": str}
        """
        # Default implementation indicates not supported
        current_app.logger.warning(f"Restart for service '{service_name}' requested, but not implemented for controller type {type(self).__name__}")
        return {
            "success": False, 
            "message": f"Service restart not implemented for this controller.", 
            "stdout": "", 
            "stderr": "Not Implemented"
        }

# --- Concrete Implementations ---

class SSHDeviceController(DeviceController):
    """Controls a device using SSH commands (primarily UCI)."""

    def __init__(self, device: Device, credential: Credential):
        super().__init__(device, credential)
        if not self.credential:
            raise ValueError("SSH Controller requires valid credentials.")

    def apply_config(self, config_data) -> dict:
        if not isinstance(config_data, list):
            # Currently expects a list of UCI commands
            raise TypeError("SSHController apply_config expects a list of UCI command strings.")
        
        current_app.logger.debug(f"SSHController: Applying config to {self.device.ip_address} via SSH: {config_data}")
        result = ssh_manager.apply_uci_commands(self.device, self.credential, config_data)
        return result 

    def get_config(self, config_key: str) -> dict:
        current_app.logger.debug(f"SSHController: Getting config key '{config_key}' from {self.device.ip_address} via SSH")
        try:
            value = ssh_manager.get_uci_option(self.device, self.credential, config_key)
            return {"success": True, "message": "Config retrieved successfully.", "value": value}
        except ValueError as e: 
            current_app.logger.error(f"SSHController get_config error for {self.device.ip_address}: {e}")
            return {"success": False, "message": str(e), "value": None}
        except RuntimeError as e: 
            current_app.logger.error(f"SSHController get_config error for {self.device.ip_address}: {e}")
            return {"success": False, "message": str(e), "value": None}
        except Exception as e:
            current_app.logger.error(f"SSHController get_config unexpected error for {self.device.ip_address}: {e}", exc_info=True)
            return {"success": False, "message": f"An unexpected error occurred: {e}", "value": None}

    def reboot(self) -> dict:
        current_app.logger.debug(f"SSHController: Sending reboot command to {self.device.ip_address} via SSH")
        result = ssh_manager.reboot_device(self.device, self.credential)
        return result 

    def check_status(self) -> dict:
        current_app.logger.debug(f"SSHController: Checking status of {self.device.ip_address} via SSH verify")
        success, message = ssh_manager.verify_ssh_connection(self.device, self.credential)
        
        # Determine status and last_seen based *only* on verification result
        status = 'Verified' if success else 'Verification Failed'
        last_seen = datetime.datetime.utcnow() if success else None # Explicitly None on failure
        
        return {"success": success, "message": message, "status": status, "last_seen": last_seen}

    def restart_service(self, service_name: str) -> dict:
        """Restart a service using OpenWRT's /etc/init.d/ script via SSH."""
        # Basic validation/mapping could be added here
        valid_services = ['log', 'network', 'firewall'] # Example
        if service_name not in valid_services:
             current_app.logger.warning(f"SSHController: Invalid service name '{service_name}' requested for restart.")
             return {"success": False, "message": f"Invalid service name: {service_name}", "stdout": "", "stderr": "Invalid Service"}
        
        command = f"/etc/init.d/{service_name} restart"
        current_app.logger.info(f"SSHController: Attempting to restart service '{service_name}' on {self.device.ip_address} via SSH")
        
        # Use execute_ssh_command from ssh_manager
        result = ssh_manager.execute_ssh_command(self.device, self.credential, command)
        
        # Add a clearer message based on success/failure
        if result.get("success"):
            result["message"] = f"Service '{service_name}' restart command sent successfully."
        else:
             result["message"] = f"Service '{service_name}' restart command failed. Stderr: {result.get('stderr', 'N/A')}"
        
        return result # execute_ssh_command should return the required dict structure

    def execute_commands(self, commands: list, timeout=60) -> dict:
        """Executes a list of arbitrary commands sequentially via SSH.
        Args:
            commands: A list of command strings.
            timeout: Timeout for the entire operation.
        Returns:
            A dictionary: {'output': combined stdout/stderr string, 'error': error message or None}
        """
        current_app.logger.debug(f"SSHController: Executing arbitrary commands on {self.device.ip_address} via SSH")
        # Directly call the function in ssh_manager
        result = ssh_manager.execute_commands(self.device, self.credential, commands, timeout=timeout)
        return result

# --- (Placeholder for future REST implementation) ---
# class RESTDeviceController(DeviceController):
#     def __init__(self, device: Device):
#         super().__init__(device)
#         # Maybe get API key from device.custom_config or a separate credential store?
#         self.api_base_url = f"http://{self.device.ip_address}/api" # Example
#         self.api_key = self.device.get_api_key() # Hypothetical
# 
#     def apply_config(self, config_data: dict) -> dict:
#         # Make POST/PUT request to device's REST API endpoint
#         # import requests
#         # try:
#         #     response = requests.post(f"{self.api_base_url}/config", json=config_data, headers={"X-API-Key": self.api_key}, timeout=10)
#         #     response.raise_for_status()
#         #     return {"success": True, "message": "REST config applied.", "stdout": response.text, "stderr": ""}
#         # except requests.exceptions.RequestException as e:
#         #     return {"success": False, "message": str(e), "stdout": "", "stderr": str(e)}
#         raise NotImplementedError("RESTController apply_config not implemented.")
# 
#     def get_config(self, config_key: str) -> dict:
#         # Make GET request to device's REST API endpoint
#         # import requests
#         # try:
#         #     response = requests.get(f"{self.api_base_url}/config/{config_key}", headers={"X-API-Key": self.api_key}, timeout=5)
#         #     response.raise_for_status()
#         #     return {"success": True, "message": "REST config retrieved.", "value": response.json().get('value')}
#         # except requests.exceptions.RequestException as e:
#         #     return {"success": False, "message": str(e), "value": None}
#         raise NotImplementedError("RESTController get_config not implemented.")
# 
#     def reboot(self) -> dict:
#         # Make POST request to device's REST API reboot endpoint
#         # ...
#         raise NotImplementedError("RESTController reboot not implemented.")
# 
#     def check_status(self) -> dict:
#         # Make GET request to device's REST API status endpoint (ping?)
#         # ...
#         raise NotImplementedError("RESTController check_status not implemented.")


# --- Controller Factory ---

def get_device_controller(device: Device) -> DeviceController:
    """Factory function to get the appropriate controller for a device."""
    
    if not device:
        raise ValueError("Cannot get controller for a null device.")

    method = getattr(device, 'control_method', 'ssh') # Default to SSH if field doesn't exist yet

    if method == 'ssh':
        if not device.credential:
             raise ValueError(f"Device '{device.name}' uses SSH control method but has no associated credential.")
        current_app.logger.debug(f"Creating SSHDeviceController for {device.name}")
        return SSHDeviceController(device, device.credential)
    # elif method == 'rest':
    #     current_app.logger.debug(f"Creating RESTDeviceController for {device.name}")
    #     # Check if necessary REST credentials/config exist for the device
    #     # if not device.has_rest_credentials(): 
    #     #    raise ValueError(f"Device '{device.name}' uses REST control method but is missing REST credentials/config.")
    #     # return RESTDeviceController(device)
    #     raise NotImplementedError(f"Control method 'rest' is not yet implemented.")
    else:
        raise ValueError(f"Unknown control method '{method}' specified for device '{device.name}'.") 