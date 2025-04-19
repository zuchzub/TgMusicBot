#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from pytdbot import types
from src import config

# ─────────────────────
# Inline Button Definitions
# ─────────────────────

SKIP_BTN = types.InlineKeyboardButton(
    text="⏭️", type=types.InlineKeyboardButtonTypeCallback(b"play_skip")
)

STOP_BTN = types.InlineKeyboardButton(
    text="⏹️", type=types.InlineKeyboardButtonTypeCallback(b"play_stop")
)

PAUSE_BTN = types.InlineKeyboardButton(
    text="⏸️", type=types.InlineKeyboardButtonTypeCallback(b"play_pause")
)

RESUME_BTN = types.InlineKeyboardButton(
    text="▶️", type=types.InlineKeyboardButtonTypeCallback(b"play_resume")
)

CLOSE_BTN = types.InlineKeyboardButton(
    text="❌ Close", type=types.InlineKeyboardButtonTypeCallback(b"play_close")
)

CHANNEL_BTN = types.InlineKeyboardButton(
    text="📢 Channel", type=types.InlineKeyboardButtonTypeUrl(config.SUPPORT_CHANNEL)
)

GROUP_BTN = types.InlineKeyboardButton(
    text="💬 Group", type=types.InlineKeyboardButtonTypeUrl(config.SUPPORT_GROUP)
)

# ─────────────────────
# Inline Keyboard Markups
# ─────────────────────

PlayButton = types.ReplyMarkupInlineKeyboard(
    [[SKIP_BTN, STOP_BTN, PAUSE_BTN, RESUME_BTN], [CLOSE_BTN]]
)

PauseButton = types.ReplyMarkupInlineKeyboard(
    [[SKIP_BTN, STOP_BTN, RESUME_BTN], [CLOSE_BTN]]
)

ResumeButton = types.ReplyMarkupInlineKeyboard(
    [[SKIP_BTN, STOP_BTN, PAUSE_BTN], [CLOSE_BTN]]
)

SupportButton = types.ReplyMarkupInlineKeyboard([[CHANNEL_BTN, GROUP_BTN], [CLOSE_BTN]])

# ─────────────────────
# Dynamic Keyboard Generator
# ─────────────────────


def add_me_markup(username: str) -> types.ReplyMarkupInlineKeyboard:
    """
    Returns an inline keyboard with a button to add the bot to a group
    and support buttons.
    """
    return types.ReplyMarkupInlineKeyboard(
        [
            [
                types.InlineKeyboardButton(
                    text="➕ Add me to your group",
                    type=types.InlineKeyboardButtonTypeUrl(
                        f"https://t.me/{username}?startgroup=true"
                    ),
                ),
            ],
            [CHANNEL_BTN, GROUP_BTN],
        ]
    )
