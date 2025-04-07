# Getting Started with Create React App

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

## Available Scripts

In the project directory, you can run:

### `npm start`

Runs the app in the development mode.\
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

The page will reload when you make changes.\
You may also see any lint errors in the console.

### `npm test`

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### `npm run build`

Builds the app for production to the `build` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.\
Your app is ready to be deployed!

See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.

### `npm run eject`

**Note: this is a one-way operation. Once you `eject`, you can't go back!**

If you aren't satisfied with the build tool and configuration choices, you can `eject` at any time. This command will remove the single build dependency from your project.

Instead, it will copy all the configuration files and the transitive dependencies (webpack, Babel, ESLint, etc) right into your project so you have full control over them. All of the commands except `eject` will still work, but they will point to the copied scripts so you can tweak them. At this point you're on your own.

You don't have to ever use `eject`. The curated feature set is suitable for small and middle deployments, and you shouldn't feel obligated to use this feature. However we understand that this tool wouldn't be useful if you couldn't customize it when you are ready for it.

## Learn More

You can learn more in the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

To learn React, check out the [React documentation](https://reactjs.org/).

### Code Splitting

This section has moved here: [https://facebook.github.io/create-react-app/docs/code-splitting](https://facebook.github.io/create-react-app/docs/code-splitting)

### Analyzing the Bundle Size

This section has moved here: [https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size](https://facebook.github.io/create-react-app/docs/analyzing-the-bundle-size)

### Making a Progressive Web App

This section has moved here: [https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app](https://facebook.github.io/create-react-app/docs/making-a-progressive-web-app)

### Advanced Configuration

This section has moved here: [https://facebook.github.io/create-react-app/docs/advanced-configuration](https://facebook.github.io/create-react-app/docs/advanced-configuration)

### Deployment

This section has moved here: [https://facebook.github.io/create-react-app/docs/deployment](https://facebook.github.io/create-react-app/docs/deployment)

### `npm run build` fails to minify

This section has moved here: [https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify](https://facebook.github.io/create-react-app/docs/troubleshooting#npm-run-build-fails-to-minify)

## Development Setup

### Backend

1.  **Prerequisites:** Python 3.8+
2.  **Clone:** `git clone <repository_url> Network_Monitor && cd Network_Monitor`
3.  **Create Virtual Environment:** `python3 -m venv backend/venv`
4.  **Activate Environment:**
    *   macOS/Linux: `source backend/venv/bin/activate`
    *   Windows: `backend\\venv\\Scripts\\activate`
5.  **Install Dependencies:** `pip install -r requirements.txt`
6.  **Environment Variables:**
    *   Copy `.env.example` to `.env` in the project root (`Network_Monitor/.env`).
    *   **Crucially, generate and set `ENCRYPTION_KEY`**:
        *   Run Python: `python`
        *   Enter: `from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())`
        *   Copy the output key into the `ENCRYPTION_KEY` field in `.env`.
    *   Set `SECRET_KEY` to a strong random string.
    *   Configure `DATABASE_URL` if not using the default SQLite path (`backend/data/app.db`).
    *   Configure `AI_ENGINE_ENDPOINT`, `AI_ENGINE_API_KEY`, and `AI_PUSH_INTERVAL_MINUTES` if using the AI push feature.
7.  **Database Initialization:**
    *   Ensure the virtual environment is active.
    *   Set Flask environment variables:
        *   macOS/Linux: `export FLASK_APP=wsgi.py && export FLASK_CONFIG=development`
        *   Windows: `set FLASK_APP=wsgi.py && set FLASK_CONFIG=development` (or use `.flaskenv` file)
    *   Initialize migrations (only once per project): `flask db init`
    *   Create migration script: `flask db migrate -m "Initial models"`
    *   Apply migrations to create database: `flask db upgrade`
8.  **Run Development Server:** `flask run`
    *   The backend API will be available at `http://localhost:5000`.
    *   The AI Pusher scheduler will start automatically.

### Frontend

1.  **Prerequisites:** Node.js (LTS recommended) and npm.
2.  **Navigate:** `cd frontend` (from the `Network_Monitor` root)
3.  **Install Dependencies:** `npm install`
4.  **Run Development Server:** `npm start`
    *   The frontend will open in your browser, usually at `http://localhost:3000`.
    *   API requests to `/api/v1` will be automatically proxied to the backend server at `http://localhost:5000` (configured in `frontend/package.json`).

## Running Background Tasks (Development)

*   **AI Pusher:** Starts automatically when you run `flask run` due to APScheduler integration. It runs based on the `AI_PUSH_INTERVAL_MINUTES` setting in `.env`. Manually trigger with `flask trigger-ai-push`.
*   **Syslog Listener:**
    *   Needs to run in a separate terminal from `flask run`.
    *   Ensure the backend virtualenv is active (`source backend/venv/bin/activate`).
    *   Run: `flask run-syslog --port 5140` (use a high port like 5140 for dev to avoid needing `sudo`).
    *   Configure your OpenWRT devices to send syslog messages via UDP to your development machine's IP on port 5140.
    *   **Important:** Make sure no other service (like the system `rsyslog`) is listening on the same port you specify.

## Testing

### Backend

1.  Ensure virtualenv is active and test dependencies are installed (`pip install -r requirements.txt`).
2.  Navigate to the project root (`Network_Monitor/`).
3.  Run: `pytest`
    *   Tests use an in-memory SQLite database by default (`TestingConfig`).

### Frontend

1.  Navigate to the frontend directory (`Network_Monitor/frontend/`).
2.  Run: `npm test`
    *   This launches the Jest test runner in watch mode.

## Deployment (Raspberry Pi 5 Example)

These steps assume a Raspberry Pi OS (or similar Debian-based system) and deployment in `/opt/openwrt-loghub`. Adjust paths and user/group as needed.

1.  **Prerequisites on Pi:**
    *   Update system: `sudo apt update && sudo apt upgrade -y`
    *   Install required packages: `sudo apt install -y python3 python3-pip python3-venv git nginx`
    *   (Optional) If using system syslog forwarding: `sudo apt install -y rsyslog` (or `syslog-ng`)

2.  **Clone Repository:**
    `sudo git clone <repository_url> /opt/openwrt-loghub`
    `sudo chown -R pi:pi /opt/openwrt-loghub` (Assuming user `pi`. Adjust ownership if needed).
    `cd /opt/openwrt-loghub`

3.  **Backend Setup:**
    *   Create venv: `python3 -m venv backend/venv`
    *   Activate venv: `source backend/venv/bin/activate`
    *   Install dependencies: `pip install -r requirements.txt`
    *   Create and configure `.env` file (copy from `.env.example`, generate `ENCRYPTION_KEY`, set `SECRET_KEY`, configure Database, AI endpoint etc. for production).
    *   Ensure correct file ownership/permissions for `.env`.
    *   Initialize/Upgrade Database:
        *   `export FLASK_APP=wsgi.py && export FLASK_CONFIG=production`
        *   `flask db upgrade` (creates `backend/data/app.db` if it doesn't exist)
    *   Ensure the `data` directory and `app.db` file are writable by the user running the web service (e.g., `pi` or `www-data`).

4.  **Frontend Build:**
    *   `cd frontend`
    *   `npm install`
    *   `npm run build` (This creates the static files in `frontend/build/`)
    *   `cd ..`

5.  **Syslog Configuration:**
    *   **Option A (Recommended): Use System Syslog (rsyslog):**
        *   Configure OpenWRT devices to send logs to the Pi's IP (port 514 UDP).
        *   Configure the Pi's `rsyslog` (`/etc/rsyslog.conf` or files in `/etc/rsyslog.d/`) to:
            *   Listen for UDP messages on port 514.
            *   Filter messages from your OpenWRT devices (e.g., based on source IP range).
            *   Write these filtered logs to a dedicated file (e.g., `/var/log/openwrt-devices.log`).
        *   Ensure the `network-monitor-web` service user can *read* this file. Update `SYSLOG_FILE_PATH` in `.env` if needed.
        *   Create a separate `systemd` timer or `cron` job to periodically run a custom Flask command (like `flask process-log-file /var/log/openwrt-devices.log`) to ingest logs from the file into the database. *(This command needs to be created in `backend/app/cli.py`)*.
    *   **Option B (Simpler, Less Robust): Use Flask Listener Service:**
        *   Configure OpenWRT devices to send logs to the Pi's IP (port 514 UDP).
        *   **Disable** the system's default syslog listener (`sudo systemctl stop rsyslog && sudo systemctl disable rsyslog`).
        *   Use the provided `network-monitor-syslog.service` systemd file (see Step 7). Note it requires running as `root` for port 514.

6.  **Web Server (Nginx):**
    *   Copy the example config: `sudo cp network-monitor-nginx.conf /etc/nginx/sites-available/network-monitor`
    *   Edit the config (`sudo nano /etc/nginx/sites-available/network-monitor`):
        *   Change `server_name` to your Pi's IP address or hostname.
        *   Ensure the `root` directive points to `/opt/openwrt-loghub/frontend/build`.
        *   Ensure the `proxy_pass` directive correctly points to the Gunicorn socket (`unix:/tmp/network-monitor.sock`).
    *   Enable the site: `sudo ln -s /etc/nginx/sites-available/network-monitor /etc/nginx/sites-enabled/`
    *   Remove default site if it exists: `sudo rm /etc/nginx/sites-enabled/default`
    *   Test Nginx config: `sudo nginx -t`
    *   Restart Nginx: `sudo systemctl restart nginx`

7.  **Process Management (systemd):**
    *   Copy the example service files:
        `sudo cp network-monitor-web.service /etc/systemd/system/`
        (Optional, if using Option B for Syslog) `sudo cp network-monitor-syslog.service /etc/systemd/system/`
    *   Edit the service files if needed (e.g., adjust `User`, `Group`, `WorkingDirectory`). Ensure `User` matches ownership/permissions for the venv, data directory, and socket path. The `network-monitor-web.service` uses user `pi` and group `www-data` by default - create the user/group or adjust as needed. The socket `/tmp/network-monitor.sock` needs to be writable by Nginx (user `www-data` usually) and readable/writable by the web service user (`pi`). The `-m 007` in Gunicorn allows group write access. Adjust permissions carefully.
    *   Reload systemd: `sudo systemctl daemon-reload`
    *   Enable services to start on boot:
        `sudo systemctl enable network-monitor-web.service`
        (If applicable) `sudo systemctl enable network-monitor-syslog.service`
    *   Start services:
        `sudo systemctl start network-monitor-web.service`
        (If applicable) `sudo systemctl start network-monitor-syslog.service`
    *   Check status:
        `sudo systemctl status network-monitor-web.service`
        (If applicable) `sudo systemctl status network-monitor-syslog.service`
        `journalctl -u network-monitor-web.service -f` (View logs)

8.  **Verification:**
    *   Access the web UI via the Pi's IP address in your browser.
    *   Configure OpenWRT devices to send logs (if not done already).
    *   Check if logs appear in the UI.
    *   Test adding devices, credentials, association, verification, and UCI application.
    *   Monitor service logs (`journalctl`) for errors.

## Configuration Details

*   **Backend:** Main configuration is handled by `backend/config.py`, which reads environment variables. Key variables are set in the root `.env` file.
*   **Frontend:** API endpoint is `/api/v1`. Development proxy is set in `frontend/package.json`.

## Future Enhancements

*   More sophisticated UI/UX (theming, dashboard, detailed views, better notifications).
*   Expanded UCI configuration options in the UI.
*   Advanced log parsing (e.g., key-value extraction from messages).
*   More robust error handling and reporting.
*   User authentication/authorization for the web UI.
*   Enhanced background task management (e.g., using Celery).
*   Comprehensive backend and frontend test coverage.
*   Option to configure syslog listener port/protocol (TCP).
*   Host key verification for SSH connections.
