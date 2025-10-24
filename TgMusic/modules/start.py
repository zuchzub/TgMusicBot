# Telif Hakkı (c) 2025 AshokShau
# GNU AGPL v3.0 Lisansı altında: https://www.gnu.org/licenses/agpl-3.0.html
# TgMusicBot projesinin bir parçasıdır. Tüm hakları saklıdır.

from pytdbot import Client, types
from TgMusic import __version__
from TgMusic.core import config, Filter, SupportButton
from TgMusic.core.buttons import add_me_markup, HelpMenu, BackHelpMenu

# ─────────────────────────────
# 🎧 Başlangıç (Start) Mesajı
# ─────────────────────────────
startText = """
★━━━━━━━━━━━━━━━━━━━━★
🎶 <b>Selam {}</b>!
Ben <b>{}</b> — hızlı, akıllı ve çok yönlü bir Telegram müzik botuyum.  

🎵 <b>Desteklenen Platformlar:</b>  
🟥 YouTube ┃ 🟩 Spotify ┃ ☁️ SoundCloud ┃ 🍎 Apple Music

⚙️ <b>Özellikler:</b>  
• Mükemmel ses kalitesi  
• Video ve sesli oynatma desteği  
• Sıra yönetimi ve otomatik kontrol  
• Modern arayüz, hızlı tepki

💡 Tüm komutları görmek için “Yardım” butonuna dokun!
★━━━━━━━━━━━━━━━━━━━━★
"""

# ─────────────────────────────
# /start ve /help komutları
# ─────────────────────────────
@Client.on_message(filters=Filter.command(["start", "help"]))
async def start_cmd(c: Client, message: types.Message):
    chat_id = message.chat_id
    bot_name = c.me.first_name
    mention = await message.mention()

    if chat_id < 0:  # Grup sohbeti
        welcome_text = (
            f"👋 <b>Selam {mention}!</b>\n\n"
            f"<b>{bot_name}</b> artık bu grupta aktif. 🎵\n\n"
            "🎧 Müzik, video ve gelişmiş oynatma kontrolleriyle hizmette!\n"
            "• YouTube, Spotify, SoundCloud ve daha fazlası\n"
            "• Kolay kullanım, yüksek performans\n\n"
            f"💬 Yardım: <a href='{config.SUPPORT_GROUP}'>Destek Sohbeti</a>"
        )
        reply = await message.reply_text(
            text=welcome_text,
            disable_web_page_preview=True,
            reply_markup=SupportButton,
        )
    else:  # Özel mesaj
        bot_username = c.me.usernames.editable_username
        reply = await message.reply_photo(
            photo=config.START_IMG,
            caption=startText.format(mention, bot_name),
            reply_markup=add_me_markup(bot_username),
        )

    if isinstance(reply, types.Error):
        c.logger.warning(reply.message)


# ─────────────────────────────
# 🎛 Yardım Menüsü (Callback)
# ─────────────────────────────
@Client.on_updateNewCallbackQuery(filters=Filter.regex(r"help_\w+"))
async def callback_query_help(c: Client, message: types.UpdateNewCallbackQuery) -> None:
    data = message.payload.data.decode()

    if data == "help_all":
        user = await c.getUser(message.sender_user_id)
        await message.answer("📚 Yardım menüsü açılıyor...")
        text = (
            f"👋 <b>Merhaba {user.first_name}!</b>\n\n"
            f"<b>{c.me.first_name}</b> yardım merkezine hoş geldin.\n"
            f"<code>Versiyon: v{__version__}</code>\n\n"
            "✨ <b>Neler yapabilirim?</b>\n"
            "🎵 YouTube, Spotify, Apple Music, SoundCloud desteği\n"
            "⚙️ Gelişmiş kuyruk ve oynatma yönetimi\n"
            "🧩 Grup ve özel sohbet desteği\n\n"
            "🔽 Aşağıdan bir kategori seç:"
        )
        edit = await message.edit_message_caption(text, reply_markup=HelpMenu)
        if isinstance(edit, types.Error):
            c.logger.error(f"Mesaj düzenlenemedi: {edit}")
        return

    if data == "help_back":
        await message.answer("🏠 Ana menüye dönülüyor...")
        user = await c.getUser(message.sender_user_id)
        await message.edit_message_caption(
            caption=startText.format(user.first_name, c.me.first_name),
            reply_markup=add_me_markup(c.me.usernames.editable_username),
        )
        return

    # ───── Yardım kategorileri ─────
    help_categories = {
        "help_user": {
            "title": "🎧 Kullanıcı",
            "content": (
                "🎵 <b>Oynatma:</b>\n"
                "• <code>/play [şarkı]</code> — Şarkı çalar\n"
                "• <code>/vplay [video]</code> — Video çalar\n\n"
                "🛠 <b>Yardımcı:</b>\n"
                "• <code>/start</code> — Başlangıç mesajı\n"
                "• <code>/queue</code> — Şarkı sırasını göster\n"
                "• <code>/privacy</code> — Gizlilik bilgisi"
            ),
            "markup": BackHelpMenu,
        },
        "help_admin": {
            "title": "⚙️ Yönetici",
            "content": (
                "🎛 <b>Kontroller:</b>\n"
                "• <code>/skip</code> — Atla\n"
                "• <code>/pause</code> — Durdur\n"
                "• <code>/resume</code> — Devam et\n"
                "• <code>/seek [sn]</code> — İleri sar\n"
                "• <code>/volume [1-200]</code> — Ses düzeyi\n\n"
                "📋 <b>Kuyruk:</b>\n"
                "• <code>/remove [x]</code> — Şarkı sil\n"
                "• <code>/clear</code> — Sırayı temizle\n"
                "• <code>/loop [0-10]</code> — Döngü sayısı\n\n"
                "👑 <b>Yetki:</b>\n"
                "• <code>/auth</code> — Yetki ver\n"
                "• <code>/unauth</code> — Yetkiyi kaldır\n"
                "• <code>/authlist</code> — Yetkilileri gör"
            ),
            "markup": BackHelpMenu,
        },
        "help_owner": {
            "title": "🔐 Sahip",
            "content": (
                "⚙️ <b>Ayarlar:</b>\n"
                "• <code>/buttons</code> — Butonları aç/kapat\n"
                "• <code>/thumb</code> — Kapak görselleri"
            ),
            "markup": BackHelpMenu,
        },
        "help_devs": {
            "title": "🧠 Geliştirici",
            "content": (
                "📊 <b>Sistem:</b>\n"
                "• <code>/stats</code> — İstatistik\n"
                "• <code>/logger</code> — Log modu\n"
                "• <code>/broadcast</code> — Duyuru\n\n"
                "🧹 <b>Bakım:</b>\n"
                "• <code>/activevc</code> — Aktif odalar\n"
                "• <code>/clearallassistants</code> — Temizle\n"
                "• <code>/autoend</code> — Otomatik çıkış"
            ),
            "markup": BackHelpMenu,
        },
    }

    if category := help_categories.get(data):
        await message.answer(f"📘 {category['title']}")
        formatted_text = (
            f"<b>{category['title']}</b>\n\n"
            f"{category['content']}\n\n"
            "🔙 <i>Geri dönmek için butonu kullan.</i>"
        )
        edit = await message.edit_message_caption(formatted_text, reply_markup=category["markup"])
        if isinstance(edit, types.Error):
            c.logger.error(f"Mesaj düzenlenemedi: {edit}")
        return

    await message.answer("⚠️ Bilinmeyen kategori.")