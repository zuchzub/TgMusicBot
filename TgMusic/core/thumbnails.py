#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import asyncio
from aiofiles.os import path as aiopath
from ._dataclass import CachedTrack
from TgMusic.logger import LOGGER


async def gen_thumb(song: CachedTrack) -> str:
    """
    Kapak fotoğrafı oluşturmayı devre dışı bırakır.
    Bu sürüm herhangi bir görsel üretmez ve boş sonuç döndürür.
    """
    try:
        save_dir = f"database/photos/{song.track_id}.png"
        if await aiopath.exists(save_dir):
            return ""  # Artık kullanılmıyor
        # Kapak işlemleri kaldırıldı
        LOGGER.info(f"Kapak fotoğrafı oluşturma atlandı: {song.name}")
        return ""
    except Exception as e:
        LOGGER.error(f"Kapak oluşturma hatası: {e}")
        return ""