import logging
from typing import Dict, Any, Optional
from collections import Counter

from .base_analyzer import BaseAnalyzer

logger = logging.getLogger(__name__)

class EventCounterAnalyzer(BaseAnalyzer):
    """A simple example analyzer that counts events based on parser rule name."""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.event_counts = Counter()

    def get_name(self) -> str:
        return "EventCounter"

    def analyze(self, parsed_log: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Increments count for the parser rule used."""
        rule_name = parsed_log.get('_parser_rule')
        if rule_name:
            self.event_counts[rule_name] += 1
            logger.debug(f"Incremented count for rule '{rule_name}'. New count: {self.event_counts[rule_name]}")

            # Optionally return status updates periodically
            if self.event_counts[rule_name] % self.config.get("report_interval", 100) == 0:
                return {
                    "type": "counter_update",
                    "rule_name": rule_name,
                    "count": self.event_counts[rule_name]
                }
        return None

    def shutdown(self):
        """Log final counts on shutdown."""
        logger.info(f"Final counts for {self.get_name()}: {dict(self.event_counts)}")
        super().shutdown()

# Add other example analyzers here if needed 