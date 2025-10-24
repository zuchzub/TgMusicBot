#  Telif Hakkı (c) 2025 AshokShau
#  GNU AGPL v3.0 Lisansı altında lisanslanmıştır: https://www.gnu.org/licenses/agpl-3.0.html
#  TgMusicBot projesinin bir parçasıdır. Uygulanabilir yerlerde tüm hakları saklıdır.

from pytdbot import Client, types

from TgMusic.core import Filter, control_buttons, chat_cache, db, call
from TgMusic.core.admins import is_admin, load_admin_cache
from .play import _get_platform_url, play_music
from .progress_handler import _handle_play_c_data
from .utils.play_helpers import edit_text
from ..core import DownloaderWrapper


@Client.on_updateNewCallbackQuery(filters=Filter.regex(r"(c)?play_\w+"))
async def callback_query(c: Client, message: types.UpdateNewCallbackQuery) -> None:
    """Müzik kontrol butonlarına verilen geri bildirimleri işler (duraklat, devam, geç, durdur vb.)."""
    data = message.payload.data.decode()
    user_id = message.sender_user_id

    # Mesaj ve kullanıcı bilgilerini al
    get_msg = await message.getMessage()
    if isinstance(get_msg, types.Error):
        c.logger.warning(f"Mesaj alınamadı: {get_msg.message}")
        return None

    user = await c.getUser(user_id)
    if isinstance(user, types.Error):
        c.logger.warning(f"Kullanıcı bilgisi alınamadı: {user.message}")
        return None

    await load_admin_cache(c, message.chat_id)
    user_name = user.first_name

    # Yönetici kontrolü gerektiren işlemler
    def requires_admin(action: str) -> bool:
        return action in {
            "play_skip",
            "play_stop",
            "play_pause",
            "play_resume",
            "play_close",
        }

    # Aktif oturum gerektiren işlemler
    def requires_active_chat(action: str) -> bool:
        return action in {
            "play_skip",
            "play_stop",
            "play_pause",
            "play_resume",
            "play_timer",
        }

    # Standart yanıt gönderici
    async def send_response(
        msg: str, alert: bool = False, delete: bool = False, reply_markup=None
    ) -> None:
        if alert:
            await message.answer(msg, show_alert=True)
        else:
            edit_func = (
                message.edit_message_caption
                if get_msg.caption
                else message.edit_message_text
            )
            await edit_func(msg, reply_markup=reply_markup)

        if delete:
            _del_result = await c.deleteMessages(
                message.chat_id, [message.message_id], revoke=True
            )
            if isinstance(_del_result, types.Error):
                c.logger.warning(f"Mesaj silinemedi: {_del_result.message}")

    # Yönetici yetkisi kontrolü
    if requires_admin(data) and not await is_admin(message.chat_id, user_id):
        await message.answer(
            "⛔ Bu işlemi yapmak için **yönetici yetkisi** gerekiyor.", show_alert=True
        )
        return None

    chat_id = message.chat_id
    if requires_active_chat(data) and not chat_cache.is_active(chat_id):
        return await send_response(
            "🎧 Şu anda bu sohbette aktif bir müzik çalma yok.", alert=True
        )

    # 🔹 Şarkı atlama
    if data == "play_skip":
        result = await call.play_next(chat_id)
        if isinstance(result, types.Error):
            return await send_response(
                f"⚠️ Şarkı atlanamadı.\n<b>Detay:</b> {result.message}", alert=True
            )
        return await send_response("⏭️ Şarkı başarıyla **atlandı** 🎶", delete=True)

    # 🔹 Oynatmayı durdurma
    if data == "play_stop":
        result = await call.end(chat_id)
        if isinstance(result, types.Error):
            return await send_response(
                f"⚠️ Oynatma durdurulamadı.\n{result.message}", alert=True
            )
        return await send_response(
            f"<b>⏹️ Müzik Durduruldu</b>\n🎧 İstek: {user_name}"
        )

    # 🔹 Oynatmayı duraklatma
    if data == "play_pause":
        result = await call.pause(chat_id)
        if isinstance(result, types.Error):
            return await send_response(
                f"⚠️ Duraklatma başarısız.\n{result.message}", alert=True
            )
        markup = (
            control_buttons("pause") if await db.get_buttons_status(chat_id) else None
        )
        return await send_response(
            f"<b>⏸️ Şarkı duraklatıldı.</b>\n🎧 {user_name} tarafından duraklatıldı.",
            reply_markup=markup,
        )

    # 🔹 Oynatmaya devam etme
    if data == "play_resume":
        result = await call.resume(chat_id)
        if isinstance(result, types.Error):
            return await send_response(
                f"⚠️ Devam ettirilemedi.\n{result.message}", alert=True
            )
        markup = (
            control_buttons("resume") if await db.get_buttons_status(chat_id) else None
        )
        return await send_response(
            f"<b>▶️ Müzik devam ediyor!</b>\n🎶 {user_name} tarafından başlatıldı.",
            reply_markup=markup,
        )

    # 🔹 Arayüz kapatma
    if data == "play_close":
        delete_result = await c.deleteMessages(
            chat_id, [message.message_id], revoke=True
        )
        if isinstance(delete_result, types.Error):
            await message.answer(
                f"⚠️ Arayüz kapatılamadı.\n{delete_result.message}", show_alert=True
            )
            return None
        await message.answer("✅ Arayüz başarıyla kapatıldı.", show_alert=True)
        return None

    # 🔹 Playlist veya zamanlayıcı işlemleri
    if data.startswith("play_c_"):
        return await _handle_play_c_data(data, message, chat_id, user_id, user_name, c)

    # 🔹 Şarkı oynatma istekleri
    try:
        _, platform, song_id = data.split("_", 2)
    except ValueError:
        c.logger.error(f"Hatalı callback verisi alındı: {data}")
        return await send_response("⚠️ Geçersiz istek biçimi.", alert=True)

    await message.answer(f"🎵 {user_name} için şarkı hazırlanıyor...", show_alert=True)
    reply = await message.edit_message_text(
        f"🔍 Şarkı aranıyor...\n👤 İstek: {user_name}"
    )
    if isinstance(reply, types.Error):
        c.logger.warning(f"Mesaj düzenlenemedi: {reply.message}")
        return None

    url = _get_platform_url(platform, song_id)
    if not url:
        c.logger.error(f"Desteklenmeyen platform: {platform} | Veri: {data}")
        await edit_text(reply, text=f"⚠️ Bu platform desteklenmiyor: {platform}")
        return None

    song = await DownloaderWrapper(url).get_info()
    if song:
        if isinstance(song, types.Error):
            await edit_text(reply, text=f"⚠️ Şarkı alınamadı.\n{song.message}")
            return None

        return await play_music(c, reply, song, user_name)

    await edit_text(reply, text="⚠️ İstenen içerik bulunamadı 😕")
    return None