#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import re
from typing import Union

from pytdbot import Client, types

from src.database import db
from src.logger import LOGGER
from src.modules.play import _get_platform_url, play_music
from src.modules.progress_handler import _handle_play_c_data
from src.modules.utils import Filter, PauseButton, ResumeButton, sec_to_min
from src.modules.utils.admins import is_admin
from src.modules.utils.cacher import chat_cache
from src.modules.utils.play_helpers import del_msg, edit_text, extract_argument
from src.platforms.downloader import MusicServiceWrapper
from src.pytgcalls import call


async def is_admin_or_reply(msg: types.Message) -> Union[int, types.Message]:
    """
    Check if user is admin and if a song is playing.
    """
    chat_id = msg.chat_id

    if not chat_cache.is_active(chat_id):
        return await msg.reply_text(text="❌ No song is currently playing.")

    if not await is_admin(chat_id, msg.from_id):
        return await msg.reply_text("You must be an admin to use this command.")

    return chat_id


async def handle_playback_action(
    _: Client, msg: types.Message, action, success_msg: str, fail_msg: str
) -> None:
    """
    Handle playback actions like stop, pause, resume, mute, unmute.
    """
    chat_id = await is_admin_or_reply(msg)
    if isinstance(chat_id, types.Message):
        return

    try:
        await action(chat_id)
        await msg.reply_text(
            f"{success_msg}\n│ \n└ Requested by: {await msg.mention()} 🥀"
        )
    except Exception as e:
        LOGGER.error("Error in %s: %s", action.__name__, e)
        await msg.reply_text(f"⚠️ {fail_msg}\nError: {e}")


@Client.on_message(filters=Filter.command("setPlayType"))
async def set_play_type(_: Client, msg: types.Message) -> None:
    """
    Set the play type for a given chat.

    The play type is a preference for a given chat that determines how the
    bot should handle song requests. If the preference is 0, the bot will
    immediately play the first search result. If the preference is 1, the
    bot will send a list of songs to choose from.

    Returns
    -------
    None
    """
    chat_id = msg.chat_id
    if chat_id > 0:
        return

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("You must be an admin to use this command.")
        return

    play_type = extract_argument(msg.text, enforce_digit=True)
    if not play_type:
        await msg.reply_text(
            text="Usage: /setPlayType 0/1\n\n0 = Directly play the first search result.\n1 = Show a list of songs to choose from."
        )
        return

    play_type = int(play_type)
    if play_type not in (0, 1):
        await msg.reply_text("Invalid option! Please use: /setPlayType 0/1")
        return

    try:
        await db.set_play_type(chat_id, play_type)
        await msg.reply_text(f"✅ Play type set to {play_type}")
    except Exception as e:
        LOGGER.error("Error setting play type: %s", e)
        await msg.reply_text("⚠️ Failed to set play type. Please try again.")


@Client.on_message(filters=Filter.command("queue"))
async def queue_info(_: Client, msg: types.Message) -> None:
    """
    Display information about the current queue.
    """
    if msg.chat_id > 0:
        return

    chat_id = msg.chat_id
    _queue = chat_cache.get_queue(chat_id)
    if not _queue:
        await msg.reply_text(text="🛑 The queue is empty. No tracks left to play!")
        return

    if not chat_cache.is_active(chat_id):
        await msg.reply_text(text="❌ No song is currently playing in this chat!")
        return

    chat: types.Chat = await msg.getChat()
    current_song = _queue[0]
    text = (
        f"<b>🎶 Current Queue in {chat.title}:</b>\n\n"
        f"<b>Currently Playing:</b>\n"
        f"‣ <b>{current_song.name[:30]}</b>\n"
        f"   ├ <b>By:</b> {current_song.user}\n"
        f"   ├ <b>Duration:</b> {sec_to_min(current_song.duration)} minutes\n"
        f"   ├ <b>Loop:</b> {current_song.loop}\n"
        f"   └ <b>Played Time:</b> {sec_to_min(await call.played_time(chat.id))} min"
    )

    if queue_remaining := _queue[1:]:
        text += "\n<b>⏭ Next in Queue:</b>\n"
        for i, song in enumerate(queue_remaining, start=1):
            text += (
                f"{i}. <b>{song.name[:30]}</b>\n"
                f"   ├ <b>Duration:</b> {sec_to_min(song.duration)} min\n"
            )

    text += f"\n<b>» Total of {len(_queue)} track(s) in the queue.</b>"
    if len(text) > 4096:
        short_text = f"<b>🎶 Current Queue in {chat.title}:</b>\n\n"
        short_text += "<b>Currently Playing:</b>\n"
        short_text += f"‣ <b>{current_song.name[:30]}</b>\n"
        short_text += f"   ├ <b>By:</b> {current_song.user}\n"
        short_text += (
            f"   ├ <b>Duration:</b> {sec_to_min(current_song.duration)} minutes\n"
        )
        short_text += f"   ├ <b>Loop:</b> {current_song.loop}\n"
        short_text += f"   └ <b>Played Time:</b> {sec_to_min(await call.played_time(chat.id))} min"
        short_text += f"\n\n<b>» Total of {len(_queue)} track(s) in the queue.</b>"
        text = short_text
    await msg.reply_text(text, disable_web_page_preview=True)


@Client.on_message(filters=Filter.command("loop"))
async def modify_loop(_: Client, msg: types.Message) -> None:
    """
    Modify the loop count for the current song.
    """
    chat_id = msg.chat_id
    if chat_id > 0:
        return None

    args = extract_argument(msg.text, enforce_digit=True)
    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("You need to be an admin to use this command")
        return None

    if not chat_cache.is_active(chat_id):
        await msg.reply_text("❌ No song is currently playing in this chat!")
        return None

    if not args:
        await msg.reply_text(
            "🛑 Usage: /loop times\n\nExample: /loop 5 will loop the current song 5 times or 0 to disable"
        )
        return None

    loop = int(args)
    try:
        chat_cache.set_loop_count(chat_id, loop)
        action = "disabled" if loop == 0 else f"changed to {loop} times"
        await msg.reply_text(f"🔄 Loop {action}\n│ \n└ Action by: {msg.mention()}")
        return None
    except Exception as e:
        LOGGER.error("Error setting loop: %s", e)
        await msg.reply_text(f"⚠️ Something went wrong...\n\nError: {str(e)}")
        return None


@Client.on_message(filters=Filter.command("seek"))
async def seek_song(_: Client, msg: types.Message) -> None:
    """
    Seek to a specific time in the current song.
    """
    chat_id = msg.chat_id
    if chat_id > 0:
        return

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("You must be an admin to use this command.")
        return

    args = extract_argument(msg.text, enforce_digit=True)
    if not args:
        await msg.reply_text(
            "🛑 Usage: /seek seconds (must be a number greater than 20)"
        )
        return

    seek_time = int(args)
    if seek_time < 20:
        await msg.reply_text("🛑 Invalid input! Seconds must be greater than 20.")
        return

    curr_song = chat_cache.get_current_song(chat_id)
    if not curr_song:
        await msg.reply_text("❌ No song is currently playing in this chat!")
        return

    curr_dur = await call.played_time(chat_id)
    seek_to = curr_dur + seek_time

    if seek_to >= curr_song.duration:
        await msg.reply_text(
            f"🛑 Cannot seek past the song duration ({sec_to_min(curr_song.duration)} min)."
        )
        return

    try:
        await call.seek_stream(
            chat_id,
            curr_song.file_path,
            seek_to,
            curr_song.duration,
            curr_song.is_video,
        )
        await msg.reply_text(
            f"⏩ Seeked to {seek_to} seconds\n│ \n└ Action by: {await msg.mention()}"
        )
    except Exception as e:
        LOGGER.error("Error seeking song: %s", e)
        await msg.reply_text(f"⚠️ Something went wrong...\n\nError: {str(e)}")


def extract_number(text: str) -> float | None:
    match = re.search(r"[-+]?\d*\.?\d+", text)
    return float(match.group()) if match else None


@Client.on_message(filters=Filter.command("speed"))
async def change_speed(_: Client, msg: types.Message) -> None:
    """
    Change the playback speed of the current song.
    """
    chat_id = msg.chat_id
    if chat_id > 0:
        return

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("You must be an admin to use this command.")
        return

    args = extract_number(msg.text)
    if args is None:
        await msg.reply_text(
            "🛑 Usage: /speed speed (must be a number between 0.5 and 4.0)"
        )
        return

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("You need to be an admin to use this command")
        return

    if not chat_cache.is_active(chat_id):
        await msg.reply_text("❌ No song is currently playing in this chat!")
        return

    speed = round(float(args), 2)
    try:
        await call.speed_change(chat_id, speed)
        await msg.reply_text(
            f"🚀 Speed changed to {speed}\n│ \n└ Action by: {await msg.mention()}"
        )
    except Exception as e:
        LOGGER.error("Error changing speed: %s", e)
        await msg.reply_text(f"⚠️ Something went wrong...\n\nError: {str(e)}")


@Client.on_message(filters=Filter.command("remove"))
async def remove_song(_: Client, msg: types.Message) -> None:
    """
    Remove a track from the queue.
    """
    chat_id = msg.chat_id
    if chat_id > 0:
        return None

    args = extract_argument(msg.text, enforce_digit=True)
    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("You need to be an admin to use this command")
        return None

    if not chat_cache.is_active(chat_id):
        await msg.reply_text("❌ No song is playing in this chat!")
        return None

    if not args:
        await msg.reply_text("🛑 Usage: /remove track number (must be a valid number)")
        return None

    track_num = int(args)
    _queue = chat_cache.get_queue(chat_id)

    if not _queue:
        await msg.reply_text("🛑 The queue is empty. No tracks to remove.")
        return None

    if track_num <= 0 or track_num > len(_queue):
        await msg.reply_text(
            f"🛑 Invalid track number! The current queue has {len(_queue)} tracks."
        )
        return None

    try:
        chat_cache.remove_track(chat_id, track_num)
        await msg.reply_text(
            f"✔️ Track removed from queue\n│ \n└ Removed by: {await msg.mention()}"
        )
        return None
    except Exception as e:
        LOGGER.error("Error removing track: %s", e)
        await msg.reply_text(f"⚠️ Something went wrong...\n\nError: {str(e)}")
        return None


@Client.on_message(filters=Filter.command("clear"))
async def clear_queue(_: Client, msg: types.Message) -> None:
    """
    Clear the queue.
    """
    chat_id = msg.chat_id
    if chat_id > 0:
        return None

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("You need to be an admin to use this command")
        return None

    if not chat_cache.is_active(chat_id):
        await msg.reply_text("❌ No song is currently playing in this chat!")
        return None

    if not chat_cache.get_queue(chat_id):
        await msg.reply_text("🛑 The queue is already empty!")
        return None

    try:
        chat_cache.clear_chat(chat_id)
        await msg.reply_text(f"🗑️ Queue cleared\n│ \n└ Action by: {await msg.mention()}")
        return None
    except Exception as e:
        LOGGER.error("Error clearing queue: %s", e)
        await msg.reply_text(f"⚠️ Something went wrong...\n\nError: {str(e)}")
        return None


@Client.on_message(filters=Filter.command(["stop", "end"]))
async def stop_song(_: Client, msg: types.Message) -> None:
    """
    Stop the current song.
    """
    chat_id = await is_admin_or_reply(msg)
    if isinstance(chat_id, types.Message):
        return

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("You must be an admin to use this command.")
        return

    try:
        await call.end(chat_id)
        await msg.reply_text(
            f"🎵 <b>Stream Ended</b> ❄️\n│ \n└ Requested by: {await msg.mention()} 🥀"
        )
    except Exception as e:
        LOGGER.error("Error stopping song: %s", e)
        await msg.reply_text(f"⚠️ Failed to stop the song.\nError: {str(e)}")


@Client.on_message(filters=Filter.command("pause"))
async def pause_song(_: Client, msg: types.Message) -> None:
    """
    Pause the current song.
    """
    await handle_playback_action(
        _, msg, call.pause, "⏸️ <b>Stream Paused</b> 🥺", "Failed to pause the song"
    )


@Client.on_message(filters=Filter.command("resume"))
async def resume(_: Client, msg: types.Message) -> None:
    """
    Resume the current song.
    """
    await handle_playback_action(
        _, msg, call.resume, "🎶 <b>Stream Resumed</b> 💫", "Failed to resume the song"
    )


@Client.on_message(filters=Filter.command("mute"))
async def mute_song(_: Client, msg: types.Message) -> None:
    """
    Mute the current song.
    """
    await handle_playback_action(
        _, msg, call.mute, "🔇 <b>Stream Muted</b>", "Failed to mute the song"
    )


@Client.on_message(filters=Filter.command("unmute"))
async def unmute_song(_: Client, msg: types.Message) -> None:
    """
    Unmute the current song.
    """
    await handle_playback_action(
        _, msg, call.unmute, "🔊 <b>Stream Unmuted</b>", "Failed to unmute the song"
    )


@Client.on_message(filters=Filter.command("volume"))
async def volume(_: Client, msg: types.Message) -> None:
    """
    Change the volume of the current song.
    """
    chat_id = await is_admin_or_reply(msg)
    if isinstance(chat_id, types.Message):
        return None

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text("You must be an admin to use this command.")
        return None

    args = extract_argument(msg.text, enforce_digit=True)
    if not args:
        await msg.reply_text("⚠️ Usage: /volume 1-200")
        return None

    vol_int = int(args)
    if vol_int == 0:
        await msg.reply_text("🔇 Use /mute to mute the song.")
        return None

    if not 1 <= vol_int <= 200:
        await msg.reply_text(
            "⚠️ Volume must be between 1 and 200.\nUsage: /volume 1-200"
        )
        return None

    try:
        await call.change_volume(chat_id, vol_int)
        await msg.reply_text(
            f"🔊 <b>Stream volume set to {vol_int}</b>\n│ \n└ Requested by: {await msg.mention()} 🥀"
        )
        return None
    except Exception as e:
        LOGGER.error("Error changing volume: %s", e)
        await msg.reply_text(f"⚠️ Failed to change volume.\nError: {e}")
        return None


@Client.on_message(filters=Filter.command("skip"))
async def skip_song(_: Client, msg: types.Message) -> None:
    """
    Skip the current song.
    """
    chat_id = await is_admin_or_reply(msg)
    if isinstance(chat_id, types.Message):
        return None

    try:
        await del_msg(msg)
        await call.play_next(chat_id)
        await msg.reply_text(
            f"⏭️ Song skipped\n│ \n└ Requested by: {await msg.mention()} 🥀"
        )
        return None
    except Exception as e:
        LOGGER.error("Error skipping song: %s", e)
        await msg.reply_text(f"⚠️ Failed to skip the song.\nError: {e}")
        return None


@Client.on_updateNewCallbackQuery(filters=Filter.regex(r"play_\w+"))
async def callback_query(c: Client, message: types.UpdateNewCallbackQuery) -> None:
    """
    Handle all play control callback queries (skip, stop, pause, resume, timer).
    """
    try:
        data = message.payload.data.decode()
        chat_id = message.chat_id
        user_id = message.sender_user_id
        get_msg = await message.getMessage()
        if isinstance(get_msg, types.Error):
            LOGGER.warning("Error getting message: %s", get_msg.message)
            return None

        user = await c.getUser(user_id)
        user_name = user.first_name

        async def send_response(
            msg: str, alert: bool = False, delete: bool = False, markup=None
        ) -> None:
            """
            Helper function to send responses consistently.
            """
            if alert:
                await message.answer(msg, show_alert=True)
            else:
                if get_msg.caption:
                    await message.edit_message_caption(caption=msg, reply_markup=markup)
                else:
                    await message.edit_message_text(text=msg, reply_markup=markup)
            if delete:
                _del = await c.deleteMessages(
                    chat_id, [message.message_id], revoke=True
                )
                if isinstance(_del, types.Error):
                    LOGGER.warning("Error deleting message: %s", _del.message)

        # Check admin permissions for control actions
        def requires_admin(cb_data: str) -> bool:
            """
            Check if the action requires admin privileges.
            """
            return cb_data in {
                "play_skip",
                "play_stop",
                "play_pause",
                "play_resume",
                "play_close",
            }

        if requires_admin(data) and not await is_admin(chat_id, user_id):
            await message.answer(
                "⚠️ You must be an admin to use this command.", show_alert=True
            )
            return None

        # Check if chat is active for control actions
        def requires_active_chat(cb_data: str) -> bool:
            """
            Check if the action requires an active chat session.
            """
            return cb_data in {
                "play_skip",
                "play_stop",
                "play_pause",
                "play_resume",
                "play_timer",
            }

        if requires_active_chat(data) and not chat_cache.is_active(chat_id):
            return await send_response(
                "❌ Nothing is currently playing in this chat.", alert=True
            )

        if data == "play_skip":
            try:
                await call.play_next(chat_id)
                await send_response("⏭️ Song skipped", delete=True)
            except Exception as e:
                LOGGER.error("Could not skip song: %s", e)
                await send_response("⚠️ Error: Next song not found to play.", alert=True)
                return None

        elif data == "play_stop":
            try:
                chat_cache.clear_chat(chat_id)
                await call.end(chat_id)
                await send_response(
                    f"<b>➻ Stream stopped:</b>\n└ Requested by: {user_name}"
                )
            except Exception as e:
                LOGGER.error("Error stopping stream: %s", e)
                await send_response(
                    "⚠️ Error stopping the stream. Please try again.", alert=True
                )
                return None

        elif data == "play_pause":
            try:
                await call.pause(chat_id)
                await send_response(
                    f"<b>➻ Stream paused:</b>\n└ Requested by: {user_name}",
                    markup=(
                        PauseButton if await db.get_buttons_status(chat_id) else None
                    ),
                )
            except Exception as e:
                LOGGER.error("Error pausing stream: %s", e)
                await send_response(
                    "⚠️ Error pausing the stream. Please try again.", alert=True
                )
                return None

        elif data == "play_resume":
            try:
                await call.resume(chat_id)
                await send_response(
                    f"<b>➻ Stream resumed:</b>\n└ Requested by: {user_name}",
                    markup=(
                        ResumeButton if await db.get_buttons_status(chat_id) else None
                    ),
                )
            except Exception as e:
                LOGGER.error("Error resuming stream: %s", e)
                await send_response(
                    "⚠️ Error resuming the stream. Please try again.", alert=True
                )
                return None
        elif data == "play_close":
            _delete = await c.deleteMessages(chat_id, [message.message_id], revoke=True)
            if isinstance(_delete, types.Error):
                await message.answer(
                    f"Failed to close {_delete.message}", show_alert=True
                )
                return None
            await message.answer("Closed !", show_alert=True)
            return None
        elif data.startswith("play_c_"):
            await _handle_play_c_data(data, message, chat_id, user_id, user_name, c)
            return None
        else:
            try:
                _, platform, song_id = data.split("_", 2)
                await message.answer(
                    text=f"Playing song for {user_name}", show_alert=True
                )

                reply_message = await message.edit_message_text(
                    f"🎶 Searching ...\nRequested by: {user_name} 🥀"
                )
                url = _get_platform_url(platform, song_id)
                if not url:
                    await edit_text(
                        reply_message, text=f"⚠️ Error: Invalid Platform {platform}"
                    )
                    return None

                if song := await MusicServiceWrapper(url).get_info():
                    return await play_music(c, reply_message, song, user_name)

                await edit_text(reply_message, text="⚠️ Error: Song not found.")
                return None
            except ValueError:
                LOGGER.error("Invalid callback data format: %s", data)
                await send_response("⚠️ Error: Invalid request format.", alert=True)
                return None
            except Exception as e:
                LOGGER.error("Error handling play request: %s", e)
                await send_response("⚠️ Error processing your request.", alert=True)
                return None
    except Exception as e:
        LOGGER.critical("Unhandled exception in callback_query: %s", e)
        await message.answer(
            "⚠️ An error occurred while processing your request.", show_alert=True
        )
        return None
