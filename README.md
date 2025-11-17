# Home Assistant Add-ons

This repository bundles community add-ons for Home Assistant Supervisor. Each
add-on packages a third-party service and exposes it to Home Assistant with sane
defaults and persistent storage under `/data/addons/data/<slug>`.

## Available add-ons

| Add-on | Service | Description |
| --- | --- | --- |
| [`soft_serve`](soft_serve) | [Charm Soft Serve](https://github.com/charmbracelet/soft-serve) | Self-hostable Git server with SSH, HTTP/LFS, and an SSH-accessible TUI. |

Install this repository under **Settings → Add-ons → Add-on Store → Repositories**
and then install whichever services you need.
