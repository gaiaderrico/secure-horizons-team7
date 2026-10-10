#!/usr/bin/env bash
# MIRAGE backup-window baseline (guard must ignore). LAB ONLY: our own lab container.
set -euo pipefail
exec python -m mirage.attacker.scripted --profile backup "$@"
