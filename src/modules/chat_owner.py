#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from typing import Optional

from pytdbot import Client, types

from src import db
from src.modules.utils import Filter
from src.modules.utils.admins import is_admin, is_owner
from src.modules.utils.play_helpers import extract_argument


async def _validate_auth_command(msg: types.Message) -> Optional[types.Message]:
    """Validate a message for the auth commands.

    This function should be called as the first step of the auth
    commands. It checks if the message is from a private chat, if the
    sender is the owner of the chat, if the message is a reply to
    another message, and if the replied message is from a user or a
    channel.

    Returns the replied message if all checks pass, otherwise None.
    """
    if msg.chat_id > 0:
        return None

    if not await is_owner(msg.chat_id, msg.from_id):
        await msg.reply_text("Only group owner can use this command.")
        return None

    if not msg.reply_to_message_id:
        await msg.reply_text("Reply to a user to manage their auth permissions.")
        return None

    reply = await msg.getRepliedMessage()
    if isinstance(reply, types.Error):
        await msg.reply_text(f"⚠️ {reply.message}")
        return None

    if reply.from_id == msg.from_id:
        await msg.reply_text("You can't change your own auth permissions.")
        return None

    if isinstance(reply.sender_id, types.MessageSenderChat):
        await msg.reply_text("You can't modify auth permissions for channels.")
        return None

    return reply


@Client.on_message(filters=Filter.command("auth"))
async def auth(_: Client, msg: types.Message):
    """Grant auth permissions to a user."""
    reply = await _validate_auth_command(msg)
    if not reply:
        return

    user_id = reply.from_id
    chat_id = msg.chat_id

    if user_id in await db.get_auth_users(chat_id):
        await msg.reply_text("User already has auth permissions.")
    else:
        await db.add_auth_user(chat_id, user_id)
        await msg.reply_text("User has been granted auth permissions.")


@Client.on_message(filters=Filter.command("unauth"))
async def un_auth(_: Client, msg: types.Message):
    """Remove auth permissions from a user."""
    reply = await _validate_auth_command(msg)
    if not reply:
        return

    user_id = reply.from_id
    chat_id = msg.chat_id

    if user_id not in await db.get_auth_users(chat_id):
        await msg.reply_text("User does not have auth permissions.")
    else:
        await db.remove_auth_user(chat_id, user_id)
        await msg.reply_text("User's auth permissions have been removed.")


@Client.on_message(filters=Filter.command("authlist"))
async def auth_list(_: Client, msg: types.Message):
    """List all users with auth permissions."""
    chat_id = msg.chat_id
    if chat_id > 0:
        await msg.reply_text("This command can only be used in groups.")
        return

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("Only admins can use this command.")
        return

    auth_users = await db.get_auth_users(chat_id)
    if not auth_users:
        await msg.reply_text("No users have auth permissions.")
        return

    text = "<b>Authorized Users:</b>\n" + "\n".join(
        [f"- <code>{uid}</code>" for uid in auth_users]
    )
    await msg.reply_text(text)


async def _handle_toggle_command(
    msg: types.Message, key: str, label: str, get_func, set_func
):
    """Generic handler for toggle commands.

    This function will check if the command can be used in the current chat,
    if the user is the owner of the chat, and if the argument is valid.

    If the argument is invalid or not given, it will send a message explaining
    how to use the command. If the argument is valid, it will toggle the
    corresponding setting in the database and send a confirmation message.

    Parameters
    ----------
    msg : types.Message
        The message that triggered this command.
    key : str
        The name of the setting to toggle.
    label : str
        A human-readable label for the setting.
    get_func : callable
        A function that takes a chat ID and returns the current value of the
        setting.
    set_func : callable
        A function that takes a chat ID and a boolean value and sets the setting
        to that value.
    """
    chat_id = msg.chat_id
    if chat_id > 0:
        await msg.reply_text("This command can only be used in supergroups.")
        return

    if not await is_owner(chat_id, msg.from_id):
        await msg.reply_text("Only group owner can use this command.")
        return

    current = await get_func(chat_id)
    args = extract_argument(msg.text)
    if not args:
        status = "enabled ✅" if current else "disabled ❌"
        await msg.reply_text(
            f"⚙️ {label} is currently {status}.\n\nUse /{key} [on/off] to change it."
        )
        return

    arg = args.lower()
    if arg in ["on", "enable"]:
        await set_func(chat_id, True)
        await msg.reply_text(f"{label} has been enabled ✅.")
    elif arg in ["off", "disable"]:
        await set_func(chat_id, False)
        await msg.reply_text(f"{label} has been disabled ❌.")
    else:
        await msg.reply_text(f"⚠️ Invalid usage.\nUse /{key} [enable|disable|on|off]")


@Client.on_message(filters=Filter.command("buttons"))
async def buttons(_: Client, msg: types.Message):
    """Toggle button control."""
    await _handle_toggle_command(
        msg, "buttons", "Button control", db.get_buttons_status, db.set_buttons_status
    )


@Client.on_message(filters=Filter.command(["thumbnail", "thumb"]))
async def thumbnail(_: Client, msg: types.Message):
    """Toggle thumbnail."""
    await _handle_toggle_command(
        msg, "thumbnail", "Thumbnail", db.get_thumb_status, db.set_thumb_status
    )
