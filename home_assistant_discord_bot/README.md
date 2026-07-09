# Home Assistant Discord Bot

Home Assistant local app/add-on for a tiny Discord bot that wakes Rocket Plex.

It uses the Home Assistant Core API proxy exposed by Supervisor, so it does not
store a Home Assistant long-lived token. The Discord bot token is configured in
the add-on options UI.

## Command

Default command: `/on`

The command calls `script.rocket_wake`, then polls `binary_sensor.rocket_online`
and Plex/Tautulli sensors for status.

## Required Discord setup

- Create a separate Discord application for the Home Assistant bot.
- Invite it to the server with `bot` and `applications.commands` scopes.
- Add the bot token to the add-on option `discord_bot_token`.
- Set `guild_id` for fast slash-command registration.
- Set `channel_id` to the Plex bot channel if you want to restrict usage there.
