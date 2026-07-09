from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import Any

import aiohttp
import discord
from discord import app_commands


OPTIONS_PATH = "/data/options.json"
STATUS_MESSAGE_PATH = "/data/status_message.json"
SUPERVISOR_CORE_API = "http://supervisor/core/api"
COMMAND_NAME_PATTERN = re.compile(r"^[a-z0-9_-]{1,32}$")

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger("home-assistant-discord-bot")


class ConfigError(RuntimeError):
    pass


class HomeAssistantUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Config:
    discord_bot_token: str
    guild_id: int | None
    channel_id: int | None
    command_name: str
    status_interval_seconds: int
    wake_timeout_seconds: int
    rocket_online_entity: str
    rocket_wake_script: str
    tautulli_up_entity: str
    plex_streams_entity: str
    plex_transcodes_entity: str
    rocket_host: str
    plex_port: int


@dataclass(frozen=True)
class RocketStatus:
    online: bool
    online_source: str
    plex_available: bool | None
    streams: int | None
    transcodes: int | None


def read_options() -> dict[str, Any]:
    try:
        with open(OPTIONS_PATH, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
    except FileNotFoundError:
        loaded = {}
    if not isinstance(loaded, dict):
        raise ConfigError(f"{OPTIONS_PATH} must contain a JSON object")
    return loaded


def option_str(options: dict[str, Any], name: str, default: str = "") -> str:
    value = os.environ.get(name.upper(), options.get(name, default))
    if value is None:
        return default
    return str(value).strip()


def option_int(
    options: dict[str, Any],
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    raw = option_str(options, name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} must be an integer") from exc
    if value < minimum or value > maximum:
        raise ConfigError(f"{name} must be between {minimum} and {maximum}")
    return value


def option_snowflake(options: dict[str, Any], name: str) -> int | None:
    raw = option_str(options, name)
    if not raw:
        return None
    if not raw.isdigit():
        raise ConfigError(f"{name} must be a Discord numeric ID")
    return int(raw)


def load_config() -> Config:
    options = read_options()
    token = option_str(options, "discord_bot_token")
    if not token:
        raise ConfigError("discord_bot_token is required")

    command_name = option_str(options, "command_name", "on").lower()
    if not COMMAND_NAME_PATTERN.match(command_name):
        raise ConfigError("command_name must be 1-32 lowercase letters, numbers, _ or -")

    return Config(
        discord_bot_token=token,
        guild_id=option_snowflake(options, "guild_id"),
        channel_id=option_snowflake(options, "channel_id"),
        command_name=command_name,
        status_interval_seconds=option_int(
            options, "status_interval_seconds", 30, 10, 3600
        ),
        wake_timeout_seconds=option_int(options, "wake_timeout_seconds", 180, 30, 900),
        rocket_online_entity=option_str(
            options, "rocket_online_entity", "binary_sensor.rocket_online"
        ),
        rocket_wake_script=option_str(options, "rocket_wake_script", "script.rocket_wake"),
        tautulli_up_entity=option_str(
            options, "tautulli_up_entity", "sensor.rocket_tautulli_up"
        ),
        plex_streams_entity=option_str(
            options, "plex_streams_entity", "sensor.rocket_plex_streams"
        ),
        plex_transcodes_entity=option_str(
            options, "plex_transcodes_entity", "sensor.rocket_plex_transcodes"
        ),
        rocket_host=option_str(options, "rocket_host", "192.168.1.22"),
        plex_port=option_int(options, "plex_port", 32400, 1, 65535),
    )


def state_is_available(state: str | None) -> bool:
    return state not in (None, "", "unknown", "unavailable")


def state_to_int(value: str | None) -> int | None:
    if not state_is_available(value):
        return None
    try:
        return int(float(str(value)))
    except ValueError:
        return None


class HomeAssistantClient:
    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        self.session = session
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    async def get_state(self, entity_id: str) -> dict[str, Any] | None:
        url = f"{SUPERVISOR_CORE_API}/states/{entity_id}"
        try:
            async with self.session.get(url, headers=self.headers, timeout=5) as response:
                if response.status == 404:
                    return None
                if response.status in (502, 503, 504):
                    raise HomeAssistantUnavailable(
                        f"Home Assistant API returned HTTP {response.status}"
                    )
                response.raise_for_status()
                payload = await response.json()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise HomeAssistantUnavailable(str(exc)) from exc
        return payload if isinstance(payload, dict) else None

    async def call_script(self, entity_id: str) -> None:
        url = f"{SUPERVISOR_CORE_API}/services/script/turn_on"
        payload = {"entity_id": entity_id}
        try:
            async with self.session.post(
                url, headers=self.headers, json=payload, timeout=10
            ) as response:
                if response.status in (502, 503, 504):
                    raise HomeAssistantUnavailable(
                        f"Home Assistant API returned HTTP {response.status}"
                    )
                response.raise_for_status()
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise HomeAssistantUnavailable(str(exc)) from exc


class RocketStatusService:
    def __init__(self, config: Config, ha: HomeAssistantClient) -> None:
        self.config = config
        self.ha = ha

    async def snapshot(self) -> RocketStatus:
        ha_error: str | None = None
        try:
            online_state = await self.ha.get_state(self.config.rocket_online_entity)
        except HomeAssistantUnavailable as exc:
            online_state = None
            ha_error = str(exc) or "unavailable"
        online_raw = online_state.get("state") if online_state else None
        plex_port_open = await self._plex_port_open()

        if plex_port_open:
            online = True
            online_source = f"{self.config.rocket_host}:{self.config.plex_port}"
        elif ha_error is not None:
            online = False
            online_source = f"home-assistant-api={ha_error}"
        elif online_raw == "on":
            online = False
            online_source = (
                f"{self.config.rocket_online_entity}=on, "
                f"{self.config.rocket_host}:{self.config.plex_port}=closed"
            )
        else:
            online = False
            online_source = self.config.rocket_online_entity

        if ha_error is not None:
            return RocketStatus(
                online=online,
                online_source=online_source,
                plex_available=None,
                streams=None,
                transcodes=None,
            )

        try:
            tautulli_state = await self.ha.get_state(self.config.tautulli_up_entity)
            streams_state = await self.ha.get_state(self.config.plex_streams_entity)
            transcodes_state = await self.ha.get_state(self.config.plex_transcodes_entity)
        except HomeAssistantUnavailable as exc:
            return RocketStatus(
                online=online,
                online_source=f"{online_source}, metrics=home-assistant-api:{exc}",
                plex_available=None,
                streams=None,
                transcodes=None,
            )

        tautulli_raw = tautulli_state.get("state") if tautulli_state else None
        plex_available = None
        if state_is_available(tautulli_raw):
            plex_available = tautulli_raw in ("1", "on", "true", "True")

        return RocketStatus(
            online=online,
            online_source=online_source,
            plex_available=plex_available,
            streams=state_to_int(streams_state.get("state") if streams_state else None),
            transcodes=state_to_int(
                transcodes_state.get("state") if transcodes_state else None
            ),
        )

    async def wake(self) -> None:
        await self.ha.call_script(self.config.rocket_wake_script)

    async def _plex_port_open(self) -> bool:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self.config.rocket_host, self.config.plex_port),
                timeout=2,
            )
        except OSError:
            return False
        except asyncio.TimeoutError:
            return False
        writer.close()
        await writer.wait_closed()
        return True


def format_status(status: RocketStatus) -> str:
    if not status.online:
        return "Rocket Plex is offline."

    details: list[str] = []
    if status.plex_available is False:
        details.append("Plex metrics unavailable")
    elif status.plex_available is True:
        details.append("Plex metrics online")
    if status.streams is not None:
        details.append(f"{status.streams} stream{'s' if status.streams != 1 else ''}")
    if status.transcodes is not None:
        details.append(
            f"{status.transcodes} transcode{'s' if status.transcodes != 1 else ''}"
        )

    if details:
        return f"Rocket Plex is online: {', '.join(details)}."
    return "Rocket Plex is online."


class RocketWakeBot(discord.Client):
    def __init__(self, config: Config, status_service: RocketStatusService) -> None:
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(
            intents=intents,
            allowed_mentions=discord.AllowedMentions.none(),
        )
        self.config = config
        self.status_service = status_service
        self.tree = app_commands.CommandTree(self)
        self.presence_task: asyncio.Task[None] | None = None
        self.last_presence_online: bool | None = None
        self.last_status_message_online: bool | None = None

        async def start_command(interaction: discord.Interaction) -> None:
            await self.handle_start(interaction)

        self.tree.add_command(
            app_commands.Command(
                name=self.config.command_name,
                description="Wake Rocket Plex and show its status.",
                callback=start_command,
            )
        )

    async def setup_hook(self) -> None:
        if self.config.guild_id is not None:
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            LOGGER.info("Synced %s guild command(s)", len(synced))
        else:
            synced = await self.tree.sync()
            LOGGER.info("Synced %s global command(s)", len(synced))

        self.presence_task = asyncio.create_task(self.presence_loop())

    async def on_ready(self) -> None:
        LOGGER.info("Logged in as %s (%s)", self.user, self.user.id if self.user else "?")

    async def close(self) -> None:
        if self.presence_task is not None:
            self.presence_task.cancel()
        await super().close()

    async def presence_loop(self) -> None:
        await self.wait_until_ready()
        while not self.is_closed():
            try:
                status = await self.status_service.snapshot()
                await self.apply_presence(status)
                await self.publish_status_message(status)
            except Exception:
                LOGGER.exception("Failed to update Discord status")
            await asyncio.sleep(self.config.status_interval_seconds)

    async def apply_presence(self, status: RocketStatus) -> None:
        discord_status = discord.Status.online if status.online else discord.Status.dnd
        text = "Rocket Plex online" if status.online else "Rocket Plex offline"
        await self.change_presence(
            status=discord_status,
            activity=discord.Activity(type=discord.ActivityType.watching, name=text),
        )
        if self.last_presence_online != status.online:
            LOGGER.info(
                "Discord presence updated online=%s source=%s",
                status.online,
                status.online_source,
            )
            self.last_presence_online = status.online

    async def publish_status_message(self, status: RocketStatus) -> None:
        if self.config.channel_id is None:
            return
        if self.last_status_message_online == status.online:
            return

        try:
            channel = self.get_channel(self.config.channel_id)
            if channel is None:
                channel = await self.fetch_channel(self.config.channel_id)
        except discord.Forbidden:
            LOGGER.warning(
                "Missing Discord access to configured status channel %s",
                self.config.channel_id,
            )
            self.last_status_message_online = status.online
            return

        description = format_status(status)
        embed = discord.Embed(
            title="Rocket Plex status",
            description=description,
            color=0x2ECC71 if status.online else 0xE74C3C,
        )
        embed.set_footer(text=f"Source: {status.online_source}")

        message_id = self.read_status_message_id()
        message = None
        try:
            if message_id is not None and hasattr(channel, "fetch_message"):
                try:
                    message = await channel.fetch_message(message_id)
                except discord.NotFound:
                    message = None

            content = "Rocket Plex is online." if status.online else "Rocket Plex is offline."
            if message is None:
                if not hasattr(channel, "send"):
                    LOGGER.warning("Configured Discord channel cannot receive status messages")
                    return
                message = await channel.send(content=content, embed=embed)
                self.write_status_message_id(message.id)
            else:
                await message.edit(content=content, embed=embed)
        except discord.Forbidden:
            LOGGER.warning(
                "Missing Discord permission to send or edit status messages in channel %s",
                self.config.channel_id,
            )
            self.last_status_message_online = status.online
            return

        LOGGER.info(
            "Discord channel status message updated online=%s message_id=%s",
            status.online,
            message.id,
        )
        self.last_status_message_online = status.online

    def read_status_message_id(self) -> int | None:
        try:
            with open(STATUS_MESSAGE_PATH, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (FileNotFoundError, json.JSONDecodeError):
            return None
        message_id = payload.get("message_id") if isinstance(payload, dict) else None
        if isinstance(message_id, int):
            return message_id
        if isinstance(message_id, str) and message_id.isdigit():
            return int(message_id)
        return None

    def write_status_message_id(self, message_id: int) -> None:
        with open(STATUS_MESSAGE_PATH, "w", encoding="utf-8") as handle:
            json.dump({"message_id": str(message_id)}, handle)

    async def handle_start(self, interaction: discord.Interaction) -> None:
        LOGGER.info(
            "Received /%s interaction channel_id=%s user_id=%s",
            self.config.command_name,
            interaction.channel_id,
            interaction.user.id if interaction.user else "?",
        )
        if (
            self.config.channel_id is not None
            and interaction.channel_id != self.config.channel_id
        ):
            LOGGER.info(
                "Rejected /%s interaction from channel %s; configured channel is %s",
                self.config.command_name,
                interaction.channel_id,
                self.config.channel_id,
            )
            await interaction.response.send_message(
                "Use this in the configured Rocket/Plex bot channel.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        before = await self.status_service.snapshot()
        if before.online:
            await self.apply_presence(before)
            await interaction.edit_original_response(content=format_status(before))
            return

        try:
            await self.status_service.wake()
        except HomeAssistantUnavailable as exc:
            await interaction.edit_original_response(
                content=(
                    "Home Assistant is not accepting the wake command right now, "
                    f"so I could not wake Rocket. Last status: {before.online_source}. "
                    f"Error: {exc}"
                )
            )
            return
        await interaction.edit_original_response(
            content="Sent Rocket wake command through Home Assistant. Waiting for Plex..."
        )

        deadline = time.monotonic() + self.config.wake_timeout_seconds
        last_status = before
        while time.monotonic() < deadline:
            await asyncio.sleep(5)
            last_status = await self.status_service.snapshot()
            await self.apply_presence(last_status)
            if last_status.online:
                await interaction.edit_original_response(
                    content=f"Woke Rocket. {format_status(last_status)}"
                )
                return

        await interaction.edit_original_response(
            content=(
                "Sent Rocket wake command through Home Assistant, but Rocket did not "
                f"report online within {self.config.wake_timeout_seconds} seconds. "
                f"Last check: {format_status(last_status)}"
            )
        )


async def amain() -> None:
    config = load_config()
    supervisor_token = os.environ.get("SUPERVISOR_TOKEN")
    if not supervisor_token:
        raise ConfigError("SUPERVISOR_TOKEN is required; enable homeassistant_api")

    LOGGER.info(
        "Starting Home Assistant Discord Bot command=/%s guild_id=%s channel_id=%s",
        config.command_name,
        config.guild_id or "global",
        config.channel_id or "any",
    )

    async with aiohttp.ClientSession() as session:
        ha = HomeAssistantClient(session, supervisor_token)
        status_service = RocketStatusService(config, ha)
        bot = RocketWakeBot(config, status_service)
        await bot.start(config.discord_bot_token)


def main() -> None:
    try:
        asyncio.run(amain())
    except ConfigError as exc:
        LOGGER.error("Configuration error: %s", exc)
        raise SystemExit(78) from exc


if __name__ == "__main__":
    main()
