import yaml
import logging
import os
from typing import Dict, Any

DEFAULT_CONFIG_PATH = 'config.yaml'

logger = logging.getLogger(__name__)

def load_config(config_path: str | None = None) -> Dict[str, Any]:
    """Loads configuration from a YAML file.

    Args:
        config_path: Path to the configuration file. Defaults to DEFAULT_CONFIG_PATH.

    Returns:
        A dictionary containing the configuration.

    Raises:
        FileNotFoundError: If the config file is not found.
        yaml.YAMLError: If the config file is invalid YAML.
        Exception: For other unexpected errors during loading.
    """
    path_to_load = config_path or DEFAULT_CONFIG_PATH
    logger.info(f"Attempting to load configuration from: {path_to_load}")

    if not os.path.exists(path_to_load):
        logger.error(f"Configuration file not found: {path_to_load}")
        # Create a default empty config file for guidance?
        # For now, raise error
        raise FileNotFoundError(f"Configuration file not found: {path_to_load}")

    try:
        with open(path_to_load, 'r') as f:
            config = yaml.safe_load(f)
        if config is None:
            logger.warning(f"Configuration file is empty: {path_to_load}")
            return {}
        logger.info(f"Configuration loaded successfully from: {path_to_load}")
        return config
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML file {path_to_load}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error loading configuration from {path_to_load}: {e}")
        raise

# Example structure for config.yaml (create this file in Log-Analyzer/)
"""
# Example config.yaml
log_level: INFO

message_queue:
  type: mqtt # or redis
  client_id: log_analyzer_client # Should be unique per instance if multiple analyzers run
  host: localhost
  port: 1883
  username: null # Set username if authentication is needed
  password: null # Set password if authentication is needed
  tls_enabled: false # Set to true if using TLS/SSL
  tls_ca_certs: null # Path to CA certificate file if tls_enabled=true
  tls_certfile: null # Path to client certificate file if using client cert auth
  tls_keyfile: null  # Path to client key file if using client cert auth
  topic_prefix: network_monitor/logs # Analyzer will subscribe to topic_prefix/#
  qos: 1 # Quality of Service level for subscription

parsing:
  rules:
    # Define parsing rules here - IMPORTANT: These are basic examples, refine with real logs!
    - name: syslog_generic
      # Example: Apr 10 12:34:56 hostname process[123]: message
      pattern: '^(?P<timestamp>\\w{3}\\s+\\d{1,2}\\s+\\d{2}:\\d{2}:\\d{2})\\s+(?P<hostname>\\S+)\\s+(?P<process>\\S+?)(?:\\[(?P<pid>\\d+)\\])?[:]?\\s*(?P<message>.*)$'
    - name: hostapd_assoc
      # Example: Tue Apr 09 02:55:56 2024 daemon.info hostapd: wlan0: STA ac:de:48:12:34:56 IEEE 802.11: associated
      pattern: '^(?:.*?)daemon\\.\\w+\\s+hostapd:\\s+(?P<interface>\\S+):\\s+STA\\s+(?P<mac_address>[0-9a-fA-F:]+)\\s+IEEE\\s+802\\.11:\\s+(?P<event_type>associated|disassociated.*)$'
    - name: dnsmasq_dhcp
      # Example: Tue Apr 09 02:55:56 2024 daemon.info dnsmasq-dhcp[1]: DHCPREQUEST(br-lan) 192.168.1.100 ac:de:48:12:34:56
      pattern: '^(?:.*?)daemon\\.\\w+\\s+dnsmasq-dhcp(?:\\S+)?:\s+(?P<event_type>DHCPREQUEST|DHCPACK|DHCPNAK|DHCPDISCOVER)\\((?P<interface>\\S+)\\)\\s+(?P<ip_address>[\\d\\.]+)\\s+(?P<mac_address>[0-9a-fA-F:]+)(?:\\s+(?P<hostname>\\S+))?.*$'
    # Add more rules for firewall events, etc.

ai_modules:
  enabled:
    - EventCounter
    # - SecurityMonitor
  # Optional: Specific configs per module
  configs:
    EventCounter:
      report_interval: 50 # Example config for the counter
  worker_threads: 2 # Number of threads processing logs for analysis

command_output:
  type: mqtt # Type of output mechanism (e.g., mqtt, http_post)
  allowed_command_prefixes: # Optional: Restrict allowed commands for security
    - "set wireless."
    - "set network."
    - "uci commit"
    - "reload_config"
  # MQTT specific settings if type is mqtt
  mqtt:
    client_id: log_analyzer_publisher
    host: localhost
    port: 1883
    username: null
    password: null
    tls_enabled: false
    tls_ca_certs: null
    topic_prefix: log_analyzer/commands # Base topic, device ID will be appended
    qos: 1
    retain: false

web_ui:
  enabled: true
  host: 0.0.0.0
  port: 8080
  username: admin # The username for UI login
  # password: "your_plain_password_here" # Set initially, will be hashed on first run
  password_hash: "" # Paste the generated hash here after first run (check logs) and remove plain password
  secret_key: "" # IMPORTANT: Generate a strong, random secret key (e.g., `openssl rand -hex 32`) and paste here

monitoring:
  enabled: true
  metrics_port: 9090

""" 