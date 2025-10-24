# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Tüm hakları saklıdır.

import asyncio
from pytdbot import Client, types

from TgMusic.core import (
    chat_invite_cache,
    ChatMemberStatus,
    user_status_cache,
    chat_cache,
    call,
    db,
    SupportButton,
    config,
)
from TgMusic.logger import LOGGER
from TgMusic.core.admins import load_admin_cache
from TgMusic.core.buttons import add_me_markup


# ───────────────────────────────
# 💬 GRUP DOĞRULAMA ve BİLGİLENDİRME
# ───────────────────────────────

async def handle_non_supergroup(client: Client, chat_id: int) -> None:
    """Grubun süpergrup olmadığı durumlarda kullanıcıyı bilgilendirir ve çıkar."""
    text = (
        f"⚠️ Bu sohbet ({chat_id}) henüz bir <b>süpergrup</b> değil!\n\n"
        "🔹 Lütfen grubu süpergruba dönüştürün ve beni yönetici olarak ekleyin.\n"
        "🔗 Nasıl yapılacağını bilmiyor musun? Rehber: "
        "<a href='https://te.legra.ph/How-to-Convert-a-Group-to-a-Supergroup-01-02'>Tıkla</a>\n\n"
        "Destek almak için grubumuza katılabilirsin:"
    )
    bot_username = client.me.usernames.editable_username
    await client.sendTextMessage(
        chat_id=chat_id,
        text=text,
        reply_markup=add_me_markup(bot_username),
        disable_web_page_preview=True,
    )
    await asyncio.sleep(2)
    await client.leaveChat(chat_id)


def is_valid_supergroup(chat_id: int) -> bool:
    """Chat ID'nin süpergrup formatında olup olmadığını kontrol eder."""
    return str(chat_id).startswith("-100")


# ───────────────────────────────
# 🚀 BOT GRUBA EKLENDİĞİNDE
# ───────────────────────────────

async def handle_bot_join(client: Client, chat_id: int) -> None:
    """Bot yeni bir gruba eklendiğinde çalışır."""
    _chat_id = int(str(chat_id)[4:]) if str(chat_id).startswith("-100") else chat_id
    chat_info = await client.getSupergroupFullInfo(_chat_id)

    if isinstance(chat_info, types.Error):
        client.logger.warning(
            "❌ Süpergrup bilgisi alınamadı: %s - %s", chat_id, chat_info.message
        )
        return

    # Minimum üye kontrolü
    if chat_info.member_count < config.MIN_MEMBER_COUNT:
        text = (
            f"⚠️ Bu grupta yeterli üye yok ({chat_info.member_count}).\n\n"
            f"Botun sağlıklı çalışması için en az <b>{config.MIN_MEMBER_COUNT}</b> üye gereklidir.\n"
            "Lütfen grubunuzu büyüttükten sonra beni tekrar ekleyin.\n\n"
            "Destek almak için grubumuza katılabilirsiniz:"
        )
        await client.sendTextMessage(chat_id, text, reply_markup=SupportButton)
        await asyncio.sleep(1)
        await client.leaveChat(chat_id)
        await db.remove_chat(chat_id)
        client.logger.info("Bot %s grubundan ayrıldı (yetersiz üye sayısı).", chat_id)
        return

    if invite_link := getattr(chat_info.invite_link, "invite_link", None):
        chat_invite_cache[chat_id] = invite_link


# ───────────────────────────────
# 👥 ÜYE DURUM GÜNCELLEMELERİ
# ───────────────────────────────

@Client.on_updateChatMember()
async def chat_member(client: Client, update: types.UpdateChatMember) -> None:
    """Üye katılımı, ayrılma, terfi veya yasaklanma gibi olayları yönetir."""
    chat_id = update.chat_id

    if chat_id > 0 or not await _validate_chat(client, chat_id):
        return None

    await db.add_chat(chat_id)
    new_member = update.new_chat_member.member_id
    user_id = (
        new_member.user_id
        if isinstance(new_member, types.MessageSenderUser)
        else new_member.chat_id
    )

    old_status = update.old_chat_member.status["@type"]
    new_status = update.new_chat_member.status["@type"]

    await _handle_status_changes(client, chat_id, user_id, old_status, new_status)
    return None


async def _validate_chat(client: Client, chat_id: int) -> bool:
    """Grubun süpergrup olup olmadığını kontrol eder."""
    if not is_valid_supergroup(chat_id):
        await handle_non_supergroup(client, chat_id)
        return False
    return True


# ───────────────────────────────
# 🔄 DURUM DEĞİŞİMLERİNİ YÖNET
# ───────────────────────────────

async def _handle_status_changes(
    client: Client, chat_id: int, user_id: int, old_status: str, new_status: str
) -> None:
    """Kullanıcıların durum değişimlerini yakalar ve işler."""
    if old_status == "chatMemberStatusLeft" and new_status in {
        "chatMemberStatusMember",
        "chatMemberStatusAdministrator",
    }:
        await _handle_join(client, chat_id, user_id)
    elif old_status in {"chatMemberStatusMember", "chatMemberStatusAdministrator"} and new_status == "chatMemberStatusLeft":
        await _handle_leave_or_kick(chat_id, user_id)
    elif new_status == "chatMemberStatusBanned":
        if user_id == client.me.id:
            await call.end(chat_id)
        await _handle_ban(chat_id, user_id)
    elif old_status == "chatMemberStatusBanned" and new_status == "chatMemberStatusLeft":
        await _handle_unban(chat_id, user_id)
    else:
        await _handle_promotion_demotion(client, chat_id, user_id, old_status, new_status)


async def _handle_join(client: Client, chat_id: int, user_id: int) -> None:
    """Kullanıcı/bot gruba katıldığında tetiklenir."""
    if user_id == client.options["my_id"]:
        await handle_bot_join(client, chat_id)
    LOGGER.debug("👋 Kullanıcı %s gruba katıldı (%s).", user_id, chat_id)


async def _handle_leave_or_kick(chat_id: int, user_id: int) -> None:
    """Kullanıcı gruptan ayrıldığında veya atıldığında."""
    LOGGER.debug("👋 Kullanıcı %s gruptan ayrıldı veya atıldı (%s).", user_id, chat_id)
    await _update_user_status_cache(chat_id, user_id, types.ChatMemberStatusLeft())


async def _handle_ban(chat_id: int, user_id: int) -> None:
    """Kullanıcı yasaklandığında."""
    LOGGER.debug("🚫 Kullanıcı %s grupta yasaklandı (%s).", user_id, chat_id)
    await _update_user_status_cache(chat_id, user_id, types.ChatMemberStatusBanned())


async def _handle_unban(chat_id: int, user_id: int) -> None:
    """Kullanıcının yasağı kaldırıldığında."""
    LOGGER.debug("✅ Kullanıcının yasağı kaldırıldı: %s (%s).", user_id, chat_id)
    await _update_user_status_cache(chat_id, user_id, types.ChatMemberStatusLeft())


async def _handle_promotion_demotion(
    client: Client, chat_id: int, user_id: int, old_status: str, new_status: str
) -> None:
    """Kullanıcının terfi veya düşürülme durumunu yönetir."""
    is_promoted = old_status != "chatMemberStatusAdministrator" and new_status == "chatMemberStatusAdministrator"
    is_demoted = old_status == "chatMemberStatusAdministrator" and new_status != "chatMemberStatusAdministrator"

    if not (is_promoted or is_demoted):
        return

    if user_id == client.options["my_id"] and is_promoted:
        LOGGER.info("🔼 Bot %s grubunda yönetici yapıldı, admin cache yenileniyor.", chat_id)
    else:
        action = "terfi etti" if is_promoted else "yetkisi kaldırıldı"
        LOGGER.debug("👤 Kullanıcı %s %s (%s).", user_id, action, chat_id)

    await load_admin_cache(client, chat_id, True)
    await asyncio.sleep(1)
    if is_promoted:
        await handle_bot_join(client, chat_id)


async def _update_user_status_cache(chat_id: int, user_id: int, status: ChatMemberStatus) -> None:
    """Kullanıcının durum önbelleğini günceller."""
    ub = await call.get_client(chat_id)
    if isinstance(ub, types.Error):
        LOGGER.warning("⚠️ Chat %s için istemci alınamadı: %s", chat_id, ub)
        return

    if user_id == ub.me.id:
        cache_key = f"{chat_id}:{ub.me.id}"
        user_status_cache[cache_key] = status


# ───────────────────────────────
# 🎥 VİDEO SOHBET OLAYLARI
# ───────────────────────────────

@Client.on_updateNewMessage(position=1)
async def new_message(client: Client, update: types.UpdateNewMessage) -> None:
    """Video sohbet başlatma/bitirme olaylarını dinler."""
    message = update.message
    if not message:
        return

    chat_id = message.chat_id
    content = message.content

    # Veritabanına kullanıcı/grup ekle
    if chat_id < 0:
        client.loop.create_task(db.add_chat(chat_id))
    else:
        client.loop.create_task(db.add_user(chat_id))

    # Video sohbet bittiğinde
    if isinstance(content, types.MessageVideoChatEnded):
        LOGGER.info("🎬 Video sohbet sonlandı (%s).", chat_id)
        chat_cache.clear_chat(chat_id)
        await client.sendTextMessage(chat_id, "🎧 Video sohbet sona erdi.\nTüm müzik sırası temizlendi.")
        return

    # Video sohbet başladığında
    if isinstance(content, types.MessageVideoChatStarted):
        LOGGER.info("🎥 Video sohbet başlatıldı (%s).", chat_id)
        chat_cache.clear_chat(chat_id)
        await client.sendTextMessage(chat_id, "🎶 Video sohbet başladı!\nMüzik çalmak için /play komutunu kullanabilirsin.")
        return

    LOGGER.debug("Yeni mesaj (%s): %s", chat_id, message)