#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from typing import Optional, Union

from cachetools import TTLCache
from pytdbot import types

from src.logger import LOGGER


class Telegram:
    """Helper class to validate and process playable Telegram media
    messages."""

    MAX_FILE_SIZE = 600 * 1024 * 1024  # 600MB
    UNSUPPORTED_TYPES = (
        types.MessageText,
        types.MessagePhoto,
        types.MessageSticker,
        types.MessageAnimation,
    )
    DownloaderCache = TTLCache(maxsize=5000, ttl=600)

    def __init__(self, reply: Optional[types.Message]):
        """Initialize Telegram helper with a message.

        Args:
        reply (types.Message or None): A Telegram message, or None if there is no message.

        Instance variables:
        self.msg (types.Message or None): The Telegram message.
        self.content (types.MessageContent or None): The content of the message.
        self._file_info (tuple[int, str] or None): A lazy-loaded tuple containing the file size and filename.
        """
        self.msg = reply
        self.content = reply.content if reply else None
        self._file_info: Optional[tuple[int, str]] = None

    @property
    def file_info(self) -> tuple[int, str]:
        """Lazy-loaded property for file info."""
        if self._file_info is None:
            self._file_info = self._extract_file_info()
        return self._file_info

    def is_valid(self) -> bool:
        """Check if the Telegram message is valid for music playback.

        A valid Telegram message for music playback is a message that:

        1. Exists and is not an error message.
        2. Contains a supported media type (audio or video).
        3. It Has a file size greater than 0 bytes and fewer than or equal to 600MB.

        Returns:
        bool: True if the message is valid, False otherwise.
        """
        if not self.msg or isinstance(self.msg, types.Error):
            return False

        if isinstance(self.content, self.UNSUPPORTED_TYPES):
            return False

        file_size, _ = self.file_info
        return 0 < file_size <= self.MAX_FILE_SIZE

    def _extract_file_info(self) -> tuple[int, str]:
        """Extract the file size and filename from the Telegram message
        content.

        This method inspects the content of the Telegram message to determine
        the size and name of the file if the content type is supported.
        It handles various types of media content, including videos, audio files,
        voice notes, video notes, and documents with audio or video MIME types.

        Returns:
            tuple[int, str]: A tuple containing the file size in bytes and the
            filename. If the content type is unsupported or an error occurs,
            it returns (0, "UnknownMedia").
        """
        try:
            if isinstance(self.content, types.MessageVideo):
                return (
                    self.content.video.video.size,
                    self.content.video.file_name or "Video.mp4",
                )
            elif isinstance(self.content, types.MessageAudio):
                return (
                    self.content.audio.audio.size,
                    self.content.audio.file_name or "Audio.mp3",
                )
            elif isinstance(self.content, types.MessageVoiceNote):
                return self.content.voice_note.voice.size, "VoiceNote.ogg"
            elif isinstance(self.content, types.MessageVideoNote):
                return self.content.video_note.video.size, "VideoNote.mp4"
            elif isinstance(self.content, types.MessageDocument):
                mime = (self.content.document.mime_type or "").lower()
                if mime.startswith(("audio/", "video/")):
                    return (
                        self.content.document.document.size,
                        self.content.document.file_name or "Document.mp4",
                    )
        except Exception as e:
            LOGGER.error("Error while extracting file info: %s", e)

        LOGGER.info("Unsupported content type: %s", type(self.content).__name__)
        return 0, "UnknownMedia"

    async def dl(
        self, message: types.Message
    ) -> tuple[Union[types.Error, types.LocalFile], str]:
        """Download a media file from a Telegram message.

        This asynchronous method checks if the media file contained in the
        given message is valid and supported for download. If valid, it
        retrieves the file using the Telegram API and caches the download
        metadata for future reference.

        Args:
            message (types.Message): The Telegram message containing the media
            file to be downloaded.

        Returns:
            tuple[Union[types.Error, types.LocalFile], str]: A tuple containing either an
            error object with a message indicating an invalid or unsupported
            media file, or a LocalFile object representing the downloaded file
            along with the file name. In case of an error, the second element
            of the tuple is "InvalidMedia".
        """
        if not self.is_valid():
            return (
                types.Error(message="Invalid or unsupported media file."),
                "InvalidMedia",
            )

        unique_id = self.msg.remote_unique_file_id
        chat_id = message.chat_id if message else self.msg.chat_id
        _, file_name = self.file_info

        if unique_id not in Telegram.DownloaderCache:
            Telegram.DownloaderCache[unique_id] = {
                "chat_id": chat_id,
                "remote_file_id": self.msg.remote_file_id,
                "filename": file_name,
                "message_id": message.id,
            }

        file_obj = await self.msg.download(synchronous=True)
        return file_obj, file_name

    @staticmethod
    def get_cached_metadata(
        unique_id: str,
    ) -> Optional[dict[str, Union[int, str, str, int]]]:
        """Retrieve cached metadata for a Telegram media file.

        This method retrieves the cached metadata for a Telegram media file
        identified by its unique ID. The metadata includes the chat ID,
        remote file ID, filename, and message ID.

        Args:
            unique_id: The unique ID of the Telegram media file.

        Returns:
            A dictionary containing the cached metadata for the Telegram media
            file, or None if the unique ID is not found in the cache.
        """
        return Telegram.DownloaderCache.get(unique_id)

    @staticmethod
    def clear_cache(unique_id: str):
        """Clear cached metadata for a Telegram media file.

        This method removes the cached metadata for a Telegram media file
        identified by its unique ID.

        Args:
            unique_id: The unique ID of the Telegram media file.

        Returns:
            The cached metadata dictionary associated with the unique ID,
            or None if the unique ID is not found in the cache.
        """
        return Telegram.DownloaderCache.pop(unique_id, None)
