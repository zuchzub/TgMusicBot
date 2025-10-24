# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında lisanslanmıştır: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Uygulanabilir yerlerde tüm hakları saklıdır.

from typing import Union

from pytdbot import Client, types

from TgMusic.core import Filter, db, is_admin
from TgMusic.logger import LOGGER


async def _validate_auth_command(msg: types.Message) -> Union[types.Message, None]:
    """Yetkilendirme komutu için gereksinimleri doğrula."""
    chat_id = msg.chat_id
    if chat_id > 0:
        return None

    if not await is_admin(chat_id, msg.from_id):
        reply = await msg.reply_text("⛔ Bu komutu yalnızca grup yöneticisi kullanabilir.")
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return None

    if not msg.reply_to_message_id:
        reply = await msg.reply_text(
            "🔍 Bir kullanıcının izinlerini yönetmek için lütfen bir mesaja yanıt verin."
        )
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return None

    reply = await msg.getRepliedMessage()
    if isinstance(reply, types.Error):
        reply = await msg.reply_text(f"⚠️ Hata: {reply.message}")
        if isinstance(reply, types.Error):
            LOGGER.warning(reply.message)
        return None

    if reply.from_id == msg.from_id:
        _reply = await msg.reply_text("❌ Kendi izinlerinizi değiştiremezsiniz.")
        if isinstance(_reply, types.Error):
            LOGGER.warning(_reply.message)
        return None

    if isinstance(reply.sender_id, types.MessageSenderChat):
        _reply = await msg.reply_text("❌ Kanallara kullanıcı izni verilemez.")
        if isinstance(_reply, types.Error):
            LOGGER.warning(_reply.message)
        return None

    return reply


@Client.on_message(filters=Filter.command(["auth"]))
async def auth(c: Client, msg: types.Message) -> None:
    """Bir kullanıcıya yetki izni ver."""
    reply = await _validate_auth_command(msg)
    if not reply:
        return

    chat_id = msg.chat_id
    user_id = reply.from_id

    if user_id in await db.get_auth_users(chat_id):
        reply = await msg.reply_text("ℹ️ Kullanıcının zaten yetkilendirme izni var.")
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)
    else:
        await db.add_auth_user(chat_id, user_id)
        reply = await msg.reply_text(
            "✅ Kullanıcıya başarıyla yetkilendirme izni verildi."
        )
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)


@Client.on_message(filters=Filter.command(["unauth"]))
async def un_auth(c: Client, msg: types.Message) -> None:
    """Bir kullanıcının yetki iznini kaldır."""
    reply = await _validate_auth_command(msg)
    if not reply:
        return

    chat_id = msg.chat_id
    user_id = reply.from_id

    if user_id not in await db.get_auth_users(chat_id):
        reply = await msg.reply_text("ℹ️ Kullanıcının herhangi bir yetkilendirme izni yok.")
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)
    else:
        await db.remove_auth_user(chat_id, user_id)
        reply = await msg.reply_text(
            "✅ Kullanıcının yetkilendirme izni kaldırıldı."
        )
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)


@Client.on_message(filters=Filter.command(["authlist"]))
async def auth_list(c: Client, msg: types.Message) -> None:
    """Tüm yetkilendirilmiş kullanıcıları listele."""
    chat_id = msg.chat_id
    if chat_id > 0:
        reply = await msg.reply_text("❌ Bu komut yalnızca gruplarda kullanılabilir.")
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)
        return

    if not await is_admin(chat_id, msg.from_id):
        reply = await msg.reply_text("⛔ Yönetici yetkisi gerekli.")
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)
        return

    auth_users = await db.get_auth_users(chat_id)
    if not auth_users:
        reply = await msg.reply_text("ℹ️ Herhangi bir yetkili kullanıcı bulunamadı.")
        if isinstance(reply, types.Error):
            c.logger.warning(reply.message)
        return

    text = "<b>🔐 Yetkili Kullanıcılar:</b>\n\n" + "\n".join(
        [f"• <code>{uid}</code>" for uid in auth_users]
    )
    reply = await msg.reply_text(text)
    if isinstance(reply, types.Error):
        c.logger.warning(reply.message)