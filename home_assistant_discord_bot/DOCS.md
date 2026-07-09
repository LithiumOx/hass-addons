# Home Assistant Discord Bot

This add-on runs a small Discord bot inside Home Assistant.

## Options

- `discord_bot_token`: Discord bot token. Keep this secret.
- `guild_id`: Discord server ID. Recommended so slash command updates are immediate.
- `channel_id`: Optional Discord channel ID. If set, the slash command only works there.
- `command_name`: Slash command name. Default: `on`.
- `status_interval_seconds`: How often the bot updates its Discord presence.
- `wake_timeout_seconds`: How long `/start` waits for Rocket to report online.
- `rocket_online_entity`: Home Assistant entity used as Rocket online state.
- `rocket_wake_script`: Home Assistant script entity used to wake Rocket.
- `tautulli_up_entity`: Home Assistant entity for Tautulli/Plex metrics availability.
- `plex_streams_entity`: Home Assistant entity for current Plex streams.
- `plex_transcodes_entity`: Home Assistant entity for active transcodes.
- `rocket_host`: Rocket LAN address, used as a fallback status check.
- `plex_port`: Plex port, used as a fallback status check.

## Discord Presence

The bot uses Discord status as the simple red/green indicator:

- green/online: Rocket is online
- red/do-not-disturb: Rocket is offline

The activity text says whether Rocket Plex is online or offline.
