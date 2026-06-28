#!/bin/bash
sleep 3
export PATH="/home/amirul/.local/bin:$PATH"
/home/amirul/.local/bin/hermes gateway restart >> /home/amirul/.hermes/logs/gateway-restart.log 2>&1
