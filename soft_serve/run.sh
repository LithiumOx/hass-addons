#!/usr/bin/env bash
set -euo pipefail

source /usr/lib/bashio/bashio.sh

bashio::log.info "Configuring Soft Serve add-on"

# HA maps /data for us; keep our state in /data/soft-serve
export SOFT_SERVE_DATA_PATH="${SOFT_SERVE_DATA_PATH:-/data/soft-serve}"

mkdir -p "$SOFT_SERVE_DATA_PATH"

# Path provided by Supervisor with the current add-on options
CONFIG_PATH="${CONFIG_PATH:-/data/options.json}"

read_option_string() {
  local key="$1" default="$2" value
  if [ -f "$CONFIG_PATH" ]; then
    value="$(jq -r --arg key "$key" '.[$key] // empty' "$CONFIG_PATH" 2>/dev/null || true)"
    if [ -n "$value" ]; then
      printf '%s' "$value"
      return
    fi
  fi
  printf '%s' "$default"
}

read_option_bool() {
  local key="$1" default="$2" value
  if [ -f "$CONFIG_PATH" ]; then
    value="$(jq -r --arg key "$key" '.[$key]' "$CONFIG_PATH" 2>/dev/null || true)"
    case "$value" in
      true|false)
        printf '%s' "$value"
        return
        ;;
    esac
  fi
  printf '%s' "$default"
}

# Read configuration provided via the add-on UI
INITIAL_ADMIN_KEY="$(read_option_string 'initial_admin_key' '')"
ALLOW_KEYLESS="$(read_option_bool 'allow_keyless' 'false')"
ANON_ACCESS="$(read_option_string 'anon_access' 'read')"

# Seed/ensure admin key is provided to Soft Serve
if [ -n "$INITIAL_ADMIN_KEY" ]; then
  export SOFT_SERVE_INITIAL_ADMIN_KEYS="$INITIAL_ADMIN_KEY"
fi

# Harden defaults from add-on options
export SOFT_SERVE_ANON_ACCESS="$ANON_ACCESS"
export SOFT_SERVE_ALLOW_KEYLESS="$ALLOW_KEYLESS"

# Listen on all interfaces; default SSH port is 23231 (Soft Serve default)
exec /usr/local/bin/soft serve
