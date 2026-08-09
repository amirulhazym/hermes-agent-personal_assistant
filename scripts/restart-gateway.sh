#!/bin/bash
set -euo pipefail
systemctl --user restart hermes-gateway
echo "Gateway restarted at $(TZ=Asia/Kuala_Lumpur date '+%H:%M:%S %Z')"
