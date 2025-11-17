# Soft Serve Git Server Home Assistant Add-on

Run Charmbracelet's [Soft Serve](https://github.com/charmbracelet/soft-serve) inside Home Assistant Supervisor. Soft Serve is a tasty self-hostable Git server with a TUI over SSH, HTTP and Git protocol remotes, LFS support, per-repo collaborators, webhooks, and repo/user management via SSH. The add-on wraps the official Soft Serve image, persists state under `/data/soft-serve`, seeds an initial admin key, and exposes SSH on port `23231` and optional HTTP/LFS on `23232`.

### Soft Serve highlights

- Browse repositories, commits, and files through an SSH-accessible TUI
- Clone and push via SSH, HTTPS, or the Git daemon, including Git LFS assets
- Create/import/delete repositories and manage collaborators, branches, tags, and webhooks directly via SSH commands
- Manage users with SSH public keys, anonymous access policies, and optional user access tokens for HTTP
- Extend with Git server-side hooks (pre-receive/update/post-update/post-receive)

Supports Home Assistant on `amd64`, `aarch64` (Raspberry Pi 4/other 64-bit ARM boards), and `armv7`.

## Configuration

The add-on exposes every upstream Soft Serve setting directly in the Home Assistant UI. Defaults match the official sample `config.yaml`, so if you never touch the form you get the same behavior as running `soft serve` locally.

### Bootstrap and access control

| Option | Description |
| --- | --- |
| `initial_admin_key` | Public key placed in `SOFT_SERVE_INITIAL_ADMIN_KEYS` on first run so you can log in as an admin immediately. |
| `additional_admin_keys` | Optional list of SSH public keys to write into the generated `config.yaml` under `initial_admin_keys`. |
| `allow_keyless` | Mirrors the upstream `allow-keyless` setting (`true` by default). Set to `false` to block password/anonymous auth. |
| `anon_access` | Default anonymous access level (`no-access`, `read-only`, `read-write`, or `admin-access`). |

### Soft Serve server settings

| Option | Maps to | Default |
| --- | --- | --- |
| `name` | `name` | `Soft Serve` |
| `log_format` | `log_format` (`text`, `logfmt`, `json`) | `text` |
| `ssh_listen_addr` | `ssh.listen_addr` | `:23231` |
| `ssh_public_url` | `ssh.public_url` | `ssh://localhost:23231` |
| `ssh_key_path` | `ssh.key_path` | `ssh/soft_serve_host` |
| `ssh_client_key_path` | `ssh.client_key_path` | `ssh/soft_serve_client` |
| `ssh_max_timeout` | `ssh.max_timeout` | `0` |
| `ssh_idle_timeout` | `ssh.idle_timeout` | `120` |
| `git_listen_addr` | `git.listen_addr` | `:9418` |
| `git_max_timeout` | `git.max_timeout` | `0` |
| `git_idle_timeout` | `git.idle_timeout` | `3` |
| `git_max_connections` | `git.max_connections` | `32` |
| `http_listen_addr` | `http.listen_addr` | `:23232` |
| `http_tls_key_path` | `http.tls_key_path` | *(empty)* |
| `http_tls_cert_path` | `http.tls_cert_path` | *(empty)* |
| `http_public_url` | `http.public_url` | `http://localhost:23232` |
| `http_cors_allowed_headers` | `http.cors.allowed_headers` | `['Accept','Accept-Language','Content-Language','Content-Type','Origin','X-Requested-With','User-Agent','Authorization','Access-Control-Request-Method','Access-Control-Allow-Origin']` |
| `http_cors_allowed_origins` | `http.cors.allowed_origins` | `['http://localhost:23232']` |
| `http_cors_allowed_methods` | `http.cors.allowed_methods` | `['GET','HEAD','POST','PUT','OPTIONS']` |
| `db_driver` | `db.driver` (`sqlite` or `postgres`) | `sqlite` |
| `db_data_source` | `db.data_source` | `soft-serve.db?_pragma=busy_timeout(5000)&_pragma=foreign_keys(1)` |
| `lfs_enabled` | `lfs.enabled` | `true` |
| `lfs_ssh_enabled` | `lfs.ssh_enabled` | `false` |
| `jobs_mirror_pull` | `jobs.mirror_pull` | `@every 10m` |
| `stats_listen_addr` | `stats.listen_addr` | `:23233` |

The add-on writes these options into `/data/soft-serve/config.yaml` on every start and points Soft Serve to that file via `SOFT_SERVE_CONFIG_LOCATION`. You can safely edit the options from the UI and restart the add-on to apply changes—your repositories remain untouched under `/data/soft-serve/`.

## Ports

| Port | Purpose |
| --- | --- |
| `23231/tcp` | Soft Serve SSH (git+ssh, TUI, and management CLI). |
| `23232/tcp` | Optional HTTP/LFS interface for clone/push over HTTP. |

## Usage

After installing, start the add-on and connect over SSH:

```bash
ssh -p 23231 git@<home-assistant-host> help
```

Create repositories and manage users via the Soft Serve CLI (available over SSH). Expose the HTTP and SSH ports with your preferred reverse proxy or tunnel if you need remote access.
