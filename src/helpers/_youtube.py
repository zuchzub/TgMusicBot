#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import re
from typing import Any, Optional

from py_yt import Playlist, VideosSearch, Video

from src.helpers import MusicTrack, PlatformTracks, TrackInfo
from src.logger import LOGGER
from ._dl_helper import YouTubeDownload
from ._downloader import MusicService
from ._httpx import HttpxClient
from ..config import PROXY_URL


class YouTubeData(MusicService):
    """A class to handle YouTube music data fetching and processing."""

    YOUTUBE_VIDEO_PATTERN = re.compile(
        r"^(?:https?://)?(?:www\.)?(?:youtube\.com|music\.youtube\.com|youtu\.be)/"
        r"(?:watch\?v=|embed/|v/|shorts/)?([\w-]{11})(?:\?|&|$)",
        re.IGNORECASE,
    )
    YOUTUBE_PLAYLIST_PATTERN = re.compile(
        r"^(?:https?://)?(?:www\.)?(?:youtube\.com|music\.youtube\.com)/"
        r"(?:playlist|watch)\?.*\blist=([\w-]+)",
        re.IGNORECASE,
    )
    YOUTUBE_SHORTS_PATTERN = re.compile(
        r"^(?:https?://)?(?:www\.)?youtube\.com/shorts/([\w-]+)",
        re.IGNORECASE,
    )

    def __init__(self, query: Optional[str] = None) -> None:
        """
        Initialize YouTubeData with an optional query.

        Args:
            query: The search query or YouTube URL to process
        """
        self.client = HttpxClient()
        self.query = self._clean_query(query) if query else None

    @staticmethod
    def _clean_query(query: str) -> str:
        """Clean the query by removing unnecessary parameters."""
        return query.split("&")[0].split("#")[0].strip()

    def is_valid(self, url: Optional[str]) -> bool:
        """
        Check if the URL is a valid YouTube URL.

        Args:
            url: The URL to validate

        Returns:
            bool: True if valid YouTube URL, False otherwise
        """
        if not url:
            return False
        return any(
            pattern.match(url)
            for pattern in (
                self.YOUTUBE_VIDEO_PATTERN,
                self.YOUTUBE_PLAYLIST_PATTERN,
                self.YOUTUBE_SHORTS_PATTERN,
            )
        )

    async def get_info(self) -> Optional[PlatformTracks]:
        """Get track information from YouTube URL."""
        if not self.query or not self.is_valid(self.query):
            return None

        try:
            data = await self._fetch_data(self.query)
            return self._create_platform_tracks(data) if data else None
        except Exception as e:
            LOGGER.error(f"Error getting info for {self.query}: {str(e)}")
            return None

    async def search(self) -> Optional[PlatformTracks]:
        """Search for tracks on YouTube."""
        if not self.query:
            return None

        if self.is_valid(self.query):
            return await self.get_info()

        try:
            search = VideosSearch(self.query, limit=5)
            results = await search.next()
            if not results or "result" not in results:
                return None

            tracks = [self._format_track(video) for video in results["result"]]
            return PlatformTracks(tracks=[MusicTrack(**track) for track in tracks])
        except Exception as e:
            LOGGER.error(f"Error searching for '{self.query}': {str(e)}")
            return None

    async def get_track(self) -> Optional[TrackInfo]:
        """Get detailed track information."""
        if not self.query:
            return None

        try:
            if not self.query.startswith(("http://", "https://")):
                url = f"https://youtube.com/watch?v={self.query}"
            else:
                url = self.query

            data = await self._fetch_data(url)
            if not data or not data.get("results"):
                return None

            return await self._create_track_info(data["results"][0])
        except Exception as e:
            LOGGER.error(f"Error fetching track {self.query}: {str(e)}")
            return None

    async def download_track(
        self, track: TrackInfo, video: bool = False
    ) -> Optional[str]:
        """
        Download a YouTube track.

        Args:
            track: TrackInfo object containing track details
            video: Whether to download video (True) or audio only (False)

        Returns:
            str: Path to downloaded file or None if failed
        """
        if not track:
            return None

        try:
            return await YouTubeDownload(track).process(video)
        except Exception as e:
            LOGGER.error(f"Error downloading track {track.name}: {str(e)}")
            return None

    async def _fetch_data(self, url: str) -> Optional[dict[str, Any]]:
        """
        Fetch data based on URL type (video or playlist).

        Args:
            url: YouTube URL to fetch data from

        Returns:
            dict: Contains track data or None if failed
        """
        try:
            if self.YOUTUBE_PLAYLIST_PATTERN.match(url):
                LOGGER.debug(f"Fetching playlist data: {url}")
                return await self._get_playlist_data(url)

            LOGGER.debug(f"Fetching video data: {url}")
            return await self._get_video_data(url)
        except Exception as e:
            LOGGER.error(f"Error fetching data from {url}: {str(e)}")
            return None

    async def _get_video_data(self, url: str) -> Optional[dict[str, Any]]:
        """Get YouTube video data from the URL."""
        normalized_url = await self._normalize_youtube_url(url)
        if not normalized_url:
            return None

        if PROXY_URL:
            try:
                video_id = self._extract_video_id(normalized_url)
                if not video_id:
                    return None

                result = await Video.get(video_id)
                if not result:
                    return None

                track = self._format_track(
                    {
                        "id": result["id"],
                        "title": result["title"],
                        "duration": result.get("duration", {}).get(
                            "secondsText", "0:00"
                        ),
                        "channel": result.get("channel", {}),
                        "thumbnails": result.get("thumbnails", [{}]),
                    }
                )
                return {"results": [track]}
            except Exception as e:
                LOGGER.warning(f"Proxy fetch failed, falling back: {str(e)}")

        try:
            search = VideosSearch(normalized_url, limit=1)
            results = await search.next()
            if not results or "result" not in results or not results["result"]:
                return None

            return {"results": [self._format_track(results["result"][0])]}
        except Exception as e:
            LOGGER.error(f"Error searching video: {str(e)}")
            return None

    async def get_recommendations(self) -> Optional[PlatformTracks]:
        """Get recommended tracks (not implemented)."""
        return None

    async def _get_playlist_data(self, url: str) -> Optional[dict[str, Any]]:
        """Get YouTube playlist data."""
        try:
            playlist = await Playlist.getVideos(url)
            if not playlist or not playlist.get("videos"):
                return None

            return {
                "results": [
                    self._format_track(track)
                    for track in playlist["videos"]
                    if track.get("id")  # Only include valid tracks
                ]
            }
        except Exception as e:
            LOGGER.error(f"Error getting playlist: {str(e)}")
            return None

    @staticmethod
    def _extract_video_id(url: str) -> Optional[str]:
        """Extract video ID from various YouTube URL formats."""
        for pattern in (
            YouTubeData.YOUTUBE_VIDEO_PATTERN,
            YouTubeData.YOUTUBE_SHORTS_PATTERN,
        ):
            if match := pattern.match(url):
                return match.group(1)
        return None

    @staticmethod
    async def _normalize_youtube_url(url: str) -> Optional[str]:
        """Normalize different YouTube URL formats to standard watch URL."""
        if not url:
            return None

        # Handle youtu.be short links
        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].partition("?")[0].partition("#")[0]
            return f"https://www.youtube.com/watch?v={video_id}"

        # Handle YouTube shorts
        if "youtube.com/shorts/" in url:
            video_id = url.split("youtube.com/shorts/")[1].split("?")[0]
            return f"https://www.youtube.com/watch?v={video_id}"

        return url

    @staticmethod
    def _create_platform_tracks(data: dict[str, Any]) -> PlatformTracks:
        """Create PlatformTracks object from data."""
        if not data or "results" not in data:
            return PlatformTracks(tracks=[])

        valid_tracks = [
            MusicTrack(**track)
            for track in data["results"]
            if track and track.get("id")
        ]
        return PlatformTracks(tracks=valid_tracks)

    @staticmethod
    def _format_track(track_data: dict[str, Any]) -> dict[str, Any]:
        """Format track data into a consistent structure."""
        duration = track_data.get("duration", "0:00")
        if isinstance(duration, dict):
            duration = duration.get("secondsText", "0:00")

        return {
            "id": track_data.get("id", ""),
            "name": track_data.get("title", "Unknown Title"),
            "duration": YouTubeData._duration_to_seconds(duration),
            "artist": track_data.get("channel", {}).get("name", "Unknown Artist"),
            "cover": next(
                (
                    thumb["url"]
                    for thumb in reversed(track_data.get("thumbnails", []))
                    if thumb.get("url")
                ),
                "",
            ),
            "year": 0,
            "url": f"https://www.youtube.com/watch?v={track_data.get('id', '')}",
            "platform": "youtube",
        }

    @staticmethod
    async def _create_track_info(track_data: dict[str, Any]) -> TrackInfo:
        """Create TrackInfo from formatted track data."""
        return TrackInfo(
            cdnurl="None",
            key="None",
            name=track_data.get("name", "Unknown Title"),
            artist=track_data.get("artist", "Unknown Artist"),
            tc=track_data.get("id", ""),
            album="YouTube",
            cover=track_data.get("cover", ""),
            lyrics="None",
            duration=track_data.get("duration", 0),
            platform="youtube",
            url=f"https://youtube.com/watch?v={track_data.get('id', '')}",
            year=0,
        )

    @staticmethod
    def _duration_to_seconds(duration: str) -> int:
        """
        Convert duration string (HH:MM:SS or MM:SS) to seconds.

        Args:
            duration: Time string to convert

        Returns:
            int: Duration in seconds
        """
        if not duration:
            return 0

        try:
            parts = list(map(int, duration.split(":")))
            if len(parts) == 3:  # HH:MM:SS
                return parts[0] * 3600 + parts[1] * 60 + parts[2]
            elif len(parts) == 2:  # MM:SS
                return parts[0] * 60 + parts[1]
            elif len(parts) == 1:  # SS
                return parts[0]
            return 0
        except (ValueError, AttributeError):
            return 0
