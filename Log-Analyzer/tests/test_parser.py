import pytest
import logging

from log_analyzer.parsing.parser import LogParser

# Example rules for testing
TEST_RULES = [
    {
        "name": "syslog_test",
        "pattern": r'^(?P<timestamp>\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+(?P<hostname>\S+)\s+(?P<process>\S+?):\s*(?P<message>.*)$'
    },
    {
        "name": "kv_test",
        "pattern": r'^time=(?P<ts>\d+)\s+level=(?P<lvl>\w+)\s+msg="(?P<msg>[^"]*)"'
    },
    {
        "name": "invalid_rule", # Invalid regex
        "pattern": r'(.'
    }
]

# Example log lines
LOG_LINE_SYSLOG = "Apr 11 10:30:01 myhost process1: This is a test message"
LOG_LINE_KV = 'time=1678886400 level=info msg="Key value test"'
LOG_LINE_UNMATCHED = "This line matches nothing"

@pytest.fixture
def parser():
    """Provides a LogParser instance initialized with test rules."""
    return LogParser(TEST_RULES)

def test_parser_init(caplog): # caplog fixture captures logging output
    """Tests that the parser initializes and handles invalid rules."""
    parser = LogParser(TEST_RULES)
    assert len(parser.compiled_rules) == 2 # Only valid rules should compile
    assert "Failed to compile regex for rule invalid_rule" in caplog.text
    assert parser.compiled_rules[0]['name'] == 'syslog_test'
    assert parser.compiled_rules[1]['name'] == 'kv_test'

def test_parse_syslog(parser):
    """Tests parsing a syslog-like message."""
    result = parser.parse_log_line(LOG_LINE_SYSLOG)
    assert result is not None
    rule_name, data = result
    assert rule_name == "syslog_test"
    assert data['timestamp'] == "Apr 11 10:30:01"
    assert data['hostname'] == "myhost"
    assert data['process'] == "process1"
    assert data['message'] == "This is a test message"

def test_parse_kv(parser):
    """Tests parsing a key-value like message."""
    result = parser.parse_log_line(LOG_LINE_KV)
    assert result is not None
    rule_name, data = result
    assert rule_name == "kv_test"
    assert data['ts'] == "1678886400"
    assert data['lvl'] == "info"
    assert data['msg'] == "Key value test"

def test_parse_unmatched(parser):
    """Tests a log line that doesn't match any rules."""
    result = parser.parse_log_line(LOG_LINE_UNMATCHED)
    assert result is None

def test_parse_empty_string(parser):
    """Tests parsing an empty string."""
    result = parser.parse_log_line("")
    assert result is None

def test_parser_with_no_rules():
    """Tests parser initialized with no valid rules."""
    parser = LogParser([])
    assert len(parser.compiled_rules) == 0
    result = parser.parse_log_line(LOG_LINE_SYSLOG)
    assert result is None
 