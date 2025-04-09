import re
import logging
from typing import List, Dict, Any, Optional, Tuple
import json
import csv
import io

logger = logging.getLogger(__name__)

# Define a structure for parsing rules (could be loaded from config)
# Example rule structure:
# {
#     "name": "syslog_generic",
#     "pattern": r"^(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(?P<hostname>\S+)\s+(?P<process>\S+?)(?:\[(?P<pid>\d+)\])?:",
#     "fields": ["timestamp", "hostname", "process", "pid", "message"] # Implicitly capture the rest as 'message'
# }

class LogParser:
    """Parses log lines based on a set of configurable rules."""

    def __init__(self, rules: List[Dict[str, Any]]):
        """Initializes the parser with a list of rules.

        Args:
            rules: A list of dictionaries, each representing a parsing rule.
                   Each rule should have 'name' (str) and 'pattern' (str, regex).
                   The pattern should use named capture groups `(?P<name>...)`.
        """
        self.compiled_rules = []
        for rule in rules:
            if not isinstance(rule, dict) or 'name' not in rule or 'pattern' not in rule:
                logger.warning(f"Skipping invalid rule: {rule}")
                continue
            try:
                compiled_pattern = re.compile(rule['pattern'])
                self.compiled_rules.append({
                    "name": rule['name'],
                    "pattern": compiled_pattern
                    # We could add expected 'fields' here for validation later
                })
                logger.info(f"Compiled regex for rule: {rule['name']}")
            except re.error as e:
                logger.error(f"Failed to compile regex for rule {rule['name']}: {e}")
        if not self.compiled_rules:
            logger.warning("No valid parsing rules loaded.")

    def parse_log_line(self, log_line: str) -> Optional[Tuple[str, Dict[str, Any]]]:
        """Attempts to parse a single log line using the compiled rules.

        Args:
            log_line: The raw log line string.

        Returns:
            A tuple containing (rule_name, parsed_data_dict) if a match is found,
            otherwise None.
        """
        for rule in self.compiled_rules:
            match = rule['pattern'].match(log_line)
            if match:
                parsed_data = match.groupdict()
                # Optionally capture the rest of the line if not explicitly matched
                # This requires careful regex design
                # Example: If regex ends with ':', capture rest
                # Or add a `(?P<message>.*)` to the end of patterns
                # For now, rely on named groups

                logger.debug(f"Matched log line with rule: {rule['name']}")
                return rule['name'], parsed_data

        logger.debug(f"No matching rule found for log line: {log_line[:100]}...")
        return None

def transform_to_json(data: Dict[str, Any], **kwargs) -> str:
    """Transforms parsed data dictionary into a JSON string."""
    try:
        return json.dumps(data, **kwargs)
    except TypeError as e:
        logger.error(f"Error serializing data to JSON: {e} - Data: {data}")
        # Handle non-serializable data gracefully if needed
        return json.dumps({"error": "Serialization failed", "original_data_keys": list(data.keys())})

def transform_to_csv(data: List[Dict[str, Any]], fieldnames: Optional[List[str]] = None, **kwargs) -> str:
    """Transforms a list of parsed data dictionaries into a CSV string.

    Args:
        data: A list of dictionaries (parsed log lines).
        fieldnames: Optional list of keys to include as CSV columns. If None,
                    uses keys from the first dictionary.

    Returns:
        A string containing the data in CSV format.
    """
    if not data:
        return ""

    output = io.StringIO()
    if fieldnames is None:
        fieldnames = list(data[0].keys()) # Use keys from the first record

    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore', **kwargs)

    writer.writeheader()
    writer.writerows(data)

    return output.getvalue() 