import pytest
import paho.mqtt.client as paho_mqtt
import time
import threading
import queue
import yaml
import logging
from typing import List, Tuple, Dict, Any

from log_analyzer.core.config import load_config
from log_analyzer.ingestion.mqtt_client import MQTTClient
from log_analyzer.parsing.parser import LogParser
from log_analyzer.output.command_publisher import CommandPublisher

# Configure logging for tests
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Test Configuration ---
BROKER_HOST = "localhost"
BROKER_PORT = 1883
INGEST_TOPIC_PREFIX = "test/loganalyzer/ingest"
COMMAND_TOPIC_PREFIX = "test/loganalyzer/commands"
TEST_TIMEOUT = 10 # Seconds to wait for messages

# Minimal config for testing MQTT
TEST_CONFIG_YAML = f"""
message_queue:
  type: mqtt
  host: {BROKER_HOST}
  port: {BROKER_PORT}
  topic_prefix: {INGEST_TOPIC_PREFIX}
  qos: 1
  client_id: log_analyzer_test_subscriber

parsing:
  rules: # Need at least one rule for handle_incoming_log to proceed
    - name: catch_all
      pattern: '^(?P<message>.*)$'

command_output:
  type: mqtt
  allowed_command_prefixes: # Allow test commands
    - "test_set"
  mqtt:
    host: {BROKER_HOST}
    port: {BROKER_PORT}
    topic_prefix: {COMMAND_TOPIC_PREFIX}
    qos: 1
    client_id: log_analyzer_test_publisher
"""

@pytest.fixture(scope="module")
def test_config_file(tmp_path_factory):
    """Creates a temporary config file for tests."""
    config_content = TEST_CONFIG_YAML
    p = tmp_path_factory.mktemp("config") / "test_config.yaml"
    p.write_text(config_content)
    logger.info(f"Created test config file at: {p}")
    return p

@pytest.fixture(scope="module")
def test_config(test_config_file):
    """Loads the temporary test configuration."""
    return load_config(str(test_config_file))

@pytest.fixture
def mqtt_helper_client():
    """Provides a generic MQTT client for test publishing/subscribing."""
    client = paho_mqtt.Client()
    client.connect(BROKER_HOST, BROKER_PORT, 60)
    client.loop_start()
    logger.info("MQTT Helper client connected and loop started.")
    yield client
    client.loop_stop()
    client.disconnect()
    logger.info("MQTT Helper client disconnected.")

# --- Test Ingestion --- #

# Use a thread-safe list or queue to store received messages
received_logs_for_test: List[Tuple[str, bytes]] = []
received_logs_lock = threading.Lock()

def test_log_handler(topic: str, payload: bytes):
    """Specific handler for ingestion test."""
    logger.info(f"[Test Handler] Received message on topic: {topic}")
    with received_logs_lock:
        received_logs_for_test.append((topic, payload))

@pytest.mark.integration
def test_log_ingestion(test_config, mqtt_helper_client):
    """Tests if the service subscribes and receives MQTT logs."""
    # Clear previous test data
    with received_logs_lock:
        received_logs_for_test.clear()

    # Setup MQTTClient with the test handler
    mqtt_config = test_config.get('message_queue', {})
    ingestion_client = MQTTClient(mqtt_config, test_log_handler)
    ingestion_client.connect() # Starts loop in background thread

    # Wait briefly for connection and subscription to establish
    time.sleep(2)
    assert ingestion_client.client.is_connected()

    # Publish a test message using the helper client
    test_topic = f"{INGEST_TOPIC_PREFIX}/device1"
    test_payload = b"This is a test log line from integration test"
    logger.info(f"Publishing test log to {test_topic}")
    mqtt_helper_client.publish(test_topic, payload=test_payload, qos=1)

    # Wait for the message to be received by the test handler
    received = False
    start_time = time.time()
    while time.time() - start_time < TEST_TIMEOUT:
        with received_logs_lock:
            if received_logs_for_test:
                topic, payload = received_logs_for_test[0]
                assert topic == test_topic
                assert payload == test_payload
                received = True
                break
        time.sleep(0.1)

    # Cleanup
    ingestion_client.disconnect()

    assert received, f"Test log message not received within {TEST_TIMEOUT}s"
    logger.info("Log ingestion test passed.")

# --- Test Command Publication --- #

received_commands_for_test: List[Tuple[str, bytes]] = []
received_commands_event = threading.Event()

def command_message_callback(client, userdata, msg):
    """Callback for the helper client subscribing to commands."""
    logger.info(f"[Command Subscriber] Received command on {msg.topic}: {msg.payload}")
    with received_logs_lock: # Reuse lock for simplicity
        received_commands_for_test.append((msg.topic, msg.payload))
    received_commands_event.set() # Signal that a message was received

@pytest.mark.integration
def test_command_publication(test_config, mqtt_helper_client):
    """Tests if the CommandPublisher publishes commands correctly."""
    # Clear previous test data
    with received_logs_lock:
        received_commands_for_test.clear()
    received_commands_event.clear()

    # Setup CommandPublisher (needs an input queue)
    analysis_results_queue = queue.Queue()
    cmd_config = test_config.get('command_output', {})
    publisher = CommandPublisher(cmd_config, analysis_results_queue)
    publisher.start() # Connects and starts worker thread

    # Setup helper client to subscribe to command topic
    target_device = "test_device_cmd"
    command_topic_to_sub = f"{COMMAND_TOPIC_PREFIX}/{target_device}"
    mqtt_helper_client.on_message = command_message_callback
    mqtt_helper_client.subscribe(command_topic_to_sub, qos=1)
    logger.info(f"Helper client subscribed to {command_topic_to_sub}")

    # Wait briefly for connections
    time.sleep(2)
    assert publisher.client and publisher.client.is_connected()

    # Create a command-triggering analysis result and queue it
    test_command = "test_set system.led=1"
    analysis_result = {
        "_analyzer_name": "TestAnalyzer",
        "action": "set_config",
        "target_device_id": target_device,
        "uci_commands": [test_command, "invalid start command"]
    }
    logger.info(f"Queuing analysis result to trigger command: {analysis_result}")
    analysis_results_queue.put(analysis_result)

    # Wait for the command message to be received by the helper subscriber
    published = received_commands_event.wait(timeout=TEST_TIMEOUT)

    # Cleanup
    publisher.stop()
    mqtt_helper_client.unsubscribe(command_topic_to_sub)

    assert published, f"Command message not received on {command_topic_to_sub} within {TEST_TIMEOUT}s"

    # Verify received command
    with received_logs_lock:
        assert len(received_commands_for_test) == 1 # Only valid command should be published
        topic, payload = received_commands_for_test[0]
        assert topic == command_topic_to_sub
        assert payload.decode('utf-8') == test_command

    logger.info("Command publication test passed.") 