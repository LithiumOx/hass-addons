#!/usr/bin/env bash
set -euo pipefail

source /usr/lib/bashio/bashio.sh

bashio::log.info "Configuring Soft Serve add-on"

# HA maps /data for us; keep our state in /data/soft-serve
export SOFT_SERVE_DATA_PATH="${SOFT_SERVE_DATA_PATH:-/data/soft-serve}"

mkdir -p "$SOFT_SERVE_DATA_PATH"

# Read configuration provided via the add-on UI
INITIAL_ADMIN_KEY=""
if bashio::config.has_value 'initial_admin_key'; then
  INITIAL_ADMIN_KEY="$(bashio::config 'initial_admin_key')"
fi

ALLOW_KEYLESS="false"
if bashio::config.has_value 'allow_keyless'; then
  if bashio::config.true 'allow_keyless'; then
    ALLOW_KEYLESS="true"
  fi
fi

ANON_ACCESS="read"
if bashio::config.has_value 'anon_access'; then
  ANON_ACCESS="$(bashio::config 'anon_access')"
fi

# Seed initial admin key on first boot
if [ ! -f "$SOFT_SERVE_DATA_PATH/config.yaml" ]; then
  if [ -n "$INITIAL_ADMIN_KEY" ]; then
    export SOFT_SERVE_INITIAL_ADMIN_KEYS="$INITIAL_ADMIN_KEY"
  fi
fi

# Harden defaults from add-on options
export SOFT_SERVE_ANON_ACCESS="$ANON_ACCESS"
export SOFT_SERVE_ALLOW_KEYLESS="$ALLOW_KEYLESS"

# Listen on all interfaces; default SSH port is 23231 (Soft Serve default)
exec /usr/local/bin/soft serve
