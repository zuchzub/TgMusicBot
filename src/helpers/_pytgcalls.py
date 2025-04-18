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

from src import config
from src.logger import LOGGER
from src.modules.utils import PlayButton, get_audio_duration, sec_to_min, send_logger
from src.modules.utils.thumbnails import gen_thumb
from ._api import ApiData
from ._cacher import chat_cache
from ._database import db
from ._dataclass import CachedTrack
from ._downloader import MusicServiceWrapper
from ._jiosaavn import JiosaavnData
from ._youtube import YouTubeData


class CallError(Exception):
    """
    Custom exception for call-related errors.
    """

    def __init__(self, message: str):
        super().__init__(message or "Call error")


class MusicBot:
    """
    Main music bot class handling voice chat operations.
    """

    def __init__(self):
        """
        Initialize a MusicBot instance.

        This constructor sets up the initial state for the MusicBot, including:
        - `calls`: A dictionary to store PyTgCalls instances, indexed by client names.
        - `client_counter`: A counter to keep track of the number of clients.
        - `available_clients`: A list to maintain the names of available clients.
        - `bot`: An optional Client instance representing the main bot client.
        """
        self.calls: dict[str, PyTgCalls] = {}
        self.client_counter: int = 1
        self.available_clients: list[str] = []
        self.bot: Optional[Client] = None

    async def add_bot(self, client: Client) -> None:
        """
        Set the main bot client.

        This method takes a Client instance and assigns it to the bot attribute
        of the MusicBot instance. This is used to retrieve the main bot client,
        which is used for various admin tasks and sending messages.

        Parameters
        ----------
        client : Client
            Client instance to set as the main bot client.
        """
        self.bot = client

    async def _get_client_name(self, chat_id: int) -> str:
        """
        Get a client name for the given chat ID.

        This function takes a chat ID as argument and returns a client name
        associated with that chat ID. If the chat ID is 1, it will randomly
        select an available client. For group/channel IDs, it will first check
        if there is an associated client ID (assistant) in the database. If
        not, it will randomly assign an available client and update the
        database.

        Parameters
        ----------
        chat_id : int
            ID of the chat to get the client name for.

        Returns
        -------
        str
            Client name associated with the given chat ID.
        """
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
        """
        Retrieve the PyroClient instance for a given chat ID.

        This asynchronous function fetches the client associated with the
        specified chat ID. If the client is not available or not ready, it
        returns an error. The client name is determined by the `_get_client_name`
        method, and the corresponding Pyrogram client instance is retrieved from
        the `calls` dictionary. If any error occurs during the process, it logs
        the error and returns a types.Error with the appropriate message.

        Parameters
        ----------
        chat_id : int
            The ID of the chat for which the client is to be retrieved.

        Returns
        -------
        Union[PyroClient, types.Error]
            The PyroClient instance if available; otherwise, a types.Error
            indicating the error encountered.
        """
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
        """
        Start a new PyTgCalls client instance.

        This asynchronous function creates a new PyTgCalls client instance with
        the given API ID, API hash, and session string. It assigns a unique name
        to the client (in the format "clientX", where X is the client counter)
        and stores the client instance in the `calls` dictionary. It also adds
        the client name to the `available_clients` list and increments the
        client counter.

        If any error occurs during the process, it logs the error and raises the
        exception.

        Parameters
        ----------
        api_id : int
            The API ID to use for the new client.
        api_hash : str
            The API hash to use for the new client.
        session_string : str
            The session string to use for the new client.

        Returns
        -------
        None
        """
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
        """
        Registers decorators for handling updates from call instances.

        This method iterates over all PyTgCalls instances stored in the `calls`
        dictionary and registers an update handler for each instance.
        The handler processes various types of updates,
        such as `StreamEnded`, `UpdatedGroupCallParticipant`, and
        `ChatUpdate`, and performs appropriate actions such as playing the next track
        or clearing the chat cache.

        Returns
        -------
        None
        """
        for call_instance in self.calls.values():

            @call_instance.on_update()
            async def general_handler(_, update: Update):
                try:
                    LOGGER.debug("Received update: %s", update)
                    if isinstance(update, stream.StreamEnded):
                        await self.play_next(update.chat_id)
                        return None
                    elif isinstance(update, UpdatedGroupCallParticipant):
                        return None
                    elif isinstance(update, ChatUpdate) and (
                        update.status.KICKED or update.status.LEFT_GROUP
                    ):
                        chat_cache.clear_chat(update.chat_id)
                        return None
                    return None
                except Exception as e:
                    LOGGER.error("Error in general handler: %s", e)
                    return None

    async def play_media(
        self,
        chat_id: int,
        file_path: Union[str, Path],
        video: bool = False,
        ffmpeg_parameters: Optional[str] = None,
    ) -> None:
        """
        Plays media from the given file path in the specified chat.

        Parameters
        ----------
        chat_id : int
            The chat ID to play the media in.
        file_path : Union[str, Path]
            The path to the media file.
        video : bool
            Whether the media is a video or not. Defaults to False.
        ffmpeg_parameters : Optional[str]
            Optional ffmpeg parameters to use when playing the media.

        Raises
        ------
        CallError
            If there is an error playing the media, such as no active group call or
            needing to unmute the userbot first.
        """
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
        """
        Play the next song in the queue for the given chat.

        If a song is currently playing and the loop count is greater than 0,
        decrement the loop count and play the current song again. Otherwise,
        play the next song in the queue, or end the call if there are no more
        songs.

        Parameters:
        chat_id (int): The ID of the chat to play the next song for.
        """
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
        """
        Play the given song for the given chat.

        If the song is not downloaded, download it first and then play it.
        If there is an error downloading the song, send an error message and play
        the next song in the queue.

        This function will also handle updating the message with the song's
        information and a thumbnail if the thumbnail status is enabled.

        Parameters:
        chat_id (int): The ID of the chat to play the song for.
        Song (CachedTrack): The song to play.

        Returns:
        None
        """
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
        """
        Download a song using its platform handler.

        Args:
            song: CachedTrack object containing download details

        Returns:
            Optional[Path]: Path to a downloaded file if successful, None otherwise
        """
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
        """
        Handle the case where the queue is empty.

        Sends a message to the chat with some recommendations if available,
        otherwise asks the user to add some songs using /play.

        Args:
            chat_id: The chat ID to send the message to.
        """
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
        """
        End the current call in the specified chat.

        This function clears the chat cache and instructs the client to leave
        the ongoing call for the given chat ID. If the call is already invalid,
        it silently passes.
        Log any errors encountered during the process.

        Args:
            chat_id (int): The ID of the chat to end the call for.

        Returns:
            None
        """
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
        """
        Seek to a specific position in a stream.

        Args:
            chat_id: The chat ID to seek the stream for.
            file_path_or_url: The file path or URL of the stream.
            to_seek: The position to seek to, in seconds.
            duration: The total duration of the stream, in seconds.
            is_video: Whether the stream is a video or not.

        Raises:
            CallError: If there is an error seeking the stream.
        """
        try:
            is_url = bool(re.match(r"http(s)?://", file_path_or_url))
            if is_url or not os.path.isfile(file_path_or_url):
                ffmpeg_params = f"-ss {to_seek} -i {file_path_or_url} -to {duration}"
            else:
                ffmpeg_params = f"-ss {to_seek} -to {duration}"

            await self.play_media(chat_id, file_path_or_url, is_video, ffmpeg_params)
        except Exception as e:
            LOGGER.error("Error in seek_stream: %s", e)
            raise CallError(f"Error seeking stream: {e}") from e

    async def speed_change(self, chat_id: int, speed: float = 1.0) -> None:
        """
        Change the playback speed of the current song in the specified chat.

        Args:
            chat_id (int): The ID of the chat where the speed change should occur.
            speed (float): The desired playback speed, between 0.5 and 4.0.

        Raises:
            ValueError: If no song is currently playing or the speed is out of range.
            CallError: If there is an error changing the speed.
        """
        if not 0.5 <= speed <= 4.0:
            raise ValueError("Speed must be between 0.5 and 4.0")

        curr_song = chat_cache.get_current_song(chat_id)
        if not curr_song or not curr_song.file_path:
            raise ValueError("No song is currently playing in this chat!")

        try:
            await self.play_media(
                chat_id,
                curr_song.file_path,
                curr_song.is_video,
                ffmpeg_parameters=f"-atend -filter:v setpts=0.5*PTS -filter:a atempo={speed}",
            )
        except Exception as e:
            LOGGER.error("Error changing speed for chat %s: %s", chat_id, e)
            raise CallError(f"Error changing speed: {e}") from e

    async def change_volume(self, chat_id: int, volume: int) -> None:
        """
        Change the volume of the current call in the specified chat.

        This function adjusts the volume of the currently playing song to the given
        volume value within the allowed range.
        If there is no song currently playing, an error is raised.

        Args:
            chat_id (int): The ID of the chat where the volume change should occur.
            volume (int): The desired volume, between 1 and 200.

        Raises:
            ValueError: If no song is currently playing or the volume is out of range.
            CallError: If there is an error changing the volume.
        """
        try:
            client_name = await self._get_client_name(chat_id)
            await self.calls[client_name].change_volume_call(chat_id, volume)
        except Exception as e:
            LOGGER.error("Error changing volume for chat %s: %s", chat_id, e)
            raise CallError(f"Error changing volume: {e}") from e

    async def mute(self, chat_id: int) -> None:
        """
        Mute the current call.

        This function mutes the currently playing song in the specified chat.
        If there is no song currently playing, an error is raised.

        Args:
            chat_id (int): The ID of the chat where the mute should occur.

        Raises:
            CallError: If there is an error muting the call.
        """
        try:
            client_name = await self._get_client_name(chat_id)
            await self.calls[client_name].mute(chat_id)
        except Exception as e:
            LOGGER.error("Error muting chat %s: %s", chat_id, e)
            raise CallError(f"Error muting call: {e}") from e

    async def unmute(self, chat_id: int) -> None:
        """
        Unmute the current call.

        This function unmutes the currently playing song in the specified chat.
        If there is no song currently playing, an error is raised.

        Args:
            chat_id (int): The ID of the chat where the unmuting should occur.

        Raises:
            CallError: If there is an error unmuting the call.
        """
        LOGGER.info("Unmuting stream for chat %s", chat_id)
        try:
            client_name = await self._get_client_name(chat_id)
            await self.calls[client_name].unmute(chat_id)
        except Exception as e:
            LOGGER.error("Error unmuting chat %s: %s", chat_id, e)
            raise CallError(f"Error unmuting call: {e}") from e

    async def resume(self, chat_id: int) -> None:
        """
        Resume the current call.

        This function resumes the currently playing song in the specified chat.
        If there is no song currently playing, an error is raised.

        Args:
            chat_id (int): The ID of the chat where the resume should occur.

        Raises:
            CallError: If there is an error resuming the call.
        """
        LOGGER.info("Resuming stream for chat %s", chat_id)
        try:
            client_name = await self._get_client_name(chat_id)
            await self.calls[client_name].resume(chat_id)
        except Exception as e:
            LOGGER.error("Error resuming chat %s: %s", chat_id, e)
            raise CallError(f"Error resuming call: {e}") from e

    async def pause(self, chat_id: int) -> None:
        """
        Pause the current call.

        This function pauses the currently playing song in the specified chat.
        If there is no song currently playing, an error is raised.

        Args:
            chat_id (int): The ID of the chat where the pause should occur.

        Raises:
            CallError: If there is an error, pausing the call.
        """
        LOGGER.info("Pausing stream for chat %s", chat_id)
        try:
            client_name = await self._get_client_name(chat_id)
            await self.calls[client_name].pause(chat_id)
        except Exception as e:
            LOGGER.error("Error pausing chat %s: %s", chat_id, e)
            raise CallError(f"Error pausing call: {e}") from e

    async def played_time(self, chat_id: int) -> int:
        """
        Get the played time in seconds for the current call in the specified chat.

        This function retrieves the played time in seconds for the current call in the
        specified chat.
        If there is no call active in the chat, it will return 0.

        Args:
            chat_id (int): The ID of the chat to get the played time for.

        Returns:
            int: The played time in seconds.

        Raises:
            CallError: If there is an error getting the played time.
        """
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
        """
        Get a list of users in the voice chat for the specified chat.

        This function retrieves a list of users in the voice chat for the specified
        chat. If there is no call active in the chat, it will return an empty list.

        Args:
            chat_id (int): The ID of the chat to get the voice chat users for.

        Returns:
            list: A list of `GroupCallParticipant` objects representing the users
                in the voice chat.

        Raises:
            CallError: If there is an error getting the voice chat users.
        """
        LOGGER.info("Getting VC users for chat %s", chat_id)
        try:
            client_name = await self._get_client_name(chat_id)
            return await self.calls[client_name].get_participants(chat_id)
        except Exception as e:
            LOGGER.error("Error getting participants for chat %s: %s", chat_id, e)
            raise CallError(f"Error getting participants: {e}") from e

    async def stats_call(self, chat_id: int) -> tuple[float, float]:
        """
        Get the ping and CPU usage statistics.

        This function retrieves the ping and CPU usage statistics for the call in the
        specified chat.

        Args:
            chat_id (int): The ID of the chat to get the call statistics for.

        Returns:
            tuple[float, float]: A tuple containing the ping and CPU usage statistics.

        Raises:
            CallError: If there is an error getting the call statistics.
        """
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
    """
    Start all PyTgCalls clients using provided session strings.

    This asynchronous function retrieves session strings from the configuration
    and starts a PyTgCalls client for each valid session string.
    If no session strings are provided, it logs an error and exits the application.
    It logs the success or failure of starting clients using the defined logger.

    Raises
    ------
    SystemExit
        If no session strings are provided or if an error occurs while starting
        the clients.
    """
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
