#!/usr/bin/env bash
# MIRAGE plain-script attacker. LAB ONLY: targets our own throwaway lab container.
set -euo pipefail
exec python -m mirage.attacker.scripted --profile script "$@"
