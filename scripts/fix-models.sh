#!/bin/bash
# fix-models.sh — thin wrapper for fix_models.py
# Replaces the broken heredoc-based version (SyntaxError in Python body).
# Run after `hermes update` to restore curated model lists + MoA/Gemini removal.
exec python3 /home/amirul/.hermes/scripts/fix_models.py "$@"
