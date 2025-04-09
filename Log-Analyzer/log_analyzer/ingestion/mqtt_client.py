import logging
import paho.mqtt.client as paho_mqtt
from typing import Callable, Dict, Any
import ssl

logger = logging.getLogger(__name__)

# Define a type for the callback function that processes messages
MessageHandler = Callable[[str, bytes], None]

class MQTTClient:
    """Handles connection and subscription to an MQTT broker."""

    def __init__(self, config: Dict[str, Any], message_handler: MessageHandler):
        """Initializes the MQTT client.

        Args:
            config: Dictionary containing MQTT configuration (host, port, topic, etc.).
            message_handler: A callback function to be called when a message is received.
                             It takes (topic: str, payload: bytes) as arguments.
        """
        if not config or config.get('type') != 'mqtt':
            raise ValueError("Invalid or missing MQTT configuration")

        self.config = config
        self.message_handler = message_handler
        self.client = paho_mqtt.Client(client_id=config.get('client_id', ""))
        self._configure_client()

    def _configure_client(self):
        """Sets up MQTT client callbacks and security options."""
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        self.client.on_log = self._on_log # Optional: for debugging paho-mqtt

        username = self.config.get('username')
        password = self.config.get('password')
        if username:
            self.client.username_pw_set(username, password)

        if self.config.get('tls_enabled', False):
            logger.info("Configuring TLS for MQTT connection")
            ca_certs = self.config.get('tls_ca_certs')
            certfile = self.config.get('tls_certfile')
            keyfile = self.config.get('tls_keyfile')
            # Basic TLS context, adjust as needed for specific requirements (e.g., cert validation)
            self.client.tls_set(
                ca_certs=ca_certs,
                certfile=certfile,
                keyfile=keyfile,
                cert_reqs=ssl.CERT_REQUIRED if ca_certs else ssl.CERT_NONE,
                tls_version=ssl.PROTOCOL_TLSv1_2 # Consider making this configurable
            )
            # Use tls_insecure_set(True) to skip hostname verification if needed (less secure)

    def _on_connect(self, client, userdata, flags, rc):
        """Callback executed when the client connects to the MQTT broker."""
        if rc == 0:
            logger.info(f"Successfully connected to MQTT broker at {self.config['host']}:{self.config['port']}")
            topic = f"{self.config.get('topic_prefix', 'network_monitor/logs')}/#"
            qos = self.config.get('qos', 1)
            logger.info(f"Subscribing to topic: {topic} with QoS: {qos}")
            try:
                client.subscribe(topic, qos=qos)
            except Exception as e:
                logger.error(f"Failed to subscribe to topic {topic}: {e}")
        else:
            logger.error(f"Failed to connect to MQTT broker. Return code: {rc} - {paho_mqtt.connack_string(rc)}")

    def _on_message(self, client, userdata, msg):
        """Callback executed when a message is received."""
        logger.debug(f"Received message on topic {msg.topic}")
        try:
            # Pass topic and raw payload to the handler
            self.message_handler(msg.topic, msg.payload)
        except Exception as e:
            logger.error(f"Error processing message from topic {msg.topic}: {e}", exc_info=True)

    def _on_disconnect(self, client, userdata, rc):
        """Callback executed when the client disconnects."""
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection. Return code: {rc}. Will attempt to reconnect.")
        else:
            logger.info("MQTT client disconnected gracefully.")

    def _on_log(self, client, userdata, level, buf):
         """Optional callback to log messages from the paho-mqtt library itself."""
         # Map paho levels to Python logging levels if desired
         # logger.debug(f"PAHO-MQTT LOG: {buf}")
         pass

    def connect(self):
        """Connects to the MQTT broker and starts the network loop."""
        host = self.config.get('host')
        port = self.config.get('port', 1883)
        if not host:
            logger.error("MQTT host not configured.")
            return

        logger.info(f"Attempting to connect to MQTT broker at {host}:{port}...")
        try:
            # connect_async allows for automatic reconnects if the connection drops
            self.client.connect_async(host, port, keepalive=60)
            # loop_start() runs the network loop in a separate thread
            self.client.loop_start()
            logger.info("MQTT client loop started.")
        except Exception as e:
            logger.error(f"Failed to initiate MQTT connection to {host}:{port}: {e}", exc_info=True)

    def disconnect(self):
        """Disconnects the client gracefully."""
        logger.info("Disconnecting MQTT client...")
        self.client.loop_stop() # Stop the network loop thread
        self.client.disconnect() 