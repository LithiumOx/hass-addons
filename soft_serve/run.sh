#!/usr/bin/env bash
set -euo pipefail

source /usr/lib/bashio/bashio.sh

bashio::log.info "Configuring Soft Serve add-on"

# HA maps /data for us; keep our state in /data/soft-serve
export SOFT_SERVE_DATA_PATH="${SOFT_SERVE_DATA_PATH:-/data/soft-serve}"

mkdir -p "$SOFT_SERVE_DATA_PATH"

# Path provided by Supervisor with the current add-on options
CONFIG_PATH="${CONFIG_PATH:-/data/options.json}"

# Read configuration provided via the add-on UI
INITIAL_ADMIN_KEY=""
ALLOW_KEYLESS="true"
ANON_ACCESS="read-only"
CONFIG_JSON='{}'

if [ -f "$CONFIG_PATH" ]; then
  INITIAL_ADMIN_KEY="$(jq -r '.initial_admin_key // ""' "$CONFIG_PATH")"
  ALLOW_KEYLESS="$(jq -r '.allow_keyless // true' "$CONFIG_PATH")"
  ANON_ACCESS="$(jq -r '.anon_access // "read-only"' "$CONFIG_PATH")"
  CONFIG_JSON="$(jq -c '.' "$CONFIG_PATH")"
else
  bashio::log.warning "Add-on options not found at $CONFIG_PATH, falling back to defaults"
fi

# Seed/ensure admin key is provided to Soft Serve
if [ -n "$INITIAL_ADMIN_KEY" ]; then
  export SOFT_SERVE_INITIAL_ADMIN_KEYS="$INITIAL_ADMIN_KEY"
fi

# Harden defaults from add-on options
export SOFT_SERVE_ANON_ACCESS="$ANON_ACCESS"
export SOFT_SERVE_ALLOW_KEYLESS="$ALLOW_KEYLESS"

# Build a full Soft Serve config from the add-on options and tell Soft Serve to use it
CONFIG_FILE="$(
  ADDON_CONFIG_JSON="$CONFIG_JSON" python3 <<'PY'
import json
import os
from pathlib import Path

import yaml

options = json.loads(os.environ.get("ADDON_CONFIG_JSON", "{}"))

def get_value(key, default):
    value = options.get(key)
    return default if value is None else value

cfg = {
    "name": get_value("name", "Soft Serve"),
    "log_format": get_value("log_format", "text"),
    "ssh": {
        "listen_addr": get_value("ssh_listen_addr", ":23231"),
        "public_url": get_value("ssh_public_url", "ssh://localhost:23231"),
        "key_path": get_value("ssh_key_path", "ssh/soft_serve_host"),
        "client_key_path": get_value("ssh_client_key_path", "ssh/soft_serve_client"),
        "max_timeout": get_value("ssh_max_timeout", 0),
        "idle_timeout": get_value("ssh_idle_timeout", 120),
    },
    "git": {
        "listen_addr": get_value("git_listen_addr", ":9418"),
        "max_timeout": get_value("git_max_timeout", 0),
        "idle_timeout": get_value("git_idle_timeout", 3),
        "max_connections": get_value("git_max_connections", 32),
    },
    "http": {
        "listen_addr": get_value("http_listen_addr", ":23232"),
        "tls_key_path": get_value("http_tls_key_path", ""),
        "tls_cert_path": get_value("http_tls_cert_path", ""),
        "public_url": get_value("http_public_url", "http://localhost:23232"),
        "cors": {
            "allowed_headers": get_value("http_cors_allowed_headers", [
                "Accept",
                "Accept-Language",
                "Content-Language",
                "Content-Type",
                "Origin",
                "X-Requested-With",
                "User-Agent",
                "Authorization",
                "Access-Control-Request-Method",
                "Access-Control-Allow-Origin",
            ]),
            "allowed_origins": get_value("http_cors_allowed_origins", [
                "http://localhost:23232",
            ]),
            "allowed_methods": get_value("http_cors_allowed_methods", [
                "GET",
                "HEAD",
                "POST",
                "PUT",
                "OPTIONS",
            ]),
        },
    },
    "db": {
        "driver": get_value("db_driver", "sqlite"),
        "data_source": get_value("db_data_source", "soft-serve.db?_pragma=busy_timeout(5000)&_pragma=foreign_keys(1)"),
    },
    "lfs": {
        "enabled": get_value("lfs_enabled", True),
        "ssh_enabled": get_value("lfs_ssh_enabled", False),
    },
    "jobs": {
        "mirror_pull": get_value("jobs_mirror_pull", "@every 10m"),
    },
    "stats": {
        "listen_addr": get_value("stats_listen_addr", ":23233"),
    },
}

initial_keys = options.get("additional_admin_keys")
if initial_keys:
    cfg["initial_admin_keys"] = initial_keys

data_path = Path(os.environ["SOFT_SERVE_DATA_PATH"])
data_path.mkdir(parents=True, exist_ok=True)
config_path = data_path / "config.yaml"

with config_path.open("w", encoding="utf-8") as config_file:
    yaml.safe_dump(cfg, config_file, sort_keys=False)

print(config_path, end="")
PY
)"

export SOFT_SERVE_CONFIG_LOCATION="$CONFIG_FILE"

# Listen on all interfaces; default SSH port is 23231 (Soft Serve default)
exec /usr/local/bin/soft serve
