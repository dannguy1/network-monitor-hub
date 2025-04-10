#!/bin/bash

# update_network_monitor.sh
# Updates the deployed Network Monitor Hub application.
# Assumes this script is run from the UPDATED source code directory
# after running 'git pull'.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration Variables ---
APP_USER="netmonitor"        # Dedicated user running the application
APP_GROUP="netmonitor"       # Dedicated group for the user
APP_DIR="/opt/network-monitor" # Directory where the application IS DEPLOYED
SOURCE_DIR=$(pwd)            # Assumes script is run from the source directory

# --- Helper Functions ---
echo_info() {
    echo "[INFO] $1"
}

echo_warning() {
    echo "[WARNING] $1"
}

echo_error() {
    echo "[ERROR] $1" >&2
}

# --- Check Root ---
if [ "$(id -u)" -ne 0 ]; then
    echo_error "This script must be run as root or with sudo."
    exit 1
fi

# --- Check if running from expected source directory ---
if [ ! -f "./requirements.txt" ] || [ ! -d "./backend" ] || [ ! -d "./frontend" ]; then
    echo_error "Script doesn't seem to be running from the project root directory."
    echo_error "Please 'cd' into the Network_Monitor project source directory (where you ran 'git pull') and run from there."
    exit 1
fi

# --- Check if deployment directory exists ---
if [ ! -d "$APP_DIR" ]; then
    echo_error "Deployment directory '$APP_DIR' not found."
    echo_error "Did you run the installation script first?"
    exit 1
fi

echo_info "Starting update process for Network Monitor Hub deployed at $APP_DIR"
echo_info "Source directory: $SOURCE_DIR"
echo_warning "Ensure you have backed up your database and '.env' file if necessary."
echo_warning "Services will be stopped during the update."
read -p "Press Enter to continue or Ctrl+C to cancel..."

# --- 1. Stop Services ---
echo_info "Stopping services..."
sudo systemctl stop network-monitor-web.service network-monitor-syslog.service || true # Allow failure if already stopped

# --- 2. Sync Files ---
echo_info "Syncing updated files from $SOURCE_DIR to $APP_DIR..."
sudo rsync -a --delete \
  --exclude='.git' \
  --exclude='backend/venv' \
  --exclude='frontend/node_modules' \
  --exclude='backend/data/app.db' \
  --exclude='.env' \
  "$SOURCE_DIR/" "$APP_DIR/"

# --- 2.5 Ensure Ownership (Moved Earlier) ---
echo_info "Resetting ownership for '$APP_DIR'..."
sudo chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# --- 3. Update Backend ---
echo_info "Updating backend dependencies..."
# Run as the application user
sudo -u "$APP_USER" "$APP_DIR/backend/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

echo_info "Applying database migrations..."
# Run as the application user
sudo -u "$APP_USER" bash -c "export FLASK_APP=backend.app:create_app; export FLASK_CONFIG=production; cd $APP_DIR && backend/venv/bin/flask db upgrade"

# --- 4. Update Frontend ---
echo_info "Rebuilding frontend..."
# Run npm install first in case dependencies changed, then build
if [ -f "$APP_DIR/frontend/package.json" ]; then
    sudo -u "$APP_USER" npm --prefix "$APP_DIR/frontend" install && sudo -u "$APP_USER" npm --prefix "$APP_DIR/frontend" run build
else
    echo_warning "Frontend package.json not found, skipping npm install/build."
fi

# --- 5. Ensure Ownership (Moved to 2.5) ---
# echo_info "Resetting ownership for '$APP_DIR'..."
# sudo chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# --- 6. Restart Services ---
echo_info "Restarting services..."
sudo systemctl start network-monitor-web.service network-monitor-syslog.service
sleep 2 # Add a small delay to allow services to start before reload
echo_info "Attempting to reload web service for code changes..."
sudo systemctl reload network-monitor-web.service || echo_warning "Reload command failed or not supported, restart should suffice."

echo_info "-----------------------------------------------------------------------"
echo_info "Network Monitor Hub Update Script Completed!"
echo_info "-----------------------------------------------------------------------"
echo_info "Check service status with: sudo systemctl status network-monitor-web network-monitor-syslog"
echo_info "Monitor logs with: sudo journalctl -f -u network-monitor-web -u network-monitor-syslog"
echo_info "-----------------------------------------------------------------------"

exit 0 