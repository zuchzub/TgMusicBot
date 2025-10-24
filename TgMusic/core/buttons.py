#  ⚡ Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Reimagined by Kumal | Fancy UI Edition 🎧

from typing import Literal
from pytdbot import types
from ._config import config


# ╔══════════════════════════════════╗
#     🎛️ ꜰᴀɴᴄʏ ᴘʟᴀʏʙᴀᴄᴋ ᴄᴏɴᴛʀᴏʟꜱ
# ╚══════════════════════════════════╝
def control_buttons(mode: Literal["play", "pause", "resume"]) -> types.ReplyMarkupInlineKeyboard:
    prefix = "play"

    def btn(text: str, name: str) -> types.InlineKeyboardButton:
        return types.InlineKeyboardButton(
            text=text,
            type=types.InlineKeyboardButtonTypeCallback(f"{prefix}_{name}".encode()),
        )

    skip_btn = btn("⏭️", "skip")
    stop_btn = btn("⏹️", "stop")
    pause_btn = btn("⏸️", "pause")
    resume_btn = btn("▶️", "resume")
    close_btn = btn("✖️ kapat")

    # ☔ Mavi Duyuru bağlantısı (ꜰᴀɴᴄʏ ᴛᴇxᴛ)
    info_btn = types.InlineKeyboardButton(
        text="☔ ᴍᴀᴠɪ ᴅᴜʏᴜʀᴜ",
        type=types.InlineKeyboardButtonTypeUrl("https://t.me/MaviDuyuru"),
    )

    layouts = {
        "play": [[skip_btn, stop_btn, pause_btn, resume_btn], [info_btn, close_btn]],
        "pause": [[skip_btn, stop_btn, resume_btn], [info_btn, close_btn]],
        "resume": [[skip_btn, stop_btn, pause_btn], [info_btn, close_btn]],
    }

    return types.ReplyMarkupInlineKeyboard(layouts.get(mode, [[info_btn, close_btn]]))


# ╔══════════════════════════════════╗
#         🌐 ꜰᴀɴᴄʏ ɢʟᴏʙᴀʟ ᴜɪ
# ╚══════════════════════════════════╝

CLOSE_BTN = types.InlineKeyboardButton(
    text="✖️ ᴄʟᴏꜱᴇ", type=types.InlineKeyboardButtonTypeCallback(b"play_close")
)

CHANNEL_BTN = types.InlineKeyboardButton(
    text="📢 ᴋᴀɴᴀʟ", type=types.InlineKeyboardButtonTypeUrl(config.SUPPORT_CHANNEL)
)

GROUP_BTN = types.InlineKeyboardButton(
    text="💬 ᴅᴇꜱᴛᴇᴋ", type=types.InlineKeyboardButtonTypeUrl(config.SUPPORT_GROUP)
)

HELP_BTN = types.InlineKeyboardButton(
    text="📖 ʜᴇʟᴘ", type=types.InlineKeyboardButtonTypeCallback(b"help_all")
)

USER_BTN = types.InlineKeyboardButton(
    text="🎧 ᴜꜱᴇʀ", type=types.InlineKeyboardButtonTypeCallback(b"help_user")
)

ADMIN_BTN = types.InlineKeyboardButton(
    text="⚙️ ᴀᴅᴍɪɴ", type=types.InlineKeyboardButtonTypeCallback(b"help_admin")
)

OWNER_BTN = types.InlineKeyboardButton(
    text="👑 ᴏᴡɴᴇʀ", type=types.InlineKeyboardButtonTypeCallback(b"help_owner")
)

DEVS_BTN = types.InlineKeyboardButton(
    text="💻 ᴅᴇᴠꜱ", type=types.InlineKeyboardButtonTypeCallback(b"help_devs")
)

HOME_BTN = types.InlineKeyboardButton(
    text="🏠 ʜᴏᴍᴇ", type=types.InlineKeyboardButtonTypeCallback(b"help_back")
)


# ╔══════════════════════════════════╗
#         🧩 ꜰᴀɴᴄʏ ʟᴀʏᴏᴜᴛꜱ
# ╚══════════════════════════════════╝

SupportButton = types.ReplyMarkupInlineKeyboard(
    [
        [CHANNEL_BTN, GROUP_BTN],
        [CLOSE_BTN],
    ]
)

HelpMenu = types.ReplyMarkupInlineKeyboard(
    [
        [USER_BTN, ADMIN_BTN],
        [OWNER_BTN, DEVS_BTN],
        [HOME_BTN, CLOSE_BTN],
    ]
)

BackHelpMenu = types.ReplyMarkupInlineKeyboard(
    [
        [HELP_BTN, HOME_BTN],
        [CLOSE_BTN],
    ]
)


# ╔══════════════════════════════════╗
#        ➕ ꜰᴀɴᴄʏ ᴀᴅᴅ ʙᴜᴛᴛᴏɴ
# ╚══════════════════════════════════╝

def add_me_markup(username: str) -> types.ReplyMarkupInlineKeyboard:
    """ꜰᴀɴᴄʏ ɢʀᴜᴘ ᴇᴋʟᴇᴍᴇ ᴀʀᴀʏᴜ̈ᴢᴜ̈"""
    return types.ReplyMarkupInlineKeyboard(
        [
            [
                types.InlineKeyboardButton(
                    text="➕ ᴀᴅᴅ ᴍᴇ ᴛᴏ ɢʀᴏᴜᴘ",
                    type=types.InlineKeyboardButtonTypeUrl(
                        f"https://t.me/{username}?startgroup=true"
                    ),
                ),
            ],
            [HELP_BTN],
            [CHANNEL_BTN, GROUP_BTN],
        ]
    )