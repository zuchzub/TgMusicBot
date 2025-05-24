#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from typing import Optional, Union

from cachetools import TTLCache
from pytdbot import types

from src.logger import LOGGER


class Telegram:
    """
    Helper class to validate and process playable Telegram media messages.
    """

    MAX_FILE_SIZE = 1000 * 1024 * 1024  # 1000MB
    UNSUPPORTED_TYPES = (
        types.MessageText,
        types.MessagePhoto,
        types.MessageSticker,
        types.MessageAnimation,
    )
    DownloaderCache = TTLCache(maxsize=5000, ttl=600)

    def __init__(self, reply: Optional[types.Message]):
        self.msg = reply
        self.content = reply.content if reply else None
        self._file_info: Optional[tuple[int, str]] = None

    @property
    def file_info(self) -> tuple[int, str]:
        """
        Lazy-loaded property for file info.
        """
        if self._file_info is None:
            self._file_info = self._extract_file_info()
        return self._file_info

    def is_valid(self) -> bool:
        if not self.msg or isinstance(self.msg, types.Error):
            return False

        if isinstance(self.content, self.UNSUPPORTED_TYPES):
            return False

        file_size, _ = self.file_info
        return 0 < file_size <= self.MAX_FILE_SIZE

    def _extract_file_info(self) -> tuple[int, str]:
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
            return 0, "UnknownMedia"
        except Exception as e:
            LOGGER.error("Error while extracting file info: %s", e)

        LOGGER.info("Unsupported content type: %s", type(self.content).__name__)
        return 0, "UnknownMedia"

    async def dl(
        self, message: types.Message
    ) -> tuple[Union[types.Error, types.LocalFile], str]:
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

        file_obj = await self.msg.download()
        return file_obj, file_name

    @staticmethod
    def get_cached_metadata(
        unique_id: str,
    ) -> Optional[dict[str, Union[int, str, str, int]]]:
        return Telegram.DownloaderCache.get(unique_id)

    @staticmethod
    def clear_cache(unique_id: str):
        return Telegram.DownloaderCache.pop(unique_id, None)
