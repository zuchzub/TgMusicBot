#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from pytdbot import Client, types
from TgMusic.logger import LOGGER
from TgMusic.core import config
from TgMusic.modules.utils import sec_to_min
from TgMusic.modules.utils._dataclass import CachedTrack


async def send_song_log(client: Client, chat_id: int, song: CachedTrack):
    """
    Görev:
        Şu anda çalınan şarkıyı log kanalına şık ve bağlantısız biçimde bildirmek.
    Parametreler:
        client (Client): Mesajı gönderecek bot istemcisi.
        chat_id (int): Şarkının çalındığı sohbetin kimliği.
        song (CachedTrack): Çalınan şarkı nesnesi.
    Dönüş:
        None
    """
    if not chat_id or not song or chat_id == config.LOGGER_ID or config.LOGGER_ID == 0:
        return

    # 🌌 Fancy Türkçe Log Mesajı (bağlantısız)
    text = (
        "🎧 <b>ᴍᴜ̈ᴢɪᴋ ʙɪʟᴅɪʀɪᴍɪ</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        f"🎵 <b>Şarkı:</b> <code>{song.name}</code>\n"
        f"🕒 <b>Süre:</b> {sec_to_min(song.duration)}\n"
        f"👤 <b>İsteyen:</b> {song.user}\n"
        f"💿 <b>Platform:</b> {song.platform}\n"
        f"💬 <b>Sohbet ID:</b> <code>{chat_id}</code>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "☁️ ᴍᴀᴠɪ ᴅᴜʏᴜʀᴜ • ʟᴏɢ sɪsᴛᴇᴍɪ ᴀᴋᴛɪꜰ"
    )

    msg = await client.sendTextMessage(
        config.LOGGER_ID,
        text,
        disable_web_page_preview=True,
        disable_notification=True,
    )

    if isinstance(msg, types.Error):
        LOGGER.error(f"⚠️ Log gönderim hatası: {msg.message}")
    return