#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from typing import Optional

from pytdbot import Client, types

from src.helpers import db, get_string
from src.modules.utils import Filter
from src.modules.utils.admins import is_admin, is_owner
from src.modules.utils.play_helpers import extract_argument


async def _validate_auth_command(msg: types.Message) -> Optional[types.Message]:
    chat_id = msg.chat_id
    if chat_id > 0:
        return None

    lang = await db.get_lang(chat_id)

    if not await is_owner(chat_id, msg.from_id):
        await msg.reply_text(get_string("only_owner", lang))
        return None

    if not msg.reply_to_message_id:
        await msg.reply_text(get_string("reply_manage_auth", lang))
        return None

    reply = await msg.getRepliedMessage()
    if isinstance(reply, types.Error):
        await msg.reply_text(f"⚠️ {reply.message}")
        return None

    if reply.from_id == msg.from_id:
        await msg.reply_text(get_string("cannot_change_self", lang))
        return None

    if isinstance(reply.sender_id, types.MessageSenderChat):
        await msg.reply_text(get_string("cannot_change_channel", lang))
        return None

    return reply


@Client.on_message(filters=Filter.command("auth"))
async def auth(_: Client, msg: types.Message):
    reply = await _validate_auth_command(msg)
    if not reply:
        return

    chat_id = msg.chat_id
    user_id = reply.from_id
    lang = await db.get_lang(chat_id)

    if user_id in await db.get_auth_users(chat_id):
        await msg.reply_text(get_string("user_already_auth", lang))
    else:
        await db.add_auth_user(chat_id, user_id)
        await msg.reply_text(get_string("user_granted_auth", lang))


@Client.on_message(filters=Filter.command("unauth"))
async def un_auth(_: Client, msg: types.Message):
    reply = await _validate_auth_command(msg)
    if not reply:
        return

    chat_id = msg.chat_id
    user_id = reply.from_id
    lang = await db.get_lang(chat_id)

    if user_id not in await db.get_auth_users(chat_id):
        await msg.reply_text(get_string("user_not_auth", lang))
    else:
        await db.remove_auth_user(chat_id, user_id)
        await msg.reply_text(get_string("user_removed_auth", lang))


@Client.on_message(filters=Filter.command("authlist"))
async def auth_list(_: Client, msg: types.Message):
    chat_id = msg.chat_id
    lang = await db.get_lang(chat_id)

    if chat_id > 0:
        await msg.reply_text(get_string("only_group", lang))
        return

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text(get_string("only_admin", lang))
        return

    auth_users = await db.get_auth_users(chat_id)
    if not auth_users:
        await msg.reply_text(get_string("no_auth_users", lang))
        return

    text = (
        get_string("auth_list_header", lang)
        + "\n"
        + "\n".join([f"- <code>{uid}</code>" for uid in auth_users])
    )
    await msg.reply_text(text)


async def _handle_toggle_command(
    msg: types.Message, key: str, label: str, get_func, set_func
):
    chat_id = msg.chat_id
    lang = await db.get_lang(chat_id)

    if chat_id > 0:
        await msg.reply_text(get_string("only_group", lang))
        return

    if not await is_owner(chat_id, msg.from_id):
        await msg.reply_text(get_string("only_owner", lang))
        return

    current = await get_func(chat_id)
    args = extract_argument(msg.text)
    if not args:
        status = (
            get_string("enabled", lang) if current else get_string("disabled", lang)
        )
        await msg.reply_text(
            get_string("toggle_status", lang).format(
                label=label, status=status, key=key
            )
        )
        return

    arg = args.lower()
    if arg in ["on", "enable"]:
        await set_func(chat_id, True)
        await msg.reply_text(get_string(f"{key}_status_enabled", lang))
    elif arg in ["off", "disable"]:
        await set_func(chat_id, False)
        await msg.reply_text(get_string(f"{key}_status_disabled", lang))
    else:
        await msg.reply_text(get_string("invalid_toggle_usage", lang).format(key=key))


@Client.on_message(filters=Filter.command("buttons"))
async def buttons(_: Client, msg: types.Message):
    await _handle_toggle_command(
        msg, "buttons", "Button control", db.get_buttons_status, db.set_buttons_status
    )


@Client.on_message(filters=Filter.command(["thumbnail", "thumb"]))
async def thumbnail(_: Client, msg: types.Message):
    await _handle_toggle_command(
        msg, "thumbnail", "Thumbnail", db.get_thumb_status, db.set_thumb_status
    )
