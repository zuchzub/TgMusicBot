#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from TgMusic import client
import asyncio
import signal


def handle_shutdown():
    client.logger.info("Shutting down...")
    asyncio.create_task(shutdown())


async def shutdown():
    if client.is_running:
        await client.stop_task()
    tasks = [t for t in asyncio.all_tasks() if t is not asyncio.current_task()]
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    client.loop.stop()


def main() -> None:
    client.logger.info("Starting TgMusicBot...")

    # Set up signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        client.loop.add_signal_handler(sig, handle_shutdown)

    try:
        client.loop.run_until_complete(client.initialize_components())
        client.run()
    except Exception as e:
        client.logger.critical(f"Fatal error: {e}", exc_info=True)
    finally:
        if not client.loop.is_closed():
            client.loop.run_until_complete(shutdown())
        client.loop.close()


if __name__ == "__main__":
    main()
