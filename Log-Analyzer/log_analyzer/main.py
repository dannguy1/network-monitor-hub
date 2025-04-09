import logging
import time
import argparse
import queue

from .core.config import load_config
from .ingestion.mqtt_client import MQTTClient
from .parsing.parser import LogParser, transform_to_json
from .analysis.analyzer_manager import AnalyzerManager, analysis_result_queue
from .output.command_publisher import CommandPublisher
from .ui.app import run_web_server # Import UI runner
from .monitoring.metrics import ( # Import metrics components
    start_metrics_server, stop_metrics_server,
    LOGS_RECEIVED, LOGS_PARSED, LOGS_FAILED
)

# Queue for parsed logs, ready for AI processing
parsed_log_queue = queue.Queue(maxsize=1000)

# Global parser instance
log_parser = None

def handle_incoming_log(topic: str, payload: bytes):
    """Callback for handling received MQTT messages, parsing them, and queueing."""
    global log_parser # Access the global parser instance
    logger = logging.getLogger(__name__)
    LOGS_RECEIVED.labels(mqtt_topic=topic).inc()
    try:
        log_line = payload.decode('utf-8')
        logger.debug(f"Received log on topic {topic}: {log_line[:100]}...")

        if not log_parser:
            logger.warning("Log parser not initialized, skipping parsing.")
            LOGS_FAILED.labels(reason='parser_not_ready').inc()
            return

        parsed_result = log_parser.parse_log_line(log_line)

        if parsed_result:
            rule_name, parsed_data = parsed_result
            LOGS_PARSED.labels(parser_rule=rule_name).inc()
            # Add metadata
            parsed_data['_raw_log'] = log_line
            parsed_data['_topic'] = topic
            parsed_data['_parser_rule'] = rule_name
            # TODO: Add device ID extraction from topic?

            try:
                # Put the dictionary onto the queue for further processing
                parsed_log_queue.put(parsed_data, block=False) # Non-blocking
                logger.debug(f"Queued parsed log (Rule: {rule_name})")
            except queue.Full:
                logger.warning("Parsed log queue is full. Discarding log.")
                LOGS_FAILED.labels(reason='queue_full').inc()
        else:
            # Handle unparseable lines (maybe queue them separately?)
            logger.debug("Log line did not match any parsing rules.")
            LOGS_FAILED.labels(reason='no_match').inc()
            # Example: Queue unparsed lines elsewhere
            # unparsed_log_queue.put({"_raw_log": log_line, "_topic": topic})

    except UnicodeDecodeError:
        logger.warning(f"Failed to decode payload on topic {topic} as UTF-8.")
        LOGS_FAILED.labels(reason='decode_error').inc()
    except Exception as e:
        logger.error(f"Error in message handler for topic {topic}: {e}", exc_info=True)
        LOGS_FAILED.labels(reason='handler_exception').inc()

def main():
    """Main entry point for the Log Analyzer service."""
    global log_parser # Declare modification of global
    parser = argparse.ArgumentParser(description="OpenWRT Log Analyzer Service")
    parser.add_argument("-c", "--config", help="Path to configuration file", default=None)
    args = parser.parse_args()

    # Basic logging setup first, might be refined by config
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)

    logger.info("Starting Log Analyzer service...")

    config = None
    mqtt_client = None
    analyzer_manager = None
    command_publisher = None
    web_server_thread = None # Keep track of the thread

    try:
        config = load_config(args.config)
        # TODO: Apply log level from config if specified
        # if 'log_level' in config:
        #     logging.getLogger().setLevel(config['log_level'].upper())

    except FileNotFoundError:
        logger.error("Configuration file not found. Exiting.")
        return
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}. Exiting.")
        return

    # Initialize components
    try:
        # Start Metrics Server first (as it runs independently)
        start_metrics_server(9090, config)

        # Initialize Parser first
        if config.get('parsing') and 'rules' in config['parsing']:
            logger.info("Initializing Log Parser...")
            log_parser = LogParser(config['parsing']['rules'])
        else:
            logger.warning("Parsing rules not found in config. Parser will not be effective.")
            log_parser = LogParser([]) # Initialize with empty rules

        # Initialize Analyzer Manager
        logger.info("Initializing Analyzer Manager...")
        analyzer_manager = AnalyzerManager(config, parsed_log_queue)
        analyzer_manager.start_analysis()

        # Initialize Command Publisher (consumes from analysis_result_queue)
        if config.get('command_output'):
            logger.info("Initializing Command Publisher...")
            command_publisher = CommandPublisher(config['command_output'], analysis_result_queue)
            command_publisher.start()
        else:
            logger.warning("Command output not configured. Publisher disabled.")

        # Initialize MQTT Client (produces to parsed_log_queue via handler)
        if config.get('message_queue') and config['message_queue'].get('type') == 'mqtt':
            logger.info("Initializing MQTT client...")
            mqtt_client = MQTTClient(config['message_queue'], handle_incoming_log)
            mqtt_client.connect()
        else:
            logger.warning("MQTT message queue not configured or type is not 'mqtt'. Log ingestion disabled.")

        # Initialize Web Server (needs references to other components/queues for status)
        logger.info("Initializing Web Server...")
        config_file_path = args.config or 'config.yaml' # Determine config path used
        web_server_thread = run_web_server(
            config, config_file_path, # Pass config path
            parsed_log_queue, analysis_result_queue,
            log_parser, analyzer_manager, command_publisher, mqtt_client
        )

        # Initialize monitoring

    except Exception as e:
        logger.error(f"Error during service initialization: {e}", exc_info=True)
        # Cleanup partially initialized components
        if command_publisher:
            command_publisher.stop()
        if analyzer_manager:
            analyzer_manager.stop_analysis()
        if mqtt_client:
            mqtt_client.disconnect()
        stop_metrics_server() # Stop metrics server on init failure too
        return

    # Main loop
    try:
        logger.info("Service initialization complete. Entering main loop.")
        while True:
            # Check if essential threads are alive
            if mqtt_client and not mqtt_client.client.is_connected():
               logger.warning("MQTT Ingestion client appears disconnected.")
               # Add reconnection logic or health check here? Might be handled by paho loop.
            if web_server_thread and not web_server_thread.is_alive():
                logger.error("Web server thread has unexpectedly stopped!")
                # Attempt to restart? Or exit service?
                break # Exit for now
            # Add checks for analyzer/publisher threads if needed

            time.sleep(5) # Keep main thread alive

    except KeyboardInterrupt:
        logger.info("Shutdown signal received.")
    finally:
        logger.info("Initiating service shutdown...")
        # Stop components
        if command_publisher:
            command_publisher.stop()
        if analyzer_manager:
            analyzer_manager.stop_analysis()
        if mqtt_client:
            mqtt_client.disconnect()
        # Web server thread is daemon, should exit automatically
        # If using non-daemon threads or external process, add specific stop logic
        stop_metrics_server() # Stop metrics server
        logger.info("Log Analyzer service stopped.")

if __name__ == "__main__":
    main() 