# Soft Serve Git Server Home Assistant Add-on

Run Charmbracelet's Soft Serve inside Home Assistant Supervisor. The add-on wraps the official Soft Serve image, persists state under `/data/soft-serve`, seeds an initial admin key, and exposes SSH on port `23231` and optional HTTP/LFS on `23232`.

Supports Home Assistant on `amd64`, `aarch64` (Raspberry Pi 4/other 64-bit ARM boards), and `armv7`.

## Configuration

Set these options on the add-on configuration tab:

| Option | Description |
| --- | --- |
| `initial_admin_key` | Your public key (e.g. `~/.ssh/id_ed25519.pub`) used to bootstrap the admin user on first start. |
| `allow_keyless` | Whether to allow unknown SSH keys. Leave `false` for hardened access. |
| `anon_access` | Anonymous repository access policy: `read` or `none`. |

Soft Serve stores its data in `/data/soft-serve/` inside the add-on, so upgrades and restarts keep repositories, users, and configuration intact.

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
