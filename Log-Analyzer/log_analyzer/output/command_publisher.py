import logging
import paho.mqtt.client as paho_mqtt
from typing import Dict, Any, Optional
import json
import ssl
import queue
import threading

from ..monitoring.metrics import COMMANDS_PUBLISHED, COMMANDS_BLOCKED # Import metrics

logger = logging.getLogger(__name__)

# Expected format for analysis results that trigger commands:
# {
#     "_analyzer_name": "SomeAnalyzer",
#     "action": "set_config",
#     "target_device_id": "device123", # Optional, derived from log topic or data
#     "uci_commands": [
#         "set wireless.radio0.channel=11",
#         "set network.lan.ipaddr=192.168.1.2"
#     ]
# }

class CommandPublisher:
    """Handles formatting and publishing UCI commands via MQTT."""

    def __init__(self, config: Dict[str, Any], input_queue: queue.Queue):
        """Initializes the command publisher.

        Args:
            config: Dictionary containing command output configuration (type, host, port, topic, etc.).
            input_queue: Queue from which analysis results triggering commands are read.
        """
        self.config = config
        self.input_queue = input_queue
        self.mqtt_config = config.get('mqtt', {}) # Assuming nested config for MQTT output
        self.client: Optional[paho_mqtt.Client] = None
        self.allowed_commands: Optional[list] = self.config.get('allowed_command_prefixes') # For validation
        self.thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()

        if self.config.get('type') == 'mqtt':
            self._setup_mqtt_client()
        else:
            logger.warning("Command output type not configured or not 'mqtt'. Publisher disabled.")

    def _setup_mqtt_client(self):
        """Configures the internal MQTT client for publishing."""
        if not self.mqtt_config.get('host'):
            logger.warning("MQTT host not configured for command output. Publisher disabled.")
            return

        self.client = paho_mqtt.Client(client_id=self.mqtt_config.get('client_id', "log_analyzer_publisher"))
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        # self.client.on_publish = self._on_publish # Optional callback

        username = self.mqtt_config.get('username')
        password = self.mqtt_config.get('password')
        if username:
            self.client.username_pw_set(username, password)

        if self.mqtt_config.get('tls_enabled', False):
            # Similar TLS setup as the subscriber client
            ca_certs = self.mqtt_config.get('tls_ca_certs')
            certfile = self.mqtt_config.get('tls_certfile')
            keyfile = self.mqtt_config.get('tls_keyfile')
            self.client.tls_set(
                ca_certs=ca_certs, certfile=certfile, keyfile=keyfile,
                cert_reqs=ssl.CERT_REQUIRED if ca_certs else ssl.CERT_NONE,
                tls_version=ssl.PROTOCOL_TLSv1_2
            )
        logger.info("MQTT client configured for command publishing.")

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"Command publisher connected to MQTT broker at {self.mqtt_config['host']}")
        else:
            logger.error(f"Command publisher failed to connect to MQTT broker. RC: {rc}")

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning("Command publisher unexpectedly disconnected from MQTT.")
        else:
            logger.info("Command publisher disconnected gracefully.")

    def _validate_command(self, command: str) -> bool:
        """Checks if a command is allowed based on configured prefixes."""
        if self.allowed_commands is None: # If not configured, allow all (less secure)
            return True
        for prefix in self.allowed_commands:
            if command.startswith(prefix):
                return True
        logger.warning(f"Command blocked by validation rule: {command}")
        COMMANDS_BLOCKED.inc() # Increment metric
        return False

    def _publish_command(self, target_device_id: str, uci_command: str):
        """Publishes a single validated UCI command to the appropriate topic."""
        if not self.client or not self.client.is_connected():
            logger.error("Command publisher MQTT client not connected. Cannot publish.")
            return
        if not self._validate_command(uci_command):
            return # Validation failed, metric incremented in _validate_command

        topic = f"{self.mqtt_config.get('topic_prefix', 'log_analyzer/commands')}/{target_device_id}"
        qos = self.mqtt_config.get('qos', 1)
        retain = self.mqtt_config.get('retain', False)

        try:
            # Publish the raw UCI command string
            msg_info = self.client.publish(topic, payload=uci_command.encode('utf-8'), qos=qos, retain=retain)
            logger.info(f"Published command to {topic}: {uci_command}")
            # msg_info.wait_for_publish() # Optional: block until published
        except Exception as e:
            logger.error(f"Failed to publish command to {topic}: {e}")

    def _worker_loop(self):
        """Worker thread to consume analysis results and publish commands."""
        logger.info(f"Command publisher worker {threading.current_thread().name} started.")
        while not self.stop_event.is_set():
            try:
                analysis_result = self.input_queue.get(block=True, timeout=1.0)
                logger.debug(f"Publisher worker processing result: {analysis_result}")

                # Check if this result triggers a command
                if isinstance(analysis_result, dict) and analysis_result.get('action') == 'set_config':
                    target_device = analysis_result.get('target_device_id')
                    uci_commands = analysis_result.get('uci_commands')

                    if not target_device:
                        logger.warning(f"Command action received without target_device_id: {analysis_result}")
                        continue
                    if not isinstance(uci_commands, list):
                        logger.warning(f"Invalid uci_commands format in result: {analysis_result}")
                        continue

                    for command in uci_commands:
                        if isinstance(command, str):
                            self._publish_command(target_device, command)
                        else:
                            logger.warning(f"Ignoring non-string command in list: {command}")

                self.input_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Error in command publisher worker loop: {e}", exc_info=True)
        logger.info(f"Command publisher worker {threading.current_thread().name} stopped.")

    def start(self):
        """Connects the MQTT client and starts the worker thread."""
        if not self.client:
            return # Not configured

        try:
            host = self.mqtt_config['host']
            port = self.mqtt_config.get('port', 1883)
            self.client.connect_async(host, port, keepalive=60)
            self.client.loop_start()

            self.thread = threading.Thread(target=self._worker_loop, name="CommandPublisherWorker", daemon=True)
            self.thread.start()
            logger.info("Command publisher started.")
        except Exception as e:
            logger.error(f"Failed to start command publisher: {e}")
            if self.client.is_connected():
                self.client.loop_stop()
                self.client.disconnect()

    def stop(self):
        """Stops the worker thread and disconnects the MQTT client."""
        logger.info("Stopping command publisher...")
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=5.0)
        if self.client and self.client.is_connected():
            self.client.loop_stop()
            self.client.disconnect()
        logger.info("Command publisher stopped.") 