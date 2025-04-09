import logging
from prometheus_client import start_http_server, Counter, Gauge, Histogram
import queue
import time
import threading
from typing import Dict, Any

logger = logging.getLogger(__name__)

# --- Metric Definitions ---

# Counter for received logs (can add labels like topic/device)
LOGS_RECEIVED = Counter(
    'loganalyzer_logs_received_total',
    'Total number of log lines received by the service',
    ['mqtt_topic'] # Label to distinguish source topic
)

# Counter for successfully parsed logs (can add label for rule name)
LOGS_PARSED = Counter(
    'loganalyzer_logs_parsed_total',
    'Total number of log lines successfully parsed',
    ['parser_rule'] # Label to distinguish which rule matched
)

# Counter for logs that failed parsing or decoding
LOGS_FAILED = Counter(
    'loganalyzer_logs_failed_total',
    'Total number of log lines that failed decoding or parsing',
    ['reason'] # e.g., 'decode_error', 'no_match'
)

# Gauge for current size of processing queues
PARSED_LOG_QUEUE_SIZE = Gauge(
    'loganalyzer_parsed_log_queue_size',
    'Current number of items in the parsed log queue'
)
ANALYSIS_RESULT_QUEUE_SIZE = Gauge(
    'loganalyzer_analysis_result_queue_size',
    'Current number of items in the analysis result queue'
)

# Counter for analysis results generated (can add label for analyzer name)
ANALYSIS_RESULTS = Counter(
    'loganalyzer_analysis_results_total',
    'Total number of analysis results generated',
    ['analyzer_name']
)

# Counter for commands published (can add label for target device?)
COMMANDS_PUBLISHED = Counter(
    'loganalyzer_commands_published_total',
    'Total number of commands published'
)
COMMANDS_BLOCKED = Counter(
    'loganalyzer_commands_blocked_total',
    'Total number of commands blocked by validation rules'
)

# Histogram for processing latency (example, needs integration)
# LOG_PROCESSING_LATENCY = Histogram(
#     'loganalyzer_log_processing_latency_seconds',
#     'Histogram of time taken to process a log line (parse + analyze)',
#     buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1, 5] # Example buckets
# )

# --- Helper Functions & Server --- #

metrics_server_thread = None
stop_event = threading.Event()

def start_metrics_server(port: int, config: Dict[str, Any]):
    """Starts the Prometheus metrics HTTP server in a background thread."""
    global metrics_server_thread
    if not config.get('monitoring', {}).get('enabled', False):
        logger.info("Monitoring / Metrics server disabled in configuration.")
        return

    actual_port = config.get('monitoring', {}).get('metrics_port', port)

    logger.info(f"Starting Prometheus metrics server on port {actual_port}")
    try:
        # The start_http_server runs in its own daemon thread internally
        start_http_server(actual_port)
        logger.info(f"Metrics server started on port {actual_port}")
        # Optionally, start a thread to update gauges periodically
        metrics_server_thread = threading.Thread(target=update_gauges_periodically, args=(config,), daemon=True)
        metrics_server_thread.start()
    except Exception as e:
        logger.error(f"Failed to start metrics server on port {actual_port}: {e}")

def update_gauges_periodically(config: Dict[str, Any]):
    """Periodically update gauge metrics like queue sizes."""
    # Need access to the queues - this suggests maybe metrics should be part of a core app context
    # Or queues need to be passed in during initialization
    from ..main import parsed_log_queue, analysis_result_queue # Lazy import to avoid circular dependency

    interval = config.get('monitoring', {}).get('update_interval_seconds', 15)
    logger.info(f"Starting periodic gauge updates every {interval} seconds.")
    while not stop_event.wait(interval):
        try:
            PARSED_LOG_QUEUE_SIZE.set(parsed_log_queue.qsize())
            ANALYSIS_RESULT_QUEUE_SIZE.set(analysis_result_queue.qsize())
        except Exception as e:
            logger.error(f"Error updating gauge metrics: {e}")
    logger.info("Stopping periodic gauge updates.")

def stop_metrics_server():
    """Signals the gauge update thread to stop."""
    # The main Prometheus server thread is a daemon and stops automatically
    logger.info("Stopping metrics gauge update thread...")
    stop_event.set()
    if metrics_server_thread and metrics_server_thread.is_alive():
        metrics_server_thread.join(timeout=5.0)
    logger.info("Metrics gauge update thread stopped.") 