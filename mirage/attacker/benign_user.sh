#!/usr/bin/env bash
# MIRAGE benign-user baseline (false-positive test). LAB ONLY: our own lab container.
set -euo pipefail
exec python -m mirage.attacker.scripted --profile benign "$@"
