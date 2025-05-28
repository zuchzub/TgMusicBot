# Copyright (c) 2025 AshokShau
# Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
# Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
import re
import time
import uuid
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import unquote

import aiofiles
import aiohttp
from aiohttp import ClientSession, TCPConnector

from src.config import DOWNLOADS_DIR, API_KEY, API_URL
from src.logger import LOGGER


class DownloadResult:
    def __init__(
        self,
        success: bool,
        file_path: Optional[Path] = None,
        error: Optional[str] = None,
        status_code: Optional[int] = None,
    ):
        self.success = success
        self.file_path = file_path
        self.error = error
        self.status_code = status_code


class AioHttpClient:
    _instance = None
    _session = None
    _connector = None

    DEFAULT_TIMEOUT = 30
    DEFAULT_DOWNLOAD_TIMEOUT = 100
    CHUNK_SIZE = 8192
    MAX_RETRIES = 2
    BACKOFF_FACTOR = 1.0
    CONNECTION_LIMIT = 100
    CONNECTION_LIMIT_PER_HOST = 20

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AioHttpClient, cls).__new__(cls)
            cls._connector = TCPConnector(
                limit=cls.CONNECTION_LIMIT,
                limit_per_host=cls.CONNECTION_LIMIT_PER_HOST,
                force_close=False,
                enable_cleanup_closed=True,
                keepalive_timeout=60,
            )
        return cls._instance

    async def initialize(self):
        if self._session is None or self._session.closed:
            self._session = ClientSession(
                connector=self._connector,
                timeout=aiohttp.ClientTimeout(
                    total=self.DEFAULT_TIMEOUT,
                    connect=self.DEFAULT_TIMEOUT,
                    sock_connect=self.DEFAULT_TIMEOUT,
                    sock_read=self.DEFAULT_TIMEOUT,
                ),
                trust_env=True,
            )

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
        if self._connector and not self._connector.closed:
            await self._connector.close()
        self._instance = None
        self._session = None
        self._connector = None

    @staticmethod
    def _get_headers(url: str, base_headers: dict[str, str]) -> dict[str, str]:
        headers = base_headers.copy()
        if API_URL and url.startswith(API_URL):
            if not API_KEY:
                raise ValueError("API Key is required but not configured")
            headers["X-API-Key"] = API_KEY
        return headers

    async def download_file(
        self,
        url: str,
        file_path: Optional[Union[str, Path]] = None,
        overwrite: bool = False,
        max_redirects=0,
        **kwargs: Any,
    ) -> DownloadResult:
        await self.initialize()

        if not url:
            return DownloadResult(
                success=False, error="Empty URL provided", status_code=400
            )

        try:
            headers = self._get_headers(url, kwargs.pop("headers", {}))
        except ValueError as e:
            return DownloadResult(success=False, error=str(e), status_code=401)

        try:
            async with self._session.get(
                url, headers=headers, timeout=self.DEFAULT_DOWNLOAD_TIMEOUT, **kwargs
            ) as response:
                if response.status != 200:
                    error_msg = await self._get_error_message(response, url)
                    LOGGER.error(error_msg)
                    return DownloadResult(
                        success=False, error=error_msg, status_code=response.status
                    )

                if file_path is None:
                    cd = response.headers.get("Content-Disposition", "")
                    match = re.search(r'filename="?([^"]+)"?', cd)
                    filename = (
                        unquote(match[1])
                        if match
                        else (Path(url).name or uuid.uuid4().hex)
                    )
                    path = Path(DOWNLOADS_DIR) / filename
                else:
                    path = Path(file_path) if isinstance(file_path, str) else file_path

                if path.exists() and not overwrite:
                    return DownloadResult(success=True, file_path=path)

                path.parent.mkdir(parents=True, exist_ok=True)
                async with aiofiles.open(path, "wb") as f:
                    async for chunk in response.content.iter_chunked(self.CHUNK_SIZE):
                        await f.write(chunk)

                LOGGER.debug("Successfully downloaded file to %s", path)
                return DownloadResult(success=True, file_path=path)

        except Exception as e:
            error_msg = f"Failed to download {url}: {str(e)}"
            LOGGER.error(error_msg)
            return DownloadResult(success=False, error=error_msg, status_code=500)

    @staticmethod
    async def _get_error_message(response: aiohttp.ClientResponse, url: str) -> str:
        try:
            error_data = await response.json()
            if isinstance(error_data, dict):
                if "error" in error_data:
                    return error_data["error"]
                if "message" in error_data:
                    return error_data["message"]
        except Exception:
            pass

        status_messages = {
            400: "Bad request",
            401: "Unauthorized - Missing or invalid API key",
            403: "Forbidden - API key expired or insufficient permissions",
            404: "Resource not found",
            429: "Too many requests - Rate limit exceeded",
            500: "Internal server error",
            502: "Bad gateway",
            503: "Service unavailable",
            504: "Gateway timeout",
        }

        return status_messages.get(
            response.status,
            f"Request failed ({url}) with status code {response.status}",
        )

    async def make_request(
        self,
        url: str,
        max_retries: int = MAX_RETRIES,
        backoff_factor: float = BACKOFF_FACTOR,
        **kwargs: Any,
    ) -> Optional[dict[str, Any]]:
        await self.initialize()

        if not url:
            LOGGER.warning("Empty URL provided")
            return {"error": "Empty URL provided", "status": 400}

        try:
            headers = self._get_headers(url, kwargs.pop("headers", {}))
        except ValueError as e:
            LOGGER.error("API key error: %s", str(e))
            return {"error": str(e), "status": 401}

        for attempt in range(max_retries):
            try:
                start = time.monotonic()
                async with self._session.get(
                    url, headers=headers, **kwargs
                ) as response:
                    if response.status != 200:
                        error_msg = await self._get_error_message(response, url)
                        LOGGER.warning(
                            "HTTP %d for %s: %s", response.status, url, error_msg
                        )
                        if response.status in (401, 403, 404):
                            return {"error": error_msg, "status": response.status}
                        continue

                    duration = time.monotonic() - start
                    LOGGER.debug("Request to %s succeeded in %.2fs", url, duration)
                    return await response.json()

            except aiohttp.ClientError as e:
                LOGGER.warning("Request failed for %s: %s", url, str(e))
                error_msg = f"Network error: {str(e)}"
            except asyncio.TimeoutError:
                LOGGER.warning("Timeout while requesting %s", url)
                error_msg = "Request timed out"
            except Exception as e:
                LOGGER.error("Unexpected error for %s: %s", url, str(e))
                error_msg = f"Internal error: {str(e)}"
                return {"error": error_msg, "status": 500}

            await asyncio.sleep(backoff_factor * (2**attempt))

        LOGGER.error("All retries failed for URL: %s", url)
        return {"error": error_msg, "status": 503}

    async def __aenter__(self):
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    @classmethod
    async def shutdown(cls):
        if cls._instance:
            await cls._instance.close()


# _client = AioHttpClient()
