#  Copyright (c) 2025 AshokShau
#  Licensed under the GNU AGPL v3.0: https://www.gnu.org/licenses/agpl-3.0.html
#  Part of the TgMusicBot project. All rights reserved where applicable.

from TgMusic import client


def main() -> None:
    client.logger.info("Starting TgMusicBot...")
    client.run()


if __name__ == "__main__":
    main()
