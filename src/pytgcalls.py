#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import os
import random
import re
from pathlib import Path
from typing import Optional, Union

from ntgcalls import TelegramServerError
from pyrogram import Client as PyroClient
from pyrogram import errors
from pytdbot import Client, types

import config
from pytgcalls import PyTgCalls, exceptions
from pytgcalls.types import (
    AudioQuality,
    ChatUpdate,
    MediaStream,
    Update,
    UpdatedGroupCallParticipant,
    VideoQuality,
    stream,
)
from src.database import db
from src.logger import LOGGER
from src.modules.utils import PlayButton, get_audio_duration, sec_to_min, send_logger
from src.modules.utils.cacher import chat_cache
from src.modules.utils.thumbnails import gen_thumb
from src.platforms import ApiData, JiosaavnData, YouTubeData
from src.platforms.dataclass import CachedTrack
from src.platforms.downloader import MusicServiceWrapper


class CallError(Exception):
    """Custom exception for call-related errors."""

    def __init__(self, message: str):
        super().__init__(message)


class MusicBot:
    """Main music bot class handling voice chat operations."""

    def __init__(self):
        self.calls: dict[str, PyTgCalls] = {}
        self.client_counter: int = 1
        self.available_clients: list[str] = []
        self.bot: Optional[Client] = None

    async def add_bot(self, client: Client) -> None:
        """Add the main bot client."""
        self.bot = client

    async def _get_client_name(self, chat_id: int) -> str:
        """Get the associated client for a specific chat ID."""
        if chat_id == 1:  # Special case for random client selection
            if not self.available_clients:
                raise RuntimeError("No available clients!")
            return random.choice(self.available_clients)

        # For groups/channels
        assistant = await db.get_assistant(chat_id)
        if assistant and assistant in self.available_clients:
            return assistant

        if not self.available_clients:
            raise RuntimeError("No available clients to assign!")

        new_client = random.choice(self.available_clients)
        await db.set_assistant(chat_id, assistant=new_client)
        return new_client

    async def get_client(self, chat_id: int) -> Union[PyroClient, types.Error]:
        """Get the Pyrogram client for a specific chat ID."""
        try:
            client_name = await self._get_client_name(chat_id)
            ub = self.calls[client_name].mtproto_client

            if ub is None or not hasattr(ub, "me") or ub.me is None:
                return types.Error(code=400, message="Client not found or not ready")

            return ub
        except Exception as e:
            LOGGER.error("Error getting client for chat %s: %s", chat_id, e)
            return types.Error(code=500, message=str(e))

    async def start_client(
        self, api_id: int, api_hash: str, session_string: str
    ) -> None:
        """Start a new Pyrogram client and PyTgCalls instance."""
        client_name = f"client{self.client_counter}"
        try:
            user_bot = PyroClient(
                client_name,
                api_id=api_id,
                api_hash=api_hash,
                session_string=session_string,
            )
            calls = PyTgCalls(user_bot, cache_duration=100)
            self.calls[client_name] = calls
            self.available_clients.append(client_name)
            self.client_counter += 1

            await calls.start()
            LOGGER.info("Client %s started successfully", client_name)
        except Exception as e:
            LOGGER.error("Error starting client %s: %s", client_name, e)
            raise

    async def register_decorators(self) -> None:
        """Register event handlers for all clients."""
        for call_instance in self.calls.values():

            @call_instance.on_update()
            async def general_handler(_, update: Update):
                try:
                    LOGGER.debug("Received update: %s", update)
                    if isinstance(update, stream.StreamEnded):
                        await self.play_next(update.chat_id)
                        return
                    elif isinstance(update, UpdatedGroupCallParticipant):
                        return
                    elif isinstance(update, ChatUpdate) and (
                        update.status.KICKED or update.status.LEFT_GROUP
                    ):
                        chat_cache.clear_chat(update.chat_id)
                        return
                    else:
                        return
                except Exception as e:
                    LOGGER.error("Error in general handler: %s", e)

    async def play_media(
        self,
        chat_id: int,
        file_path: Union[str, Path],
        video: bool = False,
        ffmpeg_parameters: Optional[str] = None,
    ) -> None:
        """Play media on a specific client."""
        LOGGER.info("Playing media for chat %s: %s", chat_id, file_path)
        try:
            _stream = MediaStream(
                audio_path=file_path,
                media_path=file_path,
                audio_parameters=AudioQuality.HIGH if video else AudioQuality.STUDIO,
                video_parameters=(
                    VideoQuality.FHD_1080p if video else VideoQuality.SD_360p
                ),
                video_flags=(
                    MediaStream.Flags.AUTO_DETECT if video else MediaStream.Flags.IGNORE
                ),
                ffmpeg_parameters=ffmpeg_parameters,
            )

            client_name = await self._get_client_name(chat_id)
            await self.calls[client_name].play(chat_id, _stream)
            if await db.get_logger_status(self.bot.me.id):
                asyncio.create_task(
                    send_logger(self.bot, chat_id, chat_cache.get_current_song(chat_id))
                )
        except (errors.ChatAdminRequired, exceptions.NoActiveGroupCall) as e:
            LOGGER.warning("Error playing media for chat %s: %s", chat_id, e)
            chat_cache.clear_chat(chat_id)
            raise CallError(
                "No active group call \nPlease start a call and try again"
            ) from e
        except TelegramServerError as e:
            LOGGER.warning(
                "Error playing media for chat %s: TelegramServerError", chat_id
            )
            raise CallError("TelegramServerError\ntry again after some time") from e
        except exceptions.UnMuteNeeded as e:
            LOGGER.warning("Error playing media for chat %s: %s", chat_id, e)
            raise CallError(
                "Needed to unmute the userbot first \nPlease unmute my assistant and try again"
            ) from e
        except Exception as e:
            LOGGER.error("Error playing media for chat %s: %s", chat_id, e)
            raise CallError(f"Error playing media: {e}") from e

    async def play_next(self, chat_id: int) -> None:
        """Handle song queue logic."""
        LOGGER.info("Playing next song for chat %s", chat_id)
        try:
            loop = chat_cache.get_loop_count(chat_id)
            if loop > 0:
                chat_cache.set_loop_count(chat_id, loop - 1)
                if current_song := chat_cache.get_current_song(chat_id):
                    await self._play_song(chat_id, current_song)
                    return

            if next_song := chat_cache.get_next_song(chat_id):
                chat_cache.remove_current_song(chat_id)
                await self._play_song(chat_id, next_song)
            else:
                await self._handle_no_songs(chat_id)
        except Exception as e:
            LOGGER.error("Error in play_next for chat %s: %s", chat_id, e)

    async def _play_song(self, chat_id: int, song: CachedTrack) -> None:
        """Download and play a song."""
        LOGGER.info("Playing song for chat %s", chat_id)
        try:
            reply = await self.bot.sendTextMessage(chat_id, "⏹️ Loading... Please wait.")
            if isinstance(reply, types.Error):
                LOGGER.error("Error sending message: %s", reply)
                return

            file_path = song.file_path or await self.song_download(song)
            if not file_path:
                await reply.edit_text("❌ Error downloading song. Playing next...")
                await self.play_next(chat_id)
                return

            await self.play_media(chat_id, file_path, video=song.is_video)

            duration = song.duration or await get_audio_duration(file_path)
            text = (
                f"<b>Now playing <a href='{song.thumbnail or 'https://t.me/FallenProjects'}'>:</a></b>\n\n"
                f"‣ <b>Title:</b> {song.name}\n"
                f"‣ <b>Duration:</b> {sec_to_min(duration)}\n"
                f"‣ <b>Requested by:</b> {song.user}"
            )

            thumbnail = (
                await gen_thumb(song) if await db.get_thumb_status(chat_id) else ""
            )
            parse = await self.bot.parseTextEntities(text, types.TextParseModeHTML())
            if isinstance(parse, types.Error):
                LOGGER.error("Parse error: %s", parse)
                parse = parse.message
            if thumbnail:
                input_content = types.InputMessagePhoto(
                    photo=types.InputFileLocal(thumbnail), caption=parse
                )
                reply = await self.bot.editMessageMedia(
                    chat_id=chat_id,
                    message_id=reply.id,
                    input_message_content=input_content,
                    reply_markup=(
                        PlayButton if await db.get_buttons_status(chat_id) else None
                    ),
                )
            else:
                reply = await self.bot.editMessageText(
                    chat_id=chat_id,
                    message_id=reply.id,
                    input_message_content=types.InputMessageText(
                        text=parse,
                        link_preview_options=types.LinkPreviewOptions(is_disabled=True),
                    ),
                    reply_markup=(
                        PlayButton if await db.get_buttons_status(chat_id) else None
                    ),
                )
            if isinstance(reply, types.Error):
                LOGGER.warning("Error editing message: %s", reply)
                return
        except Exception as e:
            LOGGER.error("Error in _play_song for chat %s: %s", chat_id, e)

    @staticmethod
    async def song_download(song: CachedTrack) -> Optional[Path]:
        """Handle song downloading based on platform."""
        platform_handlers = {
            "youtube": YouTubeData(song.track_id),
            "jiosaavn": JiosaavnData(song.url),
            "spotify": ApiData(song.track_id),
            "apple_music": ApiData(song.url),
            "soundcloud": ApiData(song.url),
        }

        if handler := platform_handlers.get(song.platform.lower()):
            if track := await handler.get_track():
                return await handler.download_track(track, song.is_video)

        LOGGER.warning(
            "Unknown platform: %s for track: %s", song.platform, song.track_id
        )
        return None

    async def _handle_no_songs(self, chat_id: int) -> None:
        """Handle the case when there are no songs left in the queue."""
        try:
            await self.end(chat_id)

            if recommendations := await MusicServiceWrapper().get_recommendations():
                buttons = [
                    [
                        types.InlineKeyboardButton(
                            f"{track.name[:18]} - {track.artist}",
                            type=types.InlineKeyboardButtonTypeCallback(
                                f"play_{track.platform}_{track.id}".encode()
                            ),
                        )
                    ]
                    for track in recommendations.tracks
                ]

                reply = await self.bot.sendTextMessage(
                    chat_id,
                    text="No more songs in queue. Here are some recommendations:\n\n",
                    reply_markup=types.ReplyMarkupInlineKeyboard(buttons),
                )

                if isinstance(reply, types.Error):
                    LOGGER.warning("Error sending recommendations: %s", reply)
                return

            reply = await self.bot.sendTextMessage(
                chat_id, text="No more songs in queue. Use /play to add some."
            )

            if isinstance(reply, types.Error):
                LOGGER.warning("Error sending empty queue message: %s", reply)

        except Exception as e:
            LOGGER.error("Error in _handle_no_songs for chat %s: %s", chat_id, e)

    async def end(self, chat_id: int) -> None:
        """End the current call."""
        LOGGER.info("Ending call for chat %s", chat_id)
        try:
            chat_cache.clear_chat(chat_id)
            client_name = await self._get_client_name(chat_id)
            await self.calls[client_name].leave_call(chat_id)
        except errors.GroupCallInvalid:
            pass
        except Exception as e:
            LOGGER.error("Error ending call for chat %s: %s", chat_id, e)

    async def seek_stream(
        self,
        chat_id: int,
        file_path_or_url: str,
        to_seek: int,
        duration: int,
        is_video: bool,
    ) -> None:
        """Seek to a specific position in the stream."""
        try:
            is_url = bool(re.match(r"http(s)?://", file_path_or_url))
            if is_url or not os.path.isfile(file_path_or_url):
                ffmpeg_params = f"-ss {to_seek} -i {file_path_or_url} -to {duration}"
            else:
                ffmpeg_params = f"-ss {to_seek} -to {duration}"

            await self.play_media(
                chat_id, file_path_or_url, is_video, ffmpeg_parameters=ffmpeg_params
            )
        except Exception as e:
            LOGGER.error("Error in seek_stream: %s", e)
            raise CallError(f"Error seeking stream: {e}") from e

    async def speed_change(self, chat_id: int, speed: float = 1.0) -> None:
        """Change the playback speed (0.5x to 4.0x)."""
        if not 0.5 <= speed <= 4.0:
            raise ValueError("Speed must be between 0.5 and 4.0")

        curr_song = chat_cache.get_current_song(chat_id)
        if not curr_song or not curr_song.file_path:
            raise ValueError("No song is currently playing in this chat!")

        try:
            await self.play_media(
                chat_id,
                curr_song.file_path,
                video=curr_song.is_video,
                ffmpeg_parameters=f"-atend -filter:v setpts=0.5*PTS -filter:a atempo={speed}",
            )
        except Exception as e:
            LOGGER.error("Error changing speed for chat %s: %s", chat_id, e)
            raise CallError(f"Error changing speed: {e}") from e

    async def change_volume(self, chat_id: int, volume: int) -> None:
        """Change the volume of the current call."""
        try:
            client_name = await self._get_client_name(chat_id)
            await self.calls[client_name].change_volume_call(chat_id, volume)
        except Exception as e:
            LOGGER.error("Error changing volume for chat %s: %s", chat_id, e)
            raise CallError(f"Error changing volume: {e}") from e

    async def mute(self, chat_id: int) -> None:
        """Mute the current call."""
        try:
            client_name = await self._get_client_name(chat_id)
            await self.calls[client_name].mute(chat_id)
        except Exception as e:
            LOGGER.error("Error muting chat %s: %s", chat_id, e)
            raise CallError(f"Error muting call: {e}") from e

    async def unmute(self, chat_id: int) -> None:
        """Unmute the current call."""
        LOGGER.info("Unmuting stream for chat %s", chat_id)
        try:
            client_name = await self._get_client_name(chat_id)
            await self.calls[client_name].unmute(chat_id)
        except Exception as e:
            LOGGER.error("Error unmuting chat %s: %s", chat_id, e)
            raise CallError(f"Error unmuting call: {e}") from e

    async def resume(self, chat_id: int) -> None:
        """Resume the current call."""
        LOGGER.info("Resuming stream for chat %s", chat_id)
        try:
            client_name = await self._get_client_name(chat_id)
            await self.calls[client_name].resume(chat_id)
        except Exception as e:
            LOGGER.error("Error resuming chat %s: %s", chat_id, e)
            raise CallError(f"Error resuming call: {e}") from e

    async def pause(self, chat_id: int) -> None:
        """Pause the current call."""
        LOGGER.info("Pausing stream for chat %s", chat_id)
        try:
            client_name = await self._get_client_name(chat_id)
            await self.calls[client_name].pause(chat_id)
        except Exception as e:
            LOGGER.error("Error pausing chat %s: %s", chat_id, e)
            raise CallError(f"Error pausing call: {e}") from e

    async def played_time(self, chat_id: int) -> int:
        """Get the played time of the current call."""
        LOGGER.info("Getting played time for chat %s", chat_id)
        try:
            client_name = await self._get_client_name(chat_id)
            return await self.calls[client_name].time(chat_id)
        except exceptions.NotInCallError:
            chat_cache.clear_chat(chat_id)
            return 0
        except Exception as e:
            LOGGER.error("Error getting played time for chat %s: %s", chat_id, e)
            raise CallError(f"Error getting played time: {e}") from e

    async def vc_users(self, chat_id: int) -> list:
        """Get the list of participants in the current call."""
        LOGGER.info("Getting VC users for chat %s", chat_id)
        try:
            client_name = await self._get_client_name(chat_id)
            return await self.calls[client_name].get_participants(chat_id)
        except Exception as e:
            LOGGER.error("Error getting participants for chat %s: %s", chat_id, e)
            raise CallError(f"Error getting participants: {e}") from e

    async def stats_call(self, chat_id: int) -> tuple[float, float]:
        """Get call statistics (ping and CPU usage)."""
        try:
            client_name = await self._get_client_name(chat_id)
            return (
                self.calls[client_name].ping,
                await self.calls[client_name].cpu_usage,
            )
        except Exception as e:
            LOGGER.error("Error getting stats for chat %s: %s", chat_id, e)
            raise CallError(f"Error getting call stats: {e}") from e


async def start_clients() -> None:
    """Start PyTgCalls clients."""
    session_strings = [s for s in config.SESSION_STRINGS if s]
    if not session_strings:
        LOGGER.error("No STRING session provided. Exiting...")
        raise SystemExit(1)

    try:
        await asyncio.gather(
            *[
                call.start_client(config.API_ID, config.API_HASH, s)
                for s in session_strings
            ]
        )
        LOGGER.info("✅ Clients started successfully.")
    except Exception as exc:
        LOGGER.error("Error starting clients: %s", exc)
        raise SystemExit(1) from exc


call: MusicBot = MusicBot()
