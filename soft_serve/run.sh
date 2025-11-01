#!/usr/bin/env bash
set -euo pipefail

# HA maps /data for us; keep our state in /data/soft-serve
export SOFT_SERVE_DATA_PATH=${SOFT_SERVE_DATA_PATH:-/data/soft-serve}

mkdir -p "$SOFT_SERVE_DATA_PATH"

# Seed initial admin key on first boot
if [ ! -f "$SOFT_SERVE_DATA_PATH/config.yaml" ]; then
  if [ -n "${INITIAL_ADMIN_KEY:-}" ]; then
    export SOFT_SERVE_INITIAL_ADMIN_KEYS="$INITIAL_ADMIN_KEY"
  fi
fi

# Harden defaults from add-on options
# anon-access: "none" or "read"
if [ -n "${ANON_ACCESS:-}" ]; then
  export SOFT_SERVE_ANON_ACCESS="$ANON_ACCESS"
fi
# allow-keyless: true/false
if [ -n "${ALLOW_KEYLESS:-}" ]; then
  export SOFT_SERVE_ALLOW_KEYLESS="$ALLOW_KEYLESS"
fi

# Listen on all interfaces; default SSH port is 23231 (Soft Serve default)
exec /usr/local/bin/soft serve
