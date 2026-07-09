# Home Assistant Discord Bot

Home Assistant local app/add-on for a tiny Discord bot that wakes Rocket Plex.

It uses the Home Assistant Core API proxy exposed by Supervisor, so it does not
store a Home Assistant long-lived token. The Discord bot token is configured in
the add-on options UI.

## Command

Default command: `/on`

The command calls `script.rocket_wake`, then polls `binary_sensor.rocket_online`
and Plex/Tautulli sensors for status.

The bot also keeps Discord updated while idle:

- Presence is green/online when Rocket is online.
- Presence is red/do-not-disturb when Rocket is offline.
- One managed status message is created or edited in `channel_id`.

## Required Discord setup

- Create a separate Discord application for the Home Assistant bot.
- Invite it to the server with `bot` and `applications.commands` scopes.
- Add the bot token to the add-on option `discord_bot_token`.
- Set `guild_id` for fast slash-command registration.
- Set `channel_id` to the Plex bot channel for command restriction and the
  managed status message.
- In that channel, allow the HomeAssistant bot/role to view the channel, send
  messages, embed links, and read message history.
