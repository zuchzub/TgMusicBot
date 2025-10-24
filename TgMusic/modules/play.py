# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında lisanslanmıştır: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Uygulanabilir yerlerde tüm hakları saklıdır.

import re
from pytdbot import Client, types
from pytdbot import filters

from TgMusic.core import YouTubeData, DownloaderWrapper, db, call, tg
from TgMusic.core import (
    CachedTrack,
    MusicTrack,
    PlatformTracks,
    chat_cache,
    Filter,
    SupportButton,
    control_buttons,
)
from TgMusic.logger import LOGGER
from TgMusic.core.admins import is_admin, load_admin_cache
from TgMusic.modules.utils import sec_to_min, get_audio_duration
from TgMusic.modules.utils.play_helpers import (
    del_msg,
    edit_text,
    extract_argument,
    get_url,
)
from TgMusic.core.thumbnails import gen_thumb


# ─────────────────────────────────────────────
# 🔗 Yardımcı Fonksiyonlar
# ─────────────────────────────────────────────

def _get_jiosaavn_url(track_id: str) -> str:
    """JioSaavn şarkı kimliğinden URL üretir."""
    try:
        title, song_id = track_id.rsplit("/", 1)
    except ValueError:
        return ""
    title = re.sub(r'[\(\)"\',]', "", title.lower()).replace(" ", "-")
    return f"https://www.jiosaavn.com/song/{title}/{song_id}"


def _get_platform_url(platform: str, track_id: str) -> str:
    """Platforma göre şarkı bağlantısı oluşturur."""
    platform = platform.lower()
    if not track_id:
        return ""

    urls = {
        "youtube": f"https://youtube.com/watch?v={track_id}",
        "spotify": f"https://open.spotify.com/track/{track_id}",
        "jiosaavn": _get_jiosaavn_url(track_id),
    }
    return urls.get(platform, "")


def build_song_selection_message(user_by: str, tracks: list[MusicTrack]):
    """Kullanıcıya şarkı seçme menüsü oluşturur."""
    text = f"{user_by}, bir şarkı seç 👇" if user_by else "Bir şarkı seç 👇"
    buttons = [
        [
            types.InlineKeyboardButton(
                text=f"{track.name[:18]} - {track.artist}",
                type=types.InlineKeyboardButtonTypeCallback(
                    f"play_{track.platform.lower()}_{track.id}".encode()
                ),
            )
        ]
        for track in tracks[:4]
    ]
    return text, types.ReplyMarkupInlineKeyboard(buttons)


async def _update_msg_with_thumb(c: Client, msg: types.Message, text: str, thumb: str, buttons):
    """Mesajı kapak görseliyle günceller (varsa)."""
    if not thumb:
        return await edit_text(msg, text=text, reply_markup=buttons, disable_web_page_preview=True)

    parsed = await c.parseTextEntities(text, types.TextParseModeHTML())
    if isinstance(parsed, types.Error):
        return await edit_text(msg, text=parsed.message, reply_markup=buttons)

    input_content = types.InputMessagePhoto(types.InputFileLocal(thumb), caption=parsed)
    return await c.editMessageMedia(
        chat_id=msg.chat_id,
        message_id=msg.id,
        input_message_content=input_content,
        reply_markup=buttons,
    )


# ─────────────────────────────────────────────
# 🎧 Oynatma İşlevleri
# ─────────────────────────────────────────────

async def _handle_single_track(c: Client, msg: types.Message, track: MusicTrack, user_by: str, file_path=None, is_video=False):
    """Tek bir şarkıyı oynatır veya kuyruğa ekler."""
    chat_id = msg.chat_id
    song = CachedTrack(
        name=track.name,
        track_id=track.id,
        loop=0,
        duration=track.duration,
        file_path=file_path or "",
        thumbnail=track.cover,
        user=user_by,
        platform=track.platform,
        is_video=is_video,
        url=track.url,
    )

    if not song.file_path:
        download = await call.song_download(song)
        if isinstance(download, types.Error):
            return await edit_text(msg, f"❌ Şarkı indirilemedi: {download.message}")
        song.file_path = download or ""
        if not song.file_path:
            return await edit_text(msg, "❌ Şarkı indirilemedi.")

    song.duration = song.duration or await get_audio_duration(song.file_path)

    # Aktif çalma varsa kuyruğa ekle
    if chat_cache.is_active(chat_id):
        queue = chat_cache.get_queue(chat_id)
        chat_cache.add_song(chat_id, song)
        queue_info = (
            f"<b>🎧 Kuyruğa eklendi (#{len(queue)})</b>\n\n"
            f"🎵 <b>Şarkı:</b> <a href='{song.url}'>{song.name}</a>\n"
            f"⏱ <b>Süre:</b> {sec_to_min(song.duration)}\n"
            f"👤 <b>Ekleyen:</b> {song.user}"
        )
        thumb = await gen_thumb(song) if await db.get_thumbnail_status(chat_id) else ""
        return await _update_msg_with_thumb(
            c, msg, queue_info, thumb,
            control_buttons("play") if await db.get_buttons_status(chat_id) else None
        )

    # Yeni oturum başlat
    chat_cache.set_active(chat_id, True)
    chat_cache.add_song(chat_id, song)

    play = await call.play_media(chat_id, song.file_path, video=is_video)
    if isinstance(play, types.Error):
        return await edit_text(msg, text=f"⚠️ Oynatma hatası: {play.message}")

    now_playing = (
        f"🎵 <b>Şu anda çalıyor:</b>\n\n"
        f"🎶 <a href='{song.url}'>{song.name}</a>\n"
        f"⏱ Süre: {sec_to_min(song.duration)}\n"
        f"👤 İsteyen: {song.user}"
    )
    thumb = await gen_thumb(song) if await db.get_thumbnail_status(chat_id) else ""
    result = await _update_msg_with_thumb(
        c, msg, now_playing, thumb,
        control_buttons("play") if await db.get_buttons_status(chat_id) else None
    )
    if isinstance(result, types.Error):
        LOGGER.warning("Mesaj güncellenemedi: %s", result)
    return None


async def _handle_multiple_tracks(msg: types.Message, tracks: list[MusicTrack], user_by: str):
    """Birden fazla şarkıyı (playlist) kuyruğa ekler."""
    chat_id = msg.chat_id
    is_active = chat_cache.is_active(chat_id)
    queue = chat_cache.get_queue(chat_id)

    header = "<b>📥 Kuyruğa Eklenen Şarkılar:</b>\n<blockquote expandable>\n"
    items = []

    for i, track in enumerate(tracks):
        pos = len(queue) + i
        chat_cache.add_song(chat_id, CachedTrack(
            name=track.name,
            track_id=track.id,
            loop=1 if not is_active and i == 0 else 0,
            duration=track.duration,
            thumbnail=track.cover,
            user=user_by,
            file_path="",
            platform=track.platform,
            is_video=False,
            url=track.url,
        ))
        items.append(f"<b>{pos}.</b> {track.name}\n└ Süre: {sec_to_min(track.duration)}")

    summary = (
        "</blockquote>\n"
        f"🎶 <b>Toplam:</b> {len(chat_cache.get_queue(chat_id))} şarkı\n"
        f"⏱ <b>Toplam Süre:</b> {sec_to_min(sum(t.duration for t in tracks))}\n"
        f"👤 <b>Ekleyen:</b> {user_by}"
    )

    text = header + "\n".join(items) + summary
    if len(text) > 4096:
        text = summary

    if not is_active:
        await call.play_next(chat_id)
    await edit_text(msg, text, reply_markup=control_buttons("play"))


# ─────────────────────────────────────────────
# 🔍 Eksik Fonksiyon (Metin Arama)
# ─────────────────────────────────────────────

async def _handle_text_search(c: Client, msg: types.Message, wrapper, user_by: str):
    """Metinle şarkı arar ve çalmaya başlatır."""
    search = await wrapper.search()
    if isinstance(search, types.Error):
        return await edit_text(msg, text=f"🔍 Arama hatası: {search.message}", reply_markup=SupportButton)
    if not search or not search.tracks:
        return await edit_text(msg, text="❌ Hiç sonuç bulunamadı.", reply_markup=SupportButton)

    info = await wrapper.get_info(search.tracks[0].url)
    if isinstance(info, types.Error):
        return await edit_text(msg, text=f"⚠️ Şarkı bilgisi alınamadı: {info.message}")

    return await play_music(c, msg, info, user_by)


# ─────────────────────────────────────────────
# 🎶 Ana Oynatma Komutu
# ─────────────────────────────────────────────

async def play_music(c: Client, msg: types.Message, url_data: PlatformTracks, user_by: str, tg_file_path=None, is_video=False):
    """Ana müzik oynatma işlemi."""
    if not url_data or not url_data.tracks:
        return await edit_text(msg, "❌ Hiç şarkı bulunamadı.")

    await edit_text(msg, text="⬇️ Şarkı indiriliyor...")

    if len(url_data.tracks) == 1:
        return await _handle_single_track(c, msg, url_data.tracks[0], user_by, tg_file_path, is_video)
    return await _handle_multiple_tracks(msg, url_data.tracks, user_by)


# ─────────────────────────────────────────────
# 📂 Telegram Dosya Oynatma
# ─────────────────────────────────────────────

async def _handle_telegram_file(c: Client, reply: types.Message, msg: types.Message, user_by: str):
    """Telegram üzerinden gönderilen ses/video dosyalarını işler."""
    content = reply.content
    is_video = isinstance(content, (types.MessageVideo, types.Video)) or (
        isinstance(content, (types.MessageDocument, types.Document))
        and getattr(content, "mime_type", "").startswith("video/")
    )

    file_path, file_name = await tg.download_msg(reply, msg)
    if isinstance(file_path, types.Error):
        return await edit_text(
            msg,
            text=f"⚠️ Dosya indirilemedi:\n<code>{file_name}</code>\n<b>Hata:</b> {file_path.message}",
        )

    duration = await get_audio_duration(file_path.path)
    track_data = PlatformTracks(tracks=[
        MusicTrack(name=file_name, id=reply.remote_unique_file_id, cover="", duration=duration, url="", platform="telegram")
    ])
    await play_music(c, msg, track_data, user_by, file_path.path, is_video)


# ─────────────────────────────────────────────
# 🧩 Komut Yöneticisi
# ─────────────────────────────────────────────

async def handle_play_command(c: Client, msg: types.Message, is_video=False):
    """Ana /play ve /vplay komut yöneticisi."""
    chat_id = msg.chat_id

    if chat_id > 0:
        return await msg.reply_text("❌ Bu komut sadece gruplarda kullanılabilir.")

    if len(chat_cache.get_queue(chat_id)) > 10:
        return await msg.reply_text("⚠️ Kuyruk sınırı (10) aşıldı. /end ile temizleyebilirsin.")

    await load_admin_cache(c, chat_id)
    if not await is_admin(chat_id, c.me.id):
        return await msg.reply_text("⚠️ Müzik çalmak için yöneticilik izni gerekiyor. Lütfen beni yönetici yap ve tekrar dene.")

    reply = await msg.getRepliedMessage() if msg.reply_to_message_id else None
    url = await get_url(msg, reply)

    status_msg = await msg.reply_text("🔍 İstek işleniyor...")
    await del_msg(msg)

    args = extract_argument(msg.text)
    wrapper = (YouTubeData if is_video else DownloaderWrapper)(url or args)
    requester = await msg.mention()

    if not args and not url and (not reply or not tg.is_valid(reply)):
        usage = (
            f"🎵 <b>Kullanım:</b>\n"
            f"/{'vplay' if is_video else 'play'} [şarkı adı | bağlantı]\n\n"
            "Desteklenen platformlar:\n▫ YouTube\n▫ Spotify\n▫ JioSaavn\n▫ SoundCloud\n▫ Apple Music"
        )
        return await edit_text(status_msg, text=usage, reply_markup=SupportButton)

    if reply and tg.is_valid(reply):
        return await _handle_telegram_file(c, reply, status_msg, requester)

    if url:
        if not wrapper.is_valid():
            return await edit_text(
                status_msg,
                text="⚠️ Desteklenmeyen bağlantı türü.",
                reply_markup=SupportButton,
            )

        info = await wrapper.get_info()
        if isinstance(info, types.Error):
            return await edit_text(status_msg, text=f"⚠️ Şarkı bilgisi alınamadı: {info.message}")
        return await play_music(c, status_msg, info, requester, is_video=is_video)

    if not is_video:
        return await _handle_text_search(c, status_msg, wrapper, requester)

    search = await wrapper.search()
    if isinstance(search, types.Error):
        return await edit_text(status_msg, text=f"🔍 Arama hatası: {search.message}", reply_markup=SupportButton)
    if not search or not search.tracks:
        return await edit_text(status_msg, text="🔍 Hiç sonuç bulunamadı.", reply_markup=SupportButton)

    info = await DownloaderWrapper(search.tracks[0].url).get_info()
    if isinstance(info, types.Error):
        return await edit_text(status_msg, text=f"⚠️ Video oynatılamadı: {info.message}", reply_markup=SupportButton)
    return await play_music(c, status_msg, info, requester, is_video=True)


# ─────────────────────────────────────────────
# 🔘 Komut Kayıtları
# ─────────────────────────────────────────────

@Client.on_message(filters=Filter.command("oynat"), position=-5)
async def play_audio(c: Client, msg: types.Message):
    """Ses oynatma komutu."""
    await handle_play_command(c, msg, False)


@Client.on_message(filters=Filter.command("voynat"), position=-4)
async def play_video(c: Client, msg: types.Message):
    """Video oynatma komutu."""
    await handle_play_command(c, msg, True)