import logging
import pkgutil
import importlib
from typing import Dict, Any, List, Optional
import queue
import threading

from .base_analyzer import BaseAnalyzer
# Import specific analyzer modules here to make them discoverable
from . import example_analyzers # Assuming example_analyzers.py exists
from ..monitoring.metrics import ANALYSIS_RESULTS # Import metric

logger = logging.getLogger(__name__)

# Queue for analysis results (optional, could directly trigger outputs)
analysis_result_queue = queue.Queue(maxsize=500)

class AnalyzerManager:
    """Manages the lifecycle and execution of AI analysis modules."""

    def __init__(self, config: Dict[str, Any], input_queue: queue.Queue):
        """Initializes the manager.

        Args:
            config: The main application configuration dictionary.
            input_queue: The queue from which parsed logs are read.
        """
        self.config = config.get('ai_modules', {})
        self.input_queue = input_queue
        self.analyzers: List[BaseAnalyzer] = []
        self.threads: List[threading.Thread] = []
        self.stop_event = threading.Event()
        self._load_analyzers()

    def _discover_analyzers(self) -> Dict[str, type[BaseAnalyzer]]:
        """Discovers available BaseAnalyzer subclasses."""
        discovered = {}
        # Define the package where analyzers are located
        package = importlib.import_module('log_analyzer.analysis')

        for _, name, ispkg in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            if not ispkg:
                try:
                    module = importlib.import_module(name)
                    for item_name in dir(module):
                        item = getattr(module, item_name)
                        if isinstance(item, type) and issubclass(item, BaseAnalyzer) and item is not BaseAnalyzer:
                            try:
                                analyzer_name = item(config={}).get_name() # Instantiate briefly to get name
                                if analyzer_name in discovered:
                                    logger.warning(f"Duplicate analyzer name '{analyzer_name}' found in {name}. Overwriting.")
                                discovered[analyzer_name] = item
                                logger.info(f"Discovered analyzer '{analyzer_name}' in {name}")
                            except Exception as e:
                                logger.error(f"Could not get name from analyzer class {item_name} in {name}: {e}")
                except Exception as e:
                    logger.error(f"Failed to import or inspect module {name}: {e}")
        return discovered

    def _load_analyzers(self):
        """Loads and initializes analyzers specified in the config."""
        enabled_analyzers = self.config.get('enabled', [])
        analyzer_configs = self.config.get('configs', {})
        available_classes = self._discover_analyzers()

        if not enabled_analyzers:
            logger.warning("No AI analyzers enabled in configuration.")
            return

        for name in enabled_analyzers:
            if name in available_classes:
                try:
                    analyzer_class = available_classes[name]
                    specific_config = analyzer_configs.get(name, {}) # Pass specific config if available
                    instance = analyzer_class(config=specific_config)
                    self.analyzers.append(instance)
                    logger.info(f"Successfully loaded and initialized analyzer: {name}")
                except Exception as e:
                    logger.error(f"Failed to initialize analyzer {name}: {e}", exc_info=True)
            else:
                logger.warning(f"Enabled analyzer '{name}' not found or failed discovery.")

    def start_analysis(self):
        """Starts worker threads to process logs from the input queue."""
        num_workers = self.config.get('worker_threads', 1)
        logger.info(f"Starting {num_workers} analyzer worker thread(s)...")
        for i in range(num_workers):
            thread = threading.Thread(target=self._worker_loop, name=f"AnalyzerWorker-{i}", daemon=True)
            self.threads.append(thread)
            thread.start()

    def _worker_loop(self):
        """Worker thread function to consume logs and run analyzers."""
        logger.info(f"Analyzer worker {threading.current_thread().name} started.")
        while not self.stop_event.is_set():
            try:
                parsed_log = self.input_queue.get(block=True, timeout=1.0)
                logger.debug(f"Worker {threading.current_thread().name} processing log: {parsed_log.get('_raw_log', '')[:50]}")
                for analyzer in self.analyzers:
                    try:
                        result = analyzer.analyze(parsed_log)
                        if result:
                            # Add analyzer name to the result for context
                            analyzer_name = analyzer.get_name()
                            result['_analyzer_name'] = analyzer_name
                            ANALYSIS_RESULTS.labels(analyzer_name=analyzer_name).inc() # Increment metric
                            # Queue the result for potential command output generation
                            try:
                                analysis_result_queue.put(result, block=False)
                                logger.debug(f"Queued analysis result from {analyzer_name}")
                            except queue.Full:
                                logger.warning(f"Analysis result queue is full. Discarding result from {analyzer_name}")
                    except Exception as e:
                        logger.error(f"Error during analysis by {analyzer.get_name()}: {e}", exc_info=True)
                self.input_queue.task_done()
            except queue.Empty:
                continue # No log in queue, continue loop
            except Exception as e:
                logger.error(f"Unexpected error in worker loop: {e}", exc_info=True)
        logger.info(f"Analyzer worker {threading.current_thread().name} stopped.")

    def stop_analysis(self):
        """Signals worker threads to stop and shuts down analyzers."""
        logger.info("Stopping analyzer manager...")
        self.stop_event.set()
        for thread in self.threads:
            thread.join(timeout=5.0)
            if thread.is_alive():
                logger.warning(f"Analyzer thread {thread.name} did not exit cleanly.")
        logger.info("All analyzer workers stopped.")

        for analyzer in self.analyzers:
            try:
                analyzer.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down analyzer {analyzer.get_name()}: {e}")
        logger.info("Analyzer manager stopped.") 