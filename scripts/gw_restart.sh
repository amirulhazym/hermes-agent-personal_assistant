#!/bin/bash
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
SVC="hermes-gateway"
systemctl --user restart "$SVC"
