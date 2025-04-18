#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from pytdbot import types

from src import config

# ─────────────────────
# Reusable Button Definitions
# ─────────────────────

SKIP_BUTTON = types.InlineKeyboardButton(
    text="⏭️", type=types.InlineKeyboardButtonTypeCallback(b"play_skip")
)

STOP_BUTTON = types.InlineKeyboardButton(
    text="⏹️", type=types.InlineKeyboardButtonTypeCallback(b"play_stop")
)

PAUSE_BUTTON = types.InlineKeyboardButton(
    text="⏸️", type=types.InlineKeyboardButtonTypeCallback(b"play_pause")
)

RESUME_BUTTON = types.InlineKeyboardButton(
    text="🔁", type=types.InlineKeyboardButtonTypeCallback(b"play_resume")
)

CLOSE_BUTTON = types.InlineKeyboardButton(
    text="❌ Close", type=types.InlineKeyboardButtonTypeCallback(b"play_close")
)

CHANNEL_BUTTON = types.InlineKeyboardButton(
    text="❄ Channel", type=types.InlineKeyboardButtonTypeUrl(config.SUPPORT_CHANNEL)
)

GROUP_BUTTON = types.InlineKeyboardButton(
    text="✨ Group", type=types.InlineKeyboardButtonTypeUrl(config.SUPPORT_GROUP)
)

# ─────────────────────
# Inline Keyboard Markups
# ─────────────────────

PlayButton = types.ReplyMarkupInlineKeyboard(
    [
        [SKIP_BUTTON, STOP_BUTTON, PAUSE_BUTTON, RESUME_BUTTON],
        [CLOSE_BUTTON],
    ]
)

PauseButton = types.ReplyMarkupInlineKeyboard(
    [
        [SKIP_BUTTON, STOP_BUTTON, RESUME_BUTTON],
        [CLOSE_BUTTON],
    ]
)

ResumeButton = types.ReplyMarkupInlineKeyboard(
    [
        [SKIP_BUTTON, STOP_BUTTON, PAUSE_BUTTON],
        [CLOSE_BUTTON],
    ]
)

SupportButton = types.ReplyMarkupInlineKeyboard(
    [
        [CHANNEL_BUTTON, GROUP_BUTTON],
        [CLOSE_BUTTON],
    ]
)


# ─────────────────────
# Dynamic Keyboard Function
# ─────────────────────


def add_me_button(username: str) -> types.ReplyMarkupInlineKeyboard:
    """
    Create an inline keyboard with 'Add me to your group' button.
    """
    return types.ReplyMarkupInlineKeyboard(
        [
            [
                types.InlineKeyboardButton(
                    text="Add me to your group",
                    type=types.InlineKeyboardButtonTypeUrl(
                        f"https://t.me/{username}?startgroup=true"
                    ),
                ),
            ],
            [CHANNEL_BUTTON, GROUP_BUTTON],
        ]
    )
