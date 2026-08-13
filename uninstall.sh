#!/usr/bin/env bash

set -euo pipefail

if [[ "$(whoami)" != "root" ]]; then
    echo "You need to run this script as root."
    exit 1
fi

TARGETDIR="${1:-/opt/fan_control}"
readonly UNIT_PATH="/etc/systemd/system/fan-control.service"
if [[ ! "$TARGETDIR" =~ ^/opt/[A-Za-z0-9][A-Za-z0-9._-]*$ ]]; then
    echo "The installation path must be a dedicated directory directly under /opt."
    exit 1
fi
if [ -e "$TARGETDIR" ] && [ ! -f "$TARGETDIR/.fan-control-installation" ]; then
    echo "Refusing to remove an installation directory without the fan-control marker."
    exit 1
fi
if [ -e "$UNIT_PATH" ] && ! grep -Fqx "WorkingDirectory=$TARGETDIR" "$UNIT_PATH"; then
    echo "Refusing to remove a fan-control.service that belongs to another installation."
    exit 1
fi

if [ ! -e "$TARGETDIR" ] && [ ! -e "$UNIT_PATH" ]; then
    echo "*** Fan control is already uninstalled."
    exit 0
fi

echo "*** Stopping fan-control.service for automatic-mode recovery..."
if systemctl is-active --quiet fan-control.service; then
    systemctl stop fan-control.service
fi
if systemctl is-active --quiet fan-control.service; then
    echo "fan-control.service did not stop; no files were removed."
    exit 1
fi

echo "*** Removing systemd service..."
if [ -e "$UNIT_PATH" ]; then
    systemctl disable fan-control.service
    rm -f -- "$UNIT_PATH"
    systemctl daemon-reload
fi

echo "*** Removing installation directory '$TARGETDIR'..."
rm -rf -- "$TARGETDIR"

echo "*** Uninstall complete. Shared operating-system packages were left installed."
