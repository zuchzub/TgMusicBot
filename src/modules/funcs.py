#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

import re
from typing import Union

from pytdbot import Client, types

from src.helpers import MusicServiceWrapper, call, db, get_string
from src.helpers import chat_cache
from src.logger import LOGGER
from src.modules.play import _get_platform_url, play_music
from src.modules.progress_handler import _handle_play_c_data
from src.modules.utils import Filter, PauseButton, ResumeButton, sec_to_min
from src.modules.utils.admins import is_admin
from src.modules.utils.play_helpers import del_msg, edit_text, extract_argument


async def is_admin_or_reply(msg: types.Message) -> Union[int, types.Message]:
    """
    Check if user is admin and if a song is playing.
    """
    chat_id = msg.chat_id
    lang = await db.get_lang(chat_id)
    if not chat_cache.is_active(chat_id):
        return await msg.reply_text(text=get_string("no_song_playing", lang))

    if not await is_admin(chat_id, msg.from_id):
        return await msg.reply_text(text=get_string("admin_required", lang))

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
    lang = await db.get_lang(chat_id)
    done = await action(chat_id)
    if isinstance(done, types.Error):
        await msg.reply_text(f"⚠️ {fail_msg}\n\n{done.message}")
        return

    await msg.reply_text(
        f"{success_msg}\n│ \n{get_string('requested_by', lang)}: {await msg.mention()} 🥀"
    )
    return


@Client.on_message(filters=Filter.command(["playtype", "setPlayType"]))
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
    lang = await db.get_lang(chat_id)
    if chat_id > 0:
        return

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text(get_string("admin_required", lang))
        return

    play_type = extract_argument(msg.text, enforce_digit=True)
    if not play_type:
        await msg.reply_text(get_string("set_play_type_usage", lang))
        return

    play_type = int(play_type)
    if play_type not in (0, 1):
        await msg.reply_text(get_string("invalid_play_type", lang))
        return

    await db.set_play_type(chat_id, play_type)
    await msg.reply_text(get_string("play_type_set", lang).format(play_type))


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
        short_text += f"\n\n<b>» Total of {
        len(_queue)} track(s) in the queue.</b>"
        text = short_text
    await msg.reply_text(text, disable_web_page_preview=True)


@Client.on_message(filters=Filter.command("loop"))
async def modify_loop(c: Client, msg: types.Message) -> None:
    """
    Modify the loop count for the current song.
    """
    chat_id = msg.chat_id
    lang = await db.get_lang(chat_id)
    if chat_id > 0:
        return None

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text(get_string("admin_required", lang))
        return None

    if not chat_cache.is_active(chat_id):
        await msg.reply_text(get_string("no_song_playing", lang))
        return None

    args = extract_argument(msg.text, enforce_digit=True)
    if not args:
        await msg.reply_text(get_string("loop_usage", lang))
        return None

    loop = int(args)
    chat_cache.set_loop_count(chat_id, loop)
    action = get_string("loop_disabled" if loop == 0 else "loop_changed", lang).format(
        loop
    )
    reply = await msg.reply_text(
        get_string("loop_reply", lang).format(action, await msg.mention())
    )
    if isinstance(reply, types.Error):
        c.logger.warning(f"Error sending reply: {reply.message}")
    return None


@Client.on_message(filters=Filter.command("seek"))
async def seek_song(c: Client, msg: types.Message) -> None:
    """
    Seek to a specific time in the current song.
    """
    chat_id = msg.chat_id
    lang = await db.get_lang(chat_id)
    if chat_id > 0:
        return

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text(get_string("admin_required", lang))
        return

    args = extract_argument(msg.text, enforce_digit=True)
    if not args:
        await msg.reply_text(get_string("seek_usage", lang))
        return

    seek_time = int(args)
    if seek_time < 20:
        await msg.reply_text(get_string("seek_invalid", lang))
        return

    curr_song = chat_cache.get_current_song(chat_id)
    if not curr_song:
        await msg.reply_text(get_string("no_song_playing", lang))
        return

    curr_dur = await call.played_time(chat_id)
    if isinstance(curr_dur, types.Error):
        await msg.reply_text(curr_dur.message)
        return

    seek_to = curr_dur + seek_time
    if seek_to >= curr_song.duration:
        await msg.reply_text(
            get_string("seek_error_duration", lang).format(
                sec_to_min(curr_song.duration)
            )
        )
        return

    _seek = await call.seek_stream(
        chat_id,
        curr_song.file_path,
        seek_to,
        curr_song.duration,
        curr_song.is_video,
    )
    if isinstance(_seek, types.Error):
        await msg.reply_text(_seek.message)
        return

    await msg.reply_text(
        get_string("seek_success", lang).format(seek_to, await msg.mention())
    )
    return


def extract_number(text: str) -> float | None:
    match = re.search(r"[-+]?\d*\.?\d+", text)
    return float(match.group()) if match else None


@Client.on_message(filters=Filter.command("speed"))
async def change_speed(_: Client, msg: types.Message) -> None:
    """
    Change the playback speed of the current song.
    """
    chat_id = msg.chat_id
    lang = await db.get_lang(chat_id)
    if chat_id > 0:
        return

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text(get_string("admin_required", lang))
        return

    args = extract_number(msg.text)
    if args is None:
        await msg.reply_text(get_string("speed_usage", lang))
        return

    if not chat_cache.is_active(chat_id):
        await msg.reply_text(get_string("no_song_playing", lang))
        return

    speed = round(float(args), 2)
    _change_speed = await call.speed_change(chat_id, speed)
    if isinstance(_change_speed, types.Error):
        await msg.reply_text(_change_speed.message)
        return

    await msg.reply_text(
        get_string("speed_changed", lang).format(speed, await msg.mention())
    )
    return


@Client.on_message(filters=Filter.command("remove"))
async def remove_song(c: Client, msg: types.Message) -> None:
    """Remove a track from the queue."""
    chat_id = msg.chat_id
    lang = await db.get_lang(chat_id)
    if chat_id > 0:
        return None

    args = extract_argument(msg.text, enforce_digit=True)
    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text(get_string("admin_required", lang))
        return None

    if not chat_cache.is_active(chat_id):
        await msg.reply_text(get_string("no_song_playing", lang))
        return None

    if not args:
        await msg.reply_text(get_string("remove_usage", lang))
        return None

    track_num = int(args)
    _queue = chat_cache.get_queue(chat_id)

    if not _queue:
        await msg.reply_text(get_string("empty_queue", lang))
        return None

    if track_num <= 0 or track_num > len(_queue):
        await msg.reply_text(
            get_string("invalid_track_number", lang).format(len(_queue))
        )
        return None

    chat_cache.remove_track(chat_id, track_num)
    reply = await msg.reply_text(
        get_string("track_removed", lang).format(await msg.mention())
    )
    if isinstance(reply, types.Error):
        c.logger.warning(f"Error sending reply: {reply}")
    return None


@Client.on_message(filters=Filter.command("clear"))
async def clear_queue(c: Client, msg: types.Message) -> None:
    """
    Clear the queue.
    """
    chat_id = msg.chat_id
    lang = await db.get_lang(chat_id)
    if chat_id > 0:
        return None

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text(get_string("admin_required", lang))
        return None

    if not chat_cache.is_active(chat_id):
        await msg.reply_text(get_string("no_song_playing", lang))
        return None

    if not chat_cache.get_queue(chat_id):
        await msg.reply_text(get_string("empty_queue", lang))
        return None

    chat_cache.clear_chat(chat_id)
    reply = await msg.reply_text(
        get_string("queue_cleared", lang).format(await msg.mention())
    )
    if isinstance(reply, types.Error):
        c.logger.warning(f"Error sending reply: {reply}")
    return None


@Client.on_message(filters=Filter.command(["stop", "end"]))
async def stop_song(_: Client, msg: types.Message) -> None:
    """
    Stop the current song.
    """
    chat_id = await is_admin_or_reply(msg)
    if isinstance(chat_id, types.Message):
        return

    lang = await db.get_lang(chat_id)

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text(get_string("admin_required", lang))
        return

    _end = await call.end(chat_id)
    if isinstance(_end, types.Error):
        await msg.reply_text(_end.message)
        return

    await msg.reply_text(get_string("stream_ended", lang).format(await msg.mention()))
    return


@Client.on_message(filters=Filter.command("pause"))
async def pause_song(_: Client, msg: types.Message) -> None:
    """Pause the current song."""
    lang = await db.get_lang(msg.chat_id)
    await handle_playback_action(
        _,
        msg,
        call.pause,
        get_string("stream_paused", lang),
        get_string("pause_error", lang),
    )


@Client.on_message(filters=Filter.command("resume"))
async def resume(_: Client, msg: types.Message) -> None:
    """Resume the current song."""
    lang = await db.get_lang(msg.chat_id)
    await handle_playback_action(
        _,
        msg,
        call.resume,
        get_string("stream_resumed", lang),
        get_string("resume_error", lang),
    )


@Client.on_message(filters=Filter.command("mute"))
async def mute_song(_: Client, msg: types.Message) -> None:
    """Mute the current song."""
    lang = await db.get_lang(msg.chat_id)
    await handle_playback_action(
        _,
        msg,
        call.mute,
        get_string("stream_muted", lang),
        get_string("mute_error", lang),
    )


@Client.on_message(filters=Filter.command("unmute"))
async def unmute_song(_: Client, msg: types.Message) -> None:
    """Unmute the current song."""
    lang = await db.get_lang(msg.chat_id)
    await handle_playback_action(
        _,
        msg,
        call.unmute,
        get_string("stream_unmuted", lang),
        get_string("unmute_error", lang),
    )


@Client.on_message(filters=Filter.command("volume"))
async def volume(_: Client, msg: types.Message) -> None:
    """
    Change the volume of the current song.
    """
    chat_id = await is_admin_or_reply(msg)
    if isinstance(chat_id, types.Message):
        return None

    lang = await db.get_lang(chat_id)

    if not await is_admin(chat_id, msg.from_id):
        await msg.reply_text(get_string("admin_required", lang))
        return None

    args = extract_argument(msg.text, enforce_digit=True)
    if not args:
        await msg.reply_text(get_string("volume_usage", lang))
        return None

    vol_int = int(args)
    if vol_int == 0:
        await msg.reply_text(get_string("mute_usage", lang))
        return None

    if not 1 <= vol_int <= 200:
        await msg.reply_text(get_string("volume_range_error", lang))
        return None

    done = await call.change_volume(chat_id, vol_int)
    if isinstance(done, types.Error):
        await msg.reply_text(done.message)
        return None

    await msg.reply_text(
        get_string("volume_set", lang).format(vol_int, await msg.mention())
    )
    return None


@Client.on_message(filters=Filter.command("skip"))
async def skip_song(c: Client, msg: types.Message) -> None:
    """
    Skip the current song.
    """
    chat_id = await is_admin_or_reply(msg)
    if isinstance(chat_id, types.Message):
        return None

    lang = await db.get_lang(chat_id)
    await del_msg(msg)

    done = await call.play_next(chat_id)
    if isinstance(done, types.Error):
        await msg.reply_text(
            f"⚠️ {get_string('error_occurred', lang)}\n\n{done.message}"
        )
        return None

    reply = await msg.reply_text(
        f"⏭️ {get_string('song_skipped', lang)}\n│ \n└ {get_string('requested_by', lang)}: {await msg.mention()} 🥀"
    )
    if isinstance(reply, types.Error):
        c.logger.warning(f"Error sending reply: {reply}")

    return None


@Client.on_updateNewCallbackQuery(filters=Filter.regex(r"play_\w+"))
async def callback_query(c: Client, message: types.UpdateNewCallbackQuery) -> None:
    """Handle all play control callback queries (skip, stop, pause, resume, timer)."""
    chat_id = message.chat_id
    lang = await db.get_lang(chat_id)
    try:
        data = message.payload.data.decode()
        user_id = message.sender_user_id
        get_msg = await message.getMessage()
        if isinstance(get_msg, types.Error):
            LOGGER.warning("Error getting message: %s", get_msg.message)
            return None

        user = await c.getUser(user_id)
        if isinstance(user, types.Error):
            LOGGER.warning("Error getting user: %s", user.message)
            return None
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
                f"⚠️ {get_string('admin_required', lang)}", show_alert=True
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
                f"❌ {get_string('no_active_chat', lang)}", alert=True
            )

        if data == "play_skip":
            done = await call.play_next(chat_id)
            if isinstance(done, types.Error):
                await send_response(
                    f"⚠️ {get_string('error_occurred', lang)}\n\n{done.message}",
                    alert=True,
                )
                return None
            await send_response(get_string("song_skipped", lang), delete=True)
            return None
        elif data == "play_stop":
            done = await call.end(chat_id)
            if isinstance(done, types.Error):
                await send_response(done.message, alert=True)
                return None
            await send_response(
                f"<b>➻ {get_string('stream_stopped', lang)}:</b>\n└ {get_string('requested_by', lang)}: {user_name}"
            )
            return None
        elif data == "play_pause":
            done = await call.pause(chat_id)
            if isinstance(done, types.Error):
                await send_response(
                    f"⚠️ {get_string('error_occurred', lang)}\n\n{done.message}",
                    alert=True,
                )
                return None
            await send_response(
                f"<b>➻ {get_string('stream_paused', lang)}:</b>\n└ {get_string('requested_by', lang)}: {user_name}",
                markup=(PauseButton if await db.get_buttons_status(chat_id) else None),
            )
            return None
        elif data == "play_resume":
            done = await call.resume(chat_id)
            if isinstance(done, types.Error):
                await send_response(f"{done.message}", alert=True)
                return None
            await send_response(
                f"<b>➻ {get_string('stream_resumed', lang)}:</b>\n└ {get_string('requested_by', lang)}: {user_name}",
                markup=(ResumeButton if await db.get_buttons_status(chat_id) else None),
            )
            return None
        elif data == "play_close":
            _delete = await c.deleteMessages(chat_id, [message.message_id], revoke=True)
            if isinstance(_delete, types.Error):
                await message.answer(
                    f"Failed to close {_delete.message}", show_alert=True
                )
                return None
            await message.answer(get_string("closed", lang), show_alert=True)
            return None
        elif data.startswith("play_c_"):
            await _handle_play_c_data(data, message, chat_id, user_id, user_name, c)
            return None
        else:
            try:
                _, platform, song_id = data.split("_", 2)
            except ValueError:
                LOGGER.error(f"Invalid callback data format: {data}")
                await send_response(
                    get_string("invalid_request_format", lang), alert=True
                )
                return None

            await message.answer(
                text=f"{get_string('playing_song', lang)} {user_name}", show_alert=True
            )
            reply_message = await message.edit_message_text(
                f"🎶 {get_string('searching', lang)} ...\n{get_string('requested_by', lang)}: {user_name} 🥀"
            )
            if isinstance(reply_message, types.Error):
                c.logger.warning(f"Error sending reply: {reply_message}")
                return None

            url = _get_platform_url(platform, song_id)
            if not url:
                LOGGER.error(f"Invalid platform: {platform}; data: {data}")
                await edit_text(
                    reply_message,
                    text=f"⚠️ {get_string('invalid_platform', lang)} {platform}",
                )
                return None

            if song := await MusicServiceWrapper(url).get_info():
                return await play_music(c, reply_message, song, user_name)
            await edit_text(reply_message, text=get_string("song_not_found", lang))
            return None
    except Exception as e:
        c.logger.critical(f"Unhandled exception in callback_query: {e}")
        await message.answer(f"⚠️ {get_string('error_occurred', lang)}", show_alert=True)
        return None
