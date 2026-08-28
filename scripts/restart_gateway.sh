#!/bin/bash
# Restart Hermes Gateway via the systemd --user supervisor (canonical path).
# Fix 2026-07-11: previous version hardcoded a stale PID and used a manual
# setsid launch that fought the real systemd --user service. Now delegates to
# `systemctl --user restart hermes-gateway`.
export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"
systemctl --user restart hermes-gateway
systemctl --user status hermes-gateway --no-pager | head -5
