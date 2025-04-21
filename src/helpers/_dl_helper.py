#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import os
import random
import subprocess
from pathlib import Path
from typing import Optional

import aiofiles
from Crypto.Cipher import AES
from Crypto.Util import Counter

from src import config
from src.helpers._httpx import HttpxClient
from src.logger import LOGGER

from ._dataclass import TrackInfo


class YouTubeDownload:
    def __init__(self, track: TrackInfo):
        """
        Initialize the YouTubeDownload class with a video ID.
        """
        self.track = track
        self.video_id = track.tc
        self.video_url = f"https://www.youtube.com/watch?v={self.video_id}"
        self.client = HttpxClient()

    @staticmethod
    async def get_cookie_file():
        cookie_dir = "cookies"
        try:
            if not os.path.exists(cookie_dir):
                LOGGER.warning("Cookie directory '%s' does not exist.", cookie_dir)
                return None

            files = await asyncio.to_thread(os.listdir, cookie_dir)
            cookies_files = [f for f in files if f.endswith(".txt")]

            if not cookies_files:
                LOGGER.warning("No cookie files found in '%s'.", cookie_dir)
                return None

            random_file = random.choice(cookies_files)
            return os.path.join(cookie_dir, random_file)
        except Exception as e:
            LOGGER.warning("Error accessing cookie directory: %s", e)
            return None

    async def process(self, video: bool = False) -> Optional[str]:
        """
        Download the audio/video from YouTube and return the path to the downloaded
        file.
        """
        if config.API_URL and config.API_KEY and not video:
            if file_path := await self._download_with_api():
                return file_path

        return await self._download_with_yt_dlp(video)

    async def _download_with_api(self) -> Optional[str]:
        """
        Download audio using the API.
        """
        dl_url = f"{config.API_URL}/yt?id={self.video_id}"
        download_path = Path(config.DOWNLOADS_DIR) / f"{self.video_id}.webm"
        dl = await self.client.download_file(dl_url, download_path)
        return dl.file_path if dl.success else None

    async def _download_with_yt_dlp(self, video: bool) -> Optional[str]:
        output_template = f"{config.DOWNLOADS_DIR}/%(id)s.%(ext)s"
        cmd = [
            "yt-dlp",
            "--no-warnings",
            "--quiet",
            "--geo-bypass",
            "--retries",
            "2",
            "-o",
            output_template,
        ]

        if video:
            cmd.extend(["-f", "best[height<=?720][width<=?1280]"])
        else:
            cmd.extend(["-f", "bestaudio[ext=m4a]/bestaudio/best"])

        if config.PROXY_URL:
            cmd.extend(["--proxy", config.PROXY_URL])
        elif cookie_file := await self.get_cookie_file():
            cmd.extend(["--cookies", cookie_file])

        cmd.append(self.video_url)

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await proc.communicate()

            if proc.returncode != 0:
                LOGGER.error("❌ Error downloading: %s", stderr.decode().strip())
                return None
            possible_exts = ["mp4", "mkv"] if video else ["mp4", "m4a", "webm"]
            for ext in possible_exts:
                downloaded_path = f"{config.DOWNLOADS_DIR}/{self.video_id}.{ext}"
                if os.path.exists(downloaded_path):
                    LOGGER.info("✅ Downloaded: %s", downloaded_path)
                    return downloaded_path
            LOGGER.warning("⚠️ No file found for video ID: %s", self.video_id)
            return None
        except Exception as e:
            LOGGER.error("❌ Failed to download: %s", e)
            return None


async def rebuild_ogg(filename: str) -> None:
    """
    Fixes broken OGG headers.
    """
    if not os.path.exists(filename):
        LOGGER.error("❌ Error: %s not found.", filename)
        return

    try:
        async with aiofiles.open(filename, "r+b") as ogg_file:
            ogg_s = b"OggS"
            zeroes = b"\x00" * 10
            vorbis_start = b"\x01\x1e\x01vorbis"
            channels = b"\x02"
            sample_rate = b"\x44\xac\x00\x00"
            bit_rate = b"\x00\xe2\x04\x00"
            packet_sizes = b"\xb8\x01"

            await ogg_file.seek(0)
            await ogg_file.write(ogg_s)
            await ogg_file.seek(6)
            await ogg_file.write(zeroes)
            await ogg_file.seek(26)
            await ogg_file.write(vorbis_start)
            await ogg_file.seek(39)
            await ogg_file.write(channels)
            await ogg_file.seek(40)
            await ogg_file.write(sample_rate)
            await ogg_file.seek(48)
            await ogg_file.write(bit_rate)
            await ogg_file.seek(56)
            await ogg_file.write(packet_sizes)
            await ogg_file.seek(58)
            await ogg_file.write(ogg_s)
            await ogg_file.seek(62)
            await ogg_file.write(zeroes)
    except Exception as e:
        LOGGER.error("Error rebuilding OGG file %s: %s", filename, e)


class SpotifyDownload:
    def __init__(self, track: TrackInfo):
        self.track = track
        self.client = HttpxClient()
        self.encrypted_file = os.path.join(
            config.DOWNLOADS_DIR, f"{track.tc}.encrypted.ogg"
        )
        self.decrypted_file = os.path.join(
            config.DOWNLOADS_DIR, f"{track.tc}.decrypted.ogg"
        )
        self.output_file = os.path.join(config.DOWNLOADS_DIR, f"{track.tc}.ogg")

    async def decrypt_audio(self) -> None:
        """
        Decrypt the downloaded audio file using a stream-based approach.
        """
        try:
            key = bytes.fromhex(self.track.key)
            iv = bytes.fromhex("72e067fbddcbcf77ebe8bc643f630d93")
            iv_int = int.from_bytes(iv, "big")
            cipher = AES.new(
                key, AES.MODE_CTR, counter=Counter.new(128, initial_value=iv_int)
            )

            chunk_size = 8192  # 8KB chunks
            async with (
                aiofiles.open(self.encrypted_file, "rb") as fin,
                aiofiles.open(self.decrypted_file, "wb") as fout,
            ):
                while chunk := await fin.read(chunk_size):
                    decrypted_chunk = cipher.decrypt(chunk)
                    await fout.write(decrypted_chunk)
        except Exception as e:
            LOGGER.error("Error decrypting audio file: %s", e)
            raise

    async def fix_audio(self) -> None:
        """
        Fix the decrypted audio file using FFmpeg.
        """
        try:
            process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-i",
                self.decrypted_file,
                "-c",
                "copy",
                self.output_file,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _, stderr = await process.communicate()
            if process.returncode != 0:
                LOGGER.error("FFmpeg error: %s", stderr.decode().strip())
                raise subprocess.CalledProcessError(process.returncode, "ffmpeg")
        except Exception as e:
            LOGGER.error("Error fixing audio file: %s", e)
            raise

    async def _cleanup(self) -> None:
        """
        Cleanup temporary files asynchronously.
        """
        for file in [self.encrypted_file, self.decrypted_file]:
            try:
                if os.path.exists(file):
                    os.remove(file)
            except Exception as e:
                LOGGER.warning("Error removing %s: %s", file, e)

    async def process(self) -> Optional[str]:
        """
        Main function to download, decrypt, and fix audio.
        """
        if os.path.exists(self.output_file):
            LOGGER.info("✅ Found existing file: %s", self.output_file)
            return self.output_file

        _track_id = self.track.tc
        if not self.track.cdnurl or not self.track.key:
            LOGGER.warning("Missing CDN URL or key for track: %s", _track_id)
            return None

        try:
            await self.client.download_file(self.track.cdnurl, self.encrypted_file)
            await self.decrypt_audio()
            await rebuild_ogg(self.decrypted_file)
            await self.fix_audio()
            await self._cleanup()
            LOGGER.info("✅ Successfully processed track: %s", self.output_file)
            return self.output_file
        except Exception as e:
            LOGGER.error("Error processing track %s: %s", _track_id, e)
            await self._cleanup()
            return None
