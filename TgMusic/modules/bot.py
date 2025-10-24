import time
from datetime import datetime

from cachetools import TTLCache
from pytdbot import Client, types

from TgMusic import StartTime
from TgMusic.core import (
    chat_invite_cache,
    user_status_cache,
    chat_cache,
    call,
    Filter,
)
from TgMusic.core.admins import load_admin_cache
from TgMusic.modules.utils import sec_to_min


@Client.on_message(filters=Filter.command("privacy"))
async def privacy_handler(c: Client, message: types.Message):
    """
    /privacy komutunu işleyerek gizlilik politikasını gösterir.
    """
    bot_name = c.me.first_name
    text = f"""
    <u><b>{bot_name} için Gizlilik Politikası:</b></u>

<b>1. Veri Saklama:</b>
- {bot_name}, kullanıcının cihazında hiçbir kişisel veri saklamaz.
- Cihazınız veya kişisel gezinme etkinliğiniz hakkında herhangi bir veri toplamayız veya saklamayız.

<b>2. Topladığımız Veriler:</b>
- Yalnızca müzik oynatma ve etkileşim özelliklerini sağlayabilmek için Telegram <b>kullanıcı kimliğinizi (User ID)</b> ve <b>sohbet kimliğinizi (Chat ID)</b> toplarız.
- Adınız, telefon numaranız veya konumunuz gibi kişisel bilgiler toplanmaz.

<b>3. Verilerin Kullanımı:</b>
- Toplanan veriler (Telegram Kullanıcı ID, Sohbet ID) yalnızca botun müzik oynatma ve etkileşim özelliklerini sağlamak amacıyla kullanılır.
- Bu veriler pazarlama veya ticari amaçlarla kullanılmaz.

<b>4. Veri Paylaşımı:</b>
- Kişisel veya sohbet verilerinizi hiçbir üçüncü taraf, kurum veya kişiyle paylaşmayız.
- Hiçbir hassas veri satılmaz, kiralanmaz veya ticaret amacıyla devredilmez.

<b>5. Veri Güvenliği:</b>
- Topladığımız verileri korumak için makul güvenlik önlemleri alıyoruz. Buna şifreleme ve güvenli depolama gibi standart uygulamalar dâhildir.
- Ancak hiçbir çevrimiçi hizmetin %100 güvenli olmadığı unutulmamalıdır.

<b>6. Çerezler ve Takip:</b>
- {bot_name}, çerez veya benzeri takip teknolojilerini kullanarak kişisel bilgi toplamaz veya davranışınızı izlemez.

<b>7. Üçüncü Taraf Hizmetler:</b>
- {bot_name}, Telegram’ın kendi altyapısı dışında kişisel verilerinizi toplayan veya işleyen üçüncü taraf hizmetlerle entegre değildir.

<b>8. Haklarınız:</b>
- Verilerinizin silinmesini talep etme hakkına sahipsiniz. Bot yalnızca Telegram ID ve Chat ID bilgilerini geçici olarak sakladığı için, bunlar isteğiniz üzerine kaldırılabilir.
- Ayrıca botu kaldırarak veya engelleyerek erişimi istediğiniz zaman iptal edebilirsiniz.

<b>9. Gizlilik Politikasındaki Değişiklikler:</b>
- Bu gizlilik politikası zaman zaman güncellenebilir. Herhangi bir değişiklik bot üzerinden duyurulacaktır.

<b>10. İletişim:</b>
Gizlilik politikamızla ilgili herhangi bir sorunuz veya endişeniz varsa, <a href="https://t.me/GuardxSupport">Destek Grubu</a> üzerinden bizimle iletişime geçebilirsiniz.

──────────────────
<b>Not:</b> Bu gizlilik politikası, verilerinizin nasıl işlendiğini anlamanıza yardımcı olmak ve {bot_name} ile deneyiminizin güvenli ve saygılı olmasını sağlamak için hazırlanmıştır.
    """

    reply = await message.reply_text(text)
    if isinstance(reply, types.Error):
        c.logger.warning(f"Gizlilik politikası mesajı gönderilirken hata oluştu: {reply.message}")
    return


rate_limit_cache = TTLCache(maxsize=100, ttl=180)


@Client.on_message(filters=Filter.command(["reload"]))
async def reload_cmd(c: Client, message: types.Message) -> None:
    """Botu yeniden yüklemek için /reload komutunu işler."""
    user_id = message.from_id
    chat_id = message.chat_id
    if chat_id > 0:
        reply = await message.reply_text(
            "🚫 Bu komut yalnızca süper gruplarda kullanılabilir."
        )
        if isinstance(reply, types.Error):
            c.logger.warning(f"Mesaj gönderme hatası: {reply} - Sohbet {chat_id}")
        return None

    if user_id in rate_limit_cache:
        last_used_time = rate_limit_cache[user_id]
        time_remaining = 180 - (datetime.now() - last_used_time).total_seconds()
        reply = await message.reply_text(
            f"🚫 Bu komutu tekrar kullanmadan önce beklemeniz gereken süre: ({sec_to_min(time_remaining)} dakika)"
        )
        if isinstance(reply, types.Error):
            c.logger.warning(f"Mesaj gönderme hatası: {reply} - Sohbet {chat_id}")
        return None

    rate_limit_cache[user_id] = datetime.now()
    reply = await message.reply_text("🔄 Yeniden yükleniyor...")
    if isinstance(reply, types.Error):
        c.logger.warning(f"Mesaj gönderme hatası: {reply} - Sohbet {chat_id}")
        return None

    ub = await call.get_client(chat_id)
    if isinstance(ub, types.Error):
        await reply.edit_text(ub.message)
        return None

    chat_invite_cache.pop(chat_id, None)
    user_key = f"{chat_id}:{ub.me.id}"
    user_status_cache.pop(user_key, None)

    if not chat_cache.is_active(chat_id):
        chat_cache.clear_chat(chat_id)

    load_admins, _ = await load_admin_cache(c, chat_id, True)
    ub_stats = await call.check_user_status(chat_id)
    if isinstance(ub_stats, types.Error):
        ub_stats = ub_stats.message

    loaded = "✅" if load_admins else "❌"
    text = (
        f"<b>Asistan Durumu:</b> {ub_stats.getType()}\n"
        f"<b>Yöneticiler Yüklendi:</b> {loaded}\n"
        f"<b>» Yeniden yükleyen:</b> {await message.mention()}"
    )

    reply = await reply.edit_text(text)
    if isinstance(reply, types.Error):
        c.logger.warning(f"Mesaj gönderme hatası: {reply} - Sohbet {chat_id}")
    return None


@Client.on_message(filters=Filter.command("ping"))
async def ping_cmd(client: Client, message: types.Message) -> None:
    """
    /ping komutunu işleyerek botun performans durumunu gösterir.
    """
    response = await call.stats_call(message.chat_id if message.chat_id < 0 else 1)
    if isinstance(response, types.Error):
        call_ping = response.message
        cpu_usage = "Kullanılamıyor"
    else:
        call_ping, cpu_usage = response
    call_ping_info = f"{call_ping:.2f} ms"
    cpu_info = f"{cpu_usage:.2f}%"
    uptime = datetime.now() - StartTime
    uptime_str = str(uptime).split(".")[0]
    start_time = time.monotonic()
    reply_msg = await message.reply_text("🏓 Ping ölçülüyor...")
    latency = (time.monotonic() - start_time) * 1000  # ms cinsinden
    response = (
        "📊 <b>Sistem Performans Bilgileri</b>\n\n"
        f"⏱️ <b>Bot Gecikmesi:</b> <code>{latency:.2f} ms</code>\n"
        f"🕒 <b>Çalışma Süresi:</b> <code>{uptime_str}</code>\n"
        f"🧠 <b>CPU Kullanımı:</b> <code>{cpu_info}</code>\n"
        f"📞 <b>NTgCalls Gecikmesi:</b> <code>{call_ping_info}</code>\n"
    )
    done = await reply_msg.edit_text(response, disable_web_page_preview=True)
    if isinstance(done, types.Error):
        client.logger.warning(f"Mesaj gönderme hatası: {done}")
    return None