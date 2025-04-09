import abc
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class BaseAnalyzer(abc.ABC):
    """Abstract Base Class for all AI Analysis Modules."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize the analyzer with its specific configuration."""
        self.config = config
        logger.info(f"Initializing analyzer: {self.get_name()}")

    @abc.abstractmethod
    def get_name(self) -> str:
        """Return the unique name of this analyzer."""
        pass

    @abc.abstractmethod
    def analyze(self, parsed_log: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process a single parsed log dictionary.

        Args:
            parsed_log: A dictionary representing a single parsed log entry,
                        including metadata like '_raw_log', '_topic', '_parser_rule'.

        Returns:
            A dictionary containing analysis results or insights if any were generated,
            otherwise None. This result might trigger command outputs later.
        """
        pass

    def shutdown(self):
        """Perform any cleanup needed when the service stops."""
        logger.info(f"Shutting down analyzer: {self.get_name()}")
        # Default implementation does nothing
        pass 