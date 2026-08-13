#!/usr/bin/env bash

set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ "$(whoami)" != "root" ]]; then
    echo "You need to run this script as root."
    exit 1
fi

TARGETDIR="/opt/fan_control"
if [ -n "${1:-}" ]; then
    TARGETDIR="$1"
fi
if [[ ! "$TARGETDIR" =~ ^/opt/[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
    echo "The installation path must be a dedicated directory directly under /opt."
    exit 1
fi

echo "*** Installing packaged dependencies..."
if [ -x "$(command -v apt-get)" ]; then
    apt-get update
    apt-get install -y python3-venv lm-sensors ipmitool
elif [ -x "$(command -v dnf)" ]; then
    dnf install -y python3 lm_sensors ipmitool
else
    echo "Unsupported package manager; install Python 3, lm-sensors, and ipmitool first."
    exit 1
fi

echo "*** Creating folder '$TARGETDIR'..."
install -d -m 0755 "$TARGETDIR"

echo "*** Creating Python3 virtualenv..."
if [ -d "$TARGETDIR/venv" ]; then
    echo "*** Existing venv found, purging it."
    rm -r "$TARGETDIR/venv"
fi
python3 -m venv "$TARGETDIR/venv"

echo "*** Installing Python dependencies..."
"$TARGETDIR/venv/bin/python" -m pip install --requirement "$SOURCE_DIR/requirements.txt"

echo "*** Copying script and configuration in place..."
RUNTIME_FILES=(
    main.py
    config_loader.py
    control_policy.py
    fan_controller.py
    lifecycle.py
    monitoring_web.py
    state.py
    temp_monitor.py
    utils.py
)
for runtime_file in "${RUNTIME_FILES[@]}"; do
    install -m 0644 "$SOURCE_DIR/$runtime_file" "$TARGETDIR/$runtime_file"
done
install -m 0644 "$SOURCE_DIR/fan_control_config.yaml.example" "$TARGETDIR/fan_control_config.yaml.example"
if [ ! -f "$TARGETDIR/fan_control_config.yaml" ]; then
    install -m 0600 "$SOURCE_DIR/fan_control_config.yaml.example" "$TARGETDIR/fan_control_config.yaml"
fi
touch "$TARGETDIR/.fan-control-installation"

echo "*** Creating, (re)starting and enabling SystemD service..."
unit_tmp="$(mktemp)"
trap 'rm -f "$unit_tmp"' EXIT
sed "s#{TARGETDIR}#$TARGETDIR#g" "$SOURCE_DIR/fan-control.service" > "$unit_tmp"
install -m 0644 "$unit_tmp" /etc/systemd/system/fan-control.service
systemctl daemon-reload
systemctl restart fan-control
systemctl enable fan-control

echo "*** Waiting for the service to start..."
sleep 3

echo -e "*** All done! Check the service's output below:\n"
systemctl status fan-control
