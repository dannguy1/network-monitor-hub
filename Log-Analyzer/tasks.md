# Log-Analyzer Development Tasks (v1.0)

This task list is derived from `prd.md` (Version 1.0) and outlines the work needed for the initial release. Tasks are grouped by feature area/epic.

## Epic: Project Setup & Core Service

-   [x] Initialize Python project (`pyproject.toml`).
-   [x] Set up `requirements.txt` with initial core dependencies (`PyYAML`, `pytest`).
-   [x] Implement basic service structure (`log_analyzer/main.py`, `log_analyzer/core`).
-   [x] Implement application configuration loading from YAML/JSON files (`core/config.py`, integrated into `main.py`).
-   [x] Set up basic operational logging framework (Initial `logging.basicConfig` in `main.py`).
-   [x] Create basic `systemd` service file template (`scripts/log-analyzer.service`).
-   [x] Set up initial testing framework (`pytest` added, `tests/test_basic.py` created).
-   [x] Update `README.md` with basic setup and running instructions.

## Epic: Log Ingestion (Message Queue)

-   [x] Choose and add message queue client library (`paho-mqtt`) to `requirements.txt`.
-   [x] Define message format/topic expected from `Network_Monitor` (in `config.py` example).
-   [x] Implement message queue subscriber logic to receive logs (`ingestion/mqtt_client.py`, integrated into `main.py`).
-   [x] Implement secure connection handling for the message queue (TLS/auth options in `MQTTClient`).
-   [x] Add error handling for queue connection/subscription failures (in `MQTTClient` callbacks).
-   [x] Write integration tests for message queue subscription and message reception (`test_mqtt_integration.py` added).

## Epic: Log Parsing & Transformation

-   [x] Develop initial regex patterns for common OpenWRT log formats (Examples added to `config.py`).
-   [x] Implement core parsing logic using `re` module (`parsing/parser.py`).
-   [x] Implement data extraction logic based on parsed results (Via named regex groups in `LogParser`).
-   [x] Implement transformation to structured JSON format (`transform_to_json` in `parser.py`).
-   [x] Implement transformation to structured CSV format (`transform_to_csv` in `parser.py`).
-   [x] Implement handling for malformed/unparseable log lines (Skip/log in `handle_incoming_log`, `LogParser` handles bad regex).
-   [x] Link parsing rules to the configuration system (`LogParser` initialized from config in `main.py`).
-   [ ] Write unit tests for parsing logic for different log types.
-   [ ] Write unit tests for data transformation logic.

## Epic: AI Analysis Modularity

-   [x] Define the Python interface (`analysis/base_analyzer.py` using `abc.ABC`).
-   [x] Implement a mechanism to discover and load registered/configured AI modules (`analysis/analyzer_manager.py`).
-   [x] Implement the pipeline logic to pass structured data to enabled AI modules (`AnalyzerManager` worker threads consuming from `parsed_log_queue`).
-   [x] Develop 1-2 basic placeholder AI modules (`analysis/example_analyzers.py` - `EventCounterAnalyzer`).
-   [ ] Write unit tests for the AI module loading mechanism and interface contract.

## Epic: Command Output (UCI Events)

-   [x] Define the format for command events (Expected dict format in `command_publisher.py` comments).
-   [x] Choose and implement mechanism for publishing command events (MQTT implemented in `output/command_publisher.py`).
-   [x] Implement placeholder logic to trigger command events (Publisher checks `analysis_result['action']`).
-   [x] Implement secure publishing of command events (TLS/auth options in `CommandPublisher`).
-   [x] Implement command validation against a configurable allowlist (`_validate_command` in `CommandPublisher`).
-   [x] Write integration tests for publishing and validating command events (`test_mqtt_integration.py` added).

## Epic: Configuration & UI (Web Dashboard)

-   [x] Select and add a lightweight web framework (`Flask`, `waitress`, `ruamel.yaml`) to `requirements.txt`.
-   [x] Implement basic web server setup within the service (`ui/app.py`, integrated via `run_web_server` in `main.py`).
-   [x] Implement basic user authentication for the UI (Placeholder basic auth in `ui/app.py`).
-   [x] Ensure UI interaction occurs over HTTPS (Requires external setup - reverse proxy like Nginx/Caddy).
-   [x] Develop backend API endpoints for UI interactions (Basic `/`, `/config`, `/api/status`, `/config/edit` in `ui/app.py`).
-   [ ] Develop UI page/component: Configure log ingestion settings (Partially done via `/config/edit`).
-   [ ] Develop UI page/component: View/Manage parsing rules (Partially done via `/config/edit` - needs refinement).
-   [x] Develop UI page/component: Enable/disable available AI modules (Added to `/config/edit`).
-   [x] Develop UI page/component: View system status & basic metrics (`templates/index.html` with basic status).
-   [ ] Develop UI page/component: Display recent alerts/events from modules (Sec 3.3).
-   [ ] Write basic tests for core API endpoints supporting the UI.

## Epic: Monitoring & Observability

-   [x] Add library for exposing metrics (`prometheus-client`) to `requirements.txt`.
-   [x] Define and implement key metrics (`monitoring/metrics.py` - counters, gauges).
-   [x] Set up `/metrics` endpoint for Prometheus scraping (`start_metrics_server` in `metrics.py`).
-   [x] Refine operational logging: add levels, structure, context (Added more logging, needs ongoing refinement).
-   [x] Write tests to verify metrics endpoint and basic metric values (Basic server start/stop tested via integration).

## Epic: Security

-   [ ] Review and ensure secure implementation of message queue connection (TLS/Auth options present, needs verification).
-   [ ] Review and ensure secure implementation of command event publishing (TLS/Auth options present, needs verification).
-   [ ] Review and ensure secure implementation of UI/API authentication & HTTPS (Flask-Login added, needs thorough review. HTTPS via proxy).
-   [ ] Set up dependency vulnerability scanning (e.g., `safety`, `pip-audit`) in development/CI workflow (Tooling setup required externally).
-   [ ] Perform initial security code review focusing on sensitive areas (Manual review needed).
-   [ ] *(Deferred/Future)* Implement data anonymization options (Sec 3.5).
-   [ ] *(Deferred/Future)* Implement log encryption at rest options (Sec 3.5).

## Epic: Documentation

-   [x] Expand `README.md`: detailed setup, configuration file format, running the service, basic UI usage, interfaces, deployment.
-   [x] Document expected log ingestion format/topic (in `README.md`).
-   [x] Document command event output format/topic (in `README.md`).
-   [x] Document the AI Module Python interface for extension (in `README.md`).
-   [x] Document deployment steps (including `systemd` example and HTTPS note in `README.md`).
-   [x] Add basic architectural overview documentation (Component list in `README.md`).

## Epic: Testing & Performance

-   [x] Configure `pytest` and test coverage reporting (`pytest.ini`, `pytest-cov` added).
-   [ ] Ensure sufficient unit test coverage for critical logic (Added basic `test_parser.py`, need more for other modules).
-   [x] Ensure sufficient integration test coverage (Basic MQTT tests added in `test_mqtt_integration.py`).
-   [ ] Develop initial performance benchmark script/test case (Sec 4.4).
-   [ ] Achieve 95% accuracy target for parsing/transformation on test log sets (Sec 7) (Requires test log data and refinement). 