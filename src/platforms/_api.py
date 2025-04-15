#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import re
from pathlib import Path
from typing import Optional, Union

import config
from src.logger import LOGGER

from ._dl_helper import SpotifyDownload
from ._httpx import HttpxClient
from .dataclass import MusicTrack, PlatformTracks, TrackInfo
from .downloader import MusicService


class ApiData(MusicService):
    APPLE_MUSIC_PATTERN = re.compile(
        r"^(https?://)?(music\.apple\.com/([a-z]{2}/)?(album|playlist|song)/[a-zA-Z0-9\-_]+/[0-9]+)(\?.*)?$",
        re.IGNORECASE,
    )
    SPOTIFY_PATTERN = re.compile(
        r"^(https?://)?(open\.spotify\.com/(track|playlist|album|artist)/[a-zA-Z0-9]+)(\?.*)?$",
        re.IGNORECASE,
    )

    API_URL = config.API_URL

    def __init__(self, query: Optional[str] = None) -> None:
        self.query = query
        self.client = HttpxClient()

    def is_valid(self, url: Optional[str]) -> bool:
        """Check if the URL is a valid music service URL."""
        if not (self.API_URL and config.API_KEY):
            LOGGER.warning("API_URL or API_KEY is not configured.")
            return False

        if not url:
            return False

        return any(
            [
                self.APPLE_MUSIC_PATTERN.match(url),
                self.SPOTIFY_PATTERN.match(url),
                "soundcloud" in url.lower(),
            ]
        )

    async def _fetch_data(self, endpoint: str) -> Optional[dict]:
        """Helper method to make API requests and handle errors."""
        try:
            return await self.client.make_request(f"{self.API_URL}/{endpoint}")
        except Exception as e:
            LOGGER.error("Error fetching data from %s: %s", endpoint, str(e))
            return None

    async def get_recommendations(self, limit: int = 4) -> Optional[PlatformTracks]:
        """Get recommended tracks."""
        data = await self._fetch_data(f"recommend_songs?lim={limit}")
        return self._create_platform_tracks(data) if data else None

    async def get_info(self) -> Optional[PlatformTracks]:
        """Get track information from a URL."""
        if not self.query or not self.is_valid(self.query):
            return None

        data = await self._fetch_data(f"get_url_new?url={self.query}")
        return self._create_platform_tracks(data) if data else None

    async def search(self) -> Optional[PlatformTracks]:
        """Search for tracks."""
        if not self.query:
            return None

        data = await self._fetch_data(f"search_track/{self.query}")
        return self._create_platform_tracks(data) if data else None

    async def get_track(self) -> Optional[TrackInfo]:
        """Get detailed information about a specific track."""
        if not self.query:
            return None

        data = await self._fetch_data(f"get_track?id={self.query}")
        return TrackInfo(**data) if data else None

    async def download_track(
        self, track: TrackInfo, video: bool = False
    ) -> Optional[Union[str, Path]]:
        """Download a track based on its platform.

        Returns the path to the downloaded file if successful.
        """
        if not track:
            return None

        try:
            if track.platform.lower() == "spotify":
                return await SpotifyDownload(track).process()

            download_path = Path(config.DOWNLOADS_DIR) / f"{track.tc}.mp3"
            dl = await self.client.download_file(track.cdnurl, download_path)
            return dl.file_path if dl.success else None

        except Exception as e:
            LOGGER.error(
                "Error downloading track %s: %s",
                getattr(track, "tc", "unknown"),
                str(e),
            )
            return None

    @staticmethod
    def _create_platform_tracks(data: dict) -> Optional[PlatformTracks]:
        """Create PlatformTracks object from API response data."""
        if not data or not isinstance(data, dict) or "results" not in data:
            return None

        try:
            tracks = [MusicTrack(**track) for track in data["results"]]
            return PlatformTracks(tracks=tracks)
        except (TypeError, ValueError) as e:
            LOGGER.error("Error creating PlatformTracks: %s", str(e))
            return None
