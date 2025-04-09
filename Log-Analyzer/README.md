# Log Analyzer

OpenWRT Log Analyzer for AI Processing, designed to work with Network Monitor Hub.

This service listens for logs via MQTT (or potentially other sources), parses them according to configured rules, runs them through enabled AI analysis modules, and can optionally trigger command outputs (e.g., UCI commands via MQTT) based on analysis results. It also provides a basic web UI for status and configuration, and exposes Prometheus metrics.

## Project Status

*   Alpha / Under Development

## Core Components

*   **Ingestion (`ingestion/`):** Handles receiving raw logs (currently supports MQTT via `mqtt_client.py`).
*   **Parsing (`parsing/`):** Parses raw logs into structured data using regex rules defined in `config.yaml` (`parser.py`).
*   **Analysis (`analysis/`):** Applies AI/analysis modules to parsed logs. Features a plugin system (`base_analyzer.py`, `analyzer_manager.py`). See `example_analyzers.py` for a basic counter.
*   **Output (`output/`):** Handles actions based on analysis results (currently supports publishing UCI commands via MQTT with validation in `command_publisher.py`).
*   **UI (`ui/`):** Basic Flask web interface for status and configuration (`app.py`, `templates/`). Uses Flask-Login for authentication.
*   **Monitoring (`monitoring/`):** Exposes Prometheus metrics (`metrics.py`).
*   **Core (`core/`):** Configuration loading (`config.py`) and main application logic (`main.py`).

## Features (v1.0 - Current State)

*   [x] Log ingestion via Message Queue (MQTT via `paho-mqtt`)
*   [x] Parsing framework for common OpenWRT log formats (Regex examples provided, **needs refinement with real logs**)
*   [x] Transformation helper to structured JSON
*   [~] Transformation helper to structured CSV (Exists, but not actively used in main pipeline)
*   [x] Modular AI analysis plugin system (Manager and base class implemented, `EventCounter` example provided)
*   [x] Command event output (MQTT publisher with UCI command validation)
*   [~] Web UI for configuration and basic monitoring (Basic status/config view, partial edit via `/config/edit`, **needs more features**)
*   [x] Session-based UI Authentication (via Flask-Login, **replace placeholder user storage/handling**)
*   [x] Prometheus metrics endpoint (Basic counters and gauges implemented)

## Setup

1.  **Prerequisites:**
    *   Python >= 3.9
    *   An MQTT Broker accessible for ingestion and command output.
    *   (Optional but recommended) `virtualenv` or `conda` for environment management

2.  **Local MQTT Broker Setup (for Development/Testing):**
    *   For local development and testing, you can install Mosquitto:
        ```bash
        # On Debian/Ubuntu based systems
        sudo apt update
        sudo apt install mosquitto mosquitto-clients -y
        # Check status
        sudo systemctl status mosquitto
        ```
    *   By default, Mosquitto listens on port `1883` without authentication or encryption. This matches the default `localhost:1883` settings in the example `config.yaml`.
    *   **Production Note:** For production, configure strong authentication and TLS encryption on your MQTT broker and update the Log Analyzer config accordingly. See the [Mosquitto Documentation](https://mosquitto.org/documentation/).

3.  **Install Log Analyzer:**
    ```bash
    git clone <repository-url>
    cd network-monitor-hub/Log-Analyzer # Navigate to the Log-Analyzer directory

    # Create and activate virtual environment
    python -m venv venv
    source venv/bin/activate # On Windows use `venv\Scripts\activate`

    # Install dependencies
    pip install -r requirements.txt

    # Install the package in editable mode (allows changes without reinstalling)
    pip install -e .
    ```

4.  **Configure Log Analyzer (`config.yaml`):**
    *   Create `config.yaml` in the `Log-Analyzer` directory (or specify path with `-c` flag when running).
    *   Copy the example structure from the comment block within `log_analyzer/core/config.py` as a starting point.
    *   **Crucially, configure:**
        *   `message_queue`: MQTT broker details for *ingestion*.
        *   `command_output`: MQTT broker details for *command publishing* (if used).
        *   `parsing -> rules`: **Refine regex patterns based on your actual logs.** The examples are basic.
        *   `ai_modules -> enabled`: List the analyzers to run (e.g., `EventCounter`).
        *   `web_ui -> enabled`: Set to `true` to enable the UI.
        *   `web_ui -> host`, `port`: Interface/port for the UI.
        *   `web_ui -> username`: The username for UI login.
        *   `web_ui -> password_hash`: **MUST set this.** On first run with a plain `password` set, the service logs the generated hash. Copy that hash here and *remove* the plain `password` field.
        *   `web_ui -> secret_key`: **MUST set this** to a strong, random string (e.g., generate with `openssl rand -hex 32`) for secure Flask sessions.
        *   `monitoring`: Enable/disable metrics, set port.

## Running the Service

```bash
# Ensure virtual environment is active
source venv/bin/activate

# Run from the Log-Analyzer directory, pointing to your config
log-analyzer -c config.yaml

# Or run as a module
# python -m log_analyzer.main -c config.yaml
```
*   Access the UI (if enabled) at `http://<host>:<port>` (default: `http://0.0.0.0:8080`). Log in using the credentials configured in `config.yaml` (`username`/`password_hash`).
*   **Security Warning:** The UI uses session cookies. **Do NOT expose the UI directly over HTTP in production.** Use a reverse proxy (Nginx, Caddy) to handle HTTPS termination.
*   Access Prometheus metrics (if enabled) at `http://<host>:<metrics_port>/` (default: `http://<host>:9090/`).

## Running Tests

```bash
# Ensure virtual environment is active
source venv/bin/activate

# Run all tests (from Log-Analyzer directory)
pytest

# Run only unit tests (excluding integration)
pytest -m "not integration"

# Run only integration tests (requires local MQTT broker on localhost:1883)
pytest -m integration
```
(Note: Test coverage is currently limited. Needs expansion, especially unit tests for parsing and more integration tests).

## Interfaces

*   **Log Ingestion (MQTT):**
    *   Subscribes To: `message_queue.topic_prefix/#` (e.g., `network_monitor/logs/#`).
    *   Expects Payload: Raw log line string (UTF-8 encoded).
*   **Command Output (MQTT):**
    *   Publishes To: `command_output.mqtt.topic_prefix/<target_device_id>` (e.g., `log_analyzer/commands/device123`).
    *   Payload: Single UCI command string (UTF-8 encoded).
    *   Trigger: Analysis module result dictionary containing `"action": "set_config"`, `"target_device_id": "..."`, and `"uci_commands": ["cmd1", "cmd2", ...]`. Commands are validated against `command_output.allowed_command_prefixes` before publishing.
*   **AI Module API (`analysis/base_analyzer.py`):**
    *   Implement class inheriting `BaseAnalyzer`.
    *   Implement `get_name() -> str`.
    *   Implement `analyze(parsed_log: dict) -> Optional[dict]`.
    *   Receives parsed log data (including `_raw_log`, `_topic`, `_parser_rule` metadata).
    *   Return a dictionary to trigger actions (see Command Output trigger format).
*   **Web UI API (Requires Login):**
    *   `/`: Status HTML page.
    *   `/config/edit`: View/Edit configuration page (requires restart to apply).
    *   `/login`, `/logout`: User authentication.
    *   `/api/status` (GET): JSON status (MQTT connection, queue sizes, etc.).
    *   `/config` (GET): Read-only view of current in-memory configuration (JSON).

## Deployment

*   See `scripts/log-analyzer.service` for a template `systemd` unit file.
*   **Key Steps:**
    *   Create dedicated user/group (e.g., `loganalyzer`).
    *   Install application code (e.g., clone to `/opt/log-analyzer`).
    *   Install dependencies within a virtual environment owned by the service user.
    *   Place `config.yaml` in a secure location readable by the service user (e.g., `/etc/log-analyzer/config.yaml`). **Ensure permissions are restricted and it contains the hashed password and a strong secret key.**
    *   Update paths (WorkingDirectory, ExecStart, config path) in `log-analyzer.service`.
    *   Install and enable the `systemd` service.
    *   Configure firewall rules for UI port (e.g., 8080) and metrics port (e.g., 9090) if needed.
    *   **HTTPS (Required for Secure UI):** Set up a reverse proxy (e.g., Nginx, Caddy) to handle TLS termination and proxy requests to the Log Analyzer UI port. Configure the proxy to handle HTTPS.

## Contributing

(Placeholder: Contribution guidelines - e.g., code style, pull requests)

## License

(Placeholder: Specify License - e.g., MIT License. Add LICENSE file)
