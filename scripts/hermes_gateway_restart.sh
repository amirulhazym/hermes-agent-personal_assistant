#!/bin/bash
# Restart Hermes Gateway - called by cron one-shot
hermes gateway restart 2>&1 || true
