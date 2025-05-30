#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import re
from pathlib import Path
from typing import Any, Optional

import yt_dlp

from src import config
from src.logger import LOGGER
from ._dataclass import MusicTrack, PlatformTracks, TrackInfo
from ._downloader import MusicService
from ._httpx import DownloadResult, HttpxClient


class JiosaavnData(MusicService):
    """
    JioSaavn music service handler for searching, parsing and downloading tracks.
    """

    # URL patterns
    JIOSAAVN_SONG_PATTERN = re.compile(
        r"^(https?://)?(www\.)?jiosaavn\.com/song/[\w-]+/[a-zA-Z0-9_-]+", re.IGNORECASE
    )
    JIOSAAVN_PLAYLIST_PATTERN = re.compile(
        r"^(https?://)?(www\.)?jiosaavn\.com/featured/[\w-]+/[a-zA-Z0-9_-]+$",
        re.IGNORECASE,
    )

    # API endpoints
    API_SEARCH_ENDPOINT = (
        "https://www.jiosaavn.com/api.php?"
        "__call=autocomplete.get&"
        "query={query}&"
        "_format=json&"
        "_marker=0&"
        "ctx=wap6dot0"
    )

    # Constants
    DEFAULT_ARTIST = "Unknown Artist"
    DEFAULT_ALBUM = "Unknown Album"
    DEFAULT_DURATION = 0
    DEFAULT_YEAR = 0

    def __init__(self, query: Optional[str] = None) -> None:
        """
        Initialize JioSaavn service handler.

        Args:
            query: Search query or URL to process
        """
        self.query = query
        self._ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": "in_playlist",
            "socket_timeout": 10,
            # "noplaylist": False,
        }

    def is_valid(self, url: str) -> bool:
        """
        Check if the URL is a valid JioSaavn song or playlist URL.

        Args:
            url: URL to validate

        Returns:
            bool: True if valid JioSaavn URL, False otherwise
        """
        if not url:
            return False
        return bool(
            self.JIOSAAVN_SONG_PATTERN.match(url)
            or self.JIOSAAVN_PLAYLIST_PATTERN.match(url)
        )

    async def _fetch_data(self, url: str) -> Optional[dict[str, Any]]:
        """
        Fetch data based on URL type (song or playlist).

        Args:
            url: JioSaavn URL to fetch data from

        Returns:
            Optional[Dict]: Parsed track/playlist data or None if failed
        """
        try:
            if self.JIOSAAVN_SONG_PATTERN.match(url):
                return await self.get_track_data(url)
            return await self.get_playlist_data(url)
        except yt_dlp.DownloadError as e:
            LOGGER.error("YT-DLP error fetching %s: %s", url, str(e))
        except Exception as e:
            LOGGER.error("Unexpected error fetching %s: %s", url, str(e))
        return None

    async def search(self) -> Optional[PlatformTracks]:
        """
        Search for tracks. Falls back to JioSaavn API if not a direct URL.

        Returns:
            Optional[PlatformTracks]: Search results or None if failed
        """
        if not self.query:
            return None

        if self.is_valid(self.query):
            return await self.get_info()

        try:
            url = self.API_SEARCH_ENDPOINT.format(query=self.query)
            response = await HttpxClient().make_request(url)
            data = self._parse_search_response(response)
        except Exception as e:
            LOGGER.error("Search failed for '%s': %s", self.query, str(e))
            data = None

        return self._create_platform_tracks(data) if data else None

    async def get_recommendations(self) -> Optional[PlatformTracks]:
        """
        Placeholder for recommendations functionality.
        """
        # TODO: Implement recommendations using JioSaavn API
        return None

    async def get_info(self) -> Optional[PlatformTracks]:
        """
        Get track or playlist info.

        Returns:
            Optional[PlatformTracks]: Track/playlist info or None if failed
        """
        if not self.query or not self.is_valid(self.query):
            return None

        data = await self._fetch_data(self.query)
        return self._create_platform_tracks(data) if data else None

    async def get_track(self) -> Optional[TrackInfo]:
        """
        Get detailed track information.

        Returns:
            Optional[TrackInfo]: Track information or None if failed
        """
        if not self.query:
            return None

        url = (
            self.query
            if self.is_valid(self.query)
            else self.format_jiosaavn_url(self.query)
        )
        data = await self.get_track_data(url)
        if not data or not data.get("results"):
            return None

        return self._create_track_info(data["results"][0])

    async def get_track_data(self, url: str) -> Optional[dict[str, Any]]:
        """
        Get track data using yt-dlp.

        Args:
            url: Track URL to fetch

        Returns:
            Optional[Dict]: Track data or None if failed
        """
        try:
            with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)
                return {"results": [self._format_track(info)]} if info else None
        except yt_dlp.DownloadError as e:
            LOGGER.error("YT-DLP error getting track %s: %s", url, str(e))
        except Exception as e:
            LOGGER.error("Unexpected error getting track %s: %s", url, str(e))
        return None

    async def get_playlist_data(self, url: str) -> Optional[dict[str, Any]]:
        """
        Get playlist data using yt-dlp.

        Args:
            url: Playlist URL to fetch

        Returns:
            Optional[Dict]: Playlist data or None if failed
        """
        try:
            with yt_dlp.YoutubeDL(self._ydl_opts) as ydl:
                info = await asyncio.to_thread(ydl.extract_info, url, download=False)

                if not info or not info.get("entries"):
                    LOGGER.warning("No entries found in playlist: %s", url)
                    return None

                return {
                    "results": [
                        self._format_track(track) for track in info["entries"] if track
                    ]
                }
        except yt_dlp.DownloadError as e:
            LOGGER.error("YT-DLP error getting playlist %s: %s", url, str(e))
        except Exception as e:
            LOGGER.error("Unexpected error getting playlist %s: %s", url, str(e))
        return None

    async def download_track(
        self, track: TrackInfo, video: bool = False
    ) -> Optional[Path]:
        if not track or not track.cdnurl:
            return None

        download_path = config.DOWNLOADS_DIR / f"{track.tc}.m4a"
        dl: DownloadResult = await HttpxClient(max_redirects=1).download_file(
            track.cdnurl, download_path
        )
        return dl.file_path if dl.success else None

    @staticmethod
    def format_jiosaavn_url(name_and_id: str) -> str:
        """
        Format a JioSaavn URL from name and ID.

        Args:
            name_and_id: String in format "song_name/song_id"

        Returns:
            str: Formatted JioSaavn URL or empty string if invalid
        """
        if not name_and_id:
            return ""

        try:
            title, song_id = name_and_id.rsplit("/", 1)
            title = re.sub(r'[\(\)"\',]', "", title.lower())
            title = re.sub(r"\s+", "-", title.strip())
            return f"https://www.jiosaavn.com/song/{title}/{song_id}"
        except ValueError:
            LOGGER.warning("Invalid name_and_id format: %s", name_and_id)
            return ""

    @classmethod
    def _format_track(cls, track_data: dict[str, Any]) -> dict[str, Any]:
        """
        Format track data into a standardized format.

        Args:
            track_data: Raw track data from API

        Returns:
            Dict: Formatted track data
        """
        if not track_data:
            return {}

        # Get best available audio format
        formats = track_data.get("formats", [])
        best_format = max(formats, key=lambda x: x.get("abr", 0), default={})

        # Extract artist information
        artists = track_data.get("artists", [])
        artist = track_data.get("artist", artists[0] if artists else cls.DEFAULT_ARTIST)

        # Generate display ID
        title = track_data.get("title", "")
        display_id = f"{title}/{track_data.get('url', '').split('/')[-1]}"

        return {
            "id": track_data.get("display_id", display_id),
            "tc": track_data.get("display_id", display_id),
            "name": title,
            "album": track_data.get("album", cls.DEFAULT_ALBUM),
            "duration": track_data.get("duration", cls.DEFAULT_DURATION),
            "artist": artist,
            "cover": track_data.get("thumbnail", ""),
            "year": track_data.get("release_year", cls.DEFAULT_YEAR),
            "platform": "jiosaavn",
            "url": track_data.get("webpage_url", ""),
            "cdnurl": best_format.get("url", ""),
        }

    @classmethod
    def _create_track_info(cls, track_data: dict[str, Any]) -> TrackInfo:
        """
        Create TrackInfo object from raw track data.

        Args:
            track_data: Formatted track data

        Returns:
            TrackInfo: Track information object
        """
        return TrackInfo(
            cdnurl=track_data.get("cdnurl", ""),
            key="nil",
            name=track_data.get("name", ""),
            artist=track_data.get("artist", cls.DEFAULT_ARTIST),
            tc=track_data.get("id", ""),
            album=track_data.get("album", cls.DEFAULT_ALBUM),
            cover=track_data.get("cover", ""),
            lyrics="None",
            duration=track_data.get("duration", cls.DEFAULT_DURATION),
            year=track_data.get("year", cls.DEFAULT_YEAR),
            url=track_data.get("url", ""),
            platform="jiosaavn",
        )

    @staticmethod
    def _create_platform_tracks(data: dict[str, Any]) -> Optional[PlatformTracks]:
        """
        Create PlatformTracks object from formatted data.

        Args:
            data: Formatted tracks data

        Returns:
            Optional[PlatformTracks]: Platform tracks object or None if invalid
        """
        if not data or not data.get("results"):
            return None

        return PlatformTracks(
            tracks=[MusicTrack(**track) for track in data["results"] if track]
        )

    def _parse_search_response(
        self, response: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """
        Parse the search API response into standardized format.

        Args:
            response: Raw API response

        Returns:
            Optional[Dict]: Formatted track data or None if invalid
        """
        if not response or not response.get("songs", {}).get("data"):
            return None

        return {
            "results": [
                self._format_track(track)
                for track in response["songs"]["data"]
                if track
            ]
        }
