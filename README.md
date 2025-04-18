# [TgMusicBot](https://github.com/AshokShau/TgMusicBot) - Telegram Music Bot

Telegram Group Calls Streaming bot with some useful features, written in Python with Py-Tgcalls.
Supporting platforms like YouTube, Spotify, Apple Music, Soundcloud, JioSaavn and more.

<p align="center">
   <img src="https://raw.githubusercontent.com/AshokShau/TgMusicBot/master/.github/images/thumb.png" alt="thumbnail" width="320" height="320">
</p>

### [@FallenBeatzBot](https://t.me/FallenBeatzBot) - Try it now!

---

### 🚫 Tired of IP Bans from YouTube?

Say goodbye to restrictions with our **Premium Music API** – your ultimate solution for seamless, high-quality
downloads.

- **Easy Integration** – Just set `API_URL` in your bot configuration.
- **High-Quality Downloads** – Get music from **Spotify, Apple Music, SoundCloud**, and **YouTube** in top quality.
- **Unlimited Access** – No limits, no interruptions – download as much as you want.

[➡️ Click here for more details](https://gist.github.com/AshokShau/7528cddc5b264035dee40523a44ff153)

📩 **[Contact me on Telegram](https://t.me/AshokShau) to get access!**

---

### Want to use cookies?

> 📘 Check out this [guide](https://github.com/AshokShau/TgMusicBot/blob/master/cookies/README.md) for instructions on
> downloading and using them.

---

## **Features**

- **Multi-Platform Support** - Play music
  from [Spotify](https://open.spotify.com), [YT-Music](https://music.youtube.com), [YouTube](https://www.youtube.com), [JioSaavn](https://jiosaavn.com), [Apple Music](https://music.apple.com), [SoundCloud](https://soundcloud.com)
  and Telegram files.
- **Playlists & Queue** - Seamless music playback with queue management.
- **Full Playback Controls** - Skip, Pause, Resume, End, Mute, Unmute, Volume, Loop, Seek.
- **Group Voice Chats** - Supports Telegram **group voice chats** (requires admin permissions).
- **Optimized Performance** - Fully **async**, efficient, and lightweight.
- **Easy Deployment** - Pre-configured **Docker** setup.
- **Open-Source & Free** - Built from scratch using **[PyTdBot](https://github.com/pytdbot/client)** & **[PyTgCalls](https://github.com/pytgcalls/pytgcalls)**.
  > 💡 Prefer using Pyrogram instead of PyTdBot? Check out
  the [Pyro-Branch](https://github.com/AshokShau/TgMusicBot/tree/pyro).

---

## **Installation**

<details> 
<summary>Dependencies Tree: Click to expand</summary>

```
tgmusicbot v1.1.7
├── aiofiles v24.1.0
├── apscheduler v3.11.0
│   └── tzlocal v5.3.1
├── cachetools v5.5.2
├── kurigram v2.2.0
│   ├── pyaes v1.6.1
│   └── pysocks v1.7.1
├── meval v2.5
├── motor v3.7.0
│   └── pymongo v4.12.0
│       └── dnspython v2.7.0
├── mutagen v1.47.0
├── ntgcalls v1.3.3
├── pillow v11.2.1
├── psutil v7.0.0
├── py-tgcalls v2.1.1
│   ├── aiohttp v3.11.16
│   │   ├── aiohappyeyeballs v2.6.1
│   │   ├── aiosignal v1.3.2
│   │   │   └── frozenlist v1.6.0
│   │   ├── attrs v25.3.0
│   │   ├── frozenlist v1.6.0
│   │   ├── multidict v6.4.3
│   │   ├── propcache v0.3.1
│   │   └── yarl v1.20.0
│   │       ├── idna v3.10
│   │       ├── multidict v6.4.3
│   │       └── propcache v0.3.1
│   ├── deprecation v2.1.0
│   │   └── packaging v24.2
│   └── ntgcalls v1.3.3
├── py-yt-search v0.2
│   └── httpx v0.28.1
│       ├── anyio v4.9.0
│       │   ├── idna v3.10
│       │   └── sniffio v1.3.1
│       ├── certifi v2025.1.31
│       ├── httpcore v1.0.8
│       │   ├── certifi v2025.1.31
│       │   └── h11 v0.14.0
│       └── idna v3.10
├── pycryptodome v3.22.0
├── pydantic v2.11.3
│   ├── annotated-types v0.7.0
│   ├── pydantic-core v2.33.1
│   │   └── typing-extensions v4.13.2
│   ├── typing-extensions v4.13.2
│   └── typing-inspection v0.4.0
│       └── typing-extensions v4.13.2
├── pytdbot v0.9.2
│   ├── aio-pika v9.5.5
│   │   ├── aiormq v6.8.1
│   │   │   ├── pamqp v3.3.0
│   │   │   └── yarl v1.20.0 (*)
│   │   ├── exceptiongroup v1.2.2
│   │   └── yarl v1.20.0 (*)
│   └── deepdiff v8.4.2
│       └── orderly-set v5.4.0
├── pytgcrypto v1.2.9.2
├── python-dotenv v1.1.0
├── pytz v2025.2
├── tdjson v1.8.47
├── ujson v5.10.0
└── yt-dlp v2025.3.31
```

</details>

<details>
<summary><strong>📌 Using Docker (Recommended) (Click to expand)</strong></summary>

> Check [here](https://docs.docker.com/get-docker/) for installation instructions.

1. Clone the repository:
   ```sh
   git clone https://github.com/AshokShau/TgMusicBot.git && cd TgMusicBot
   ```
2. Build the Docker image:
   ```sh
   docker build -t tgmusicbot .
   ```
3. Set up environment variables:
   ```sh
   cp sample.env .env && vi .env
   ```
4. Run the Docker container:
   ```sh
   docker run -d --name tgmusicbot --env-file .env tgmusicbot
   ```

</details>

<details>
<summary><strong>📌 Manual Installation (Click to expand)</strong></summary>

1.Update and Upgrade your system:

   ```sh
   sudo apt-get update && sudo apt-get upgrade -y
   ```

2.Install tmux to keep running your bot when you close the terminal by:

   ```sh
   sudo apt install tmux && tmux
   ```

3.Install required packages:

   ```sh
   sudo apt-get install git python3-pip ffmpeg -y && pip3 install uv
   ```

4.Clone the repository:

   ```sh
   git clone https://github.com/AshokShau/TgMusicBot.git && cd TgMusicBot
   ```

5.Create a virtual environment:

   ```sh
   uv venv
   ```

6.Activate the virtual environment:

- Windows: `.venv/Scripts/activate`
- Linux/Mac: `source .venv/bin/activate`

7.Install dependencies:

   ```sh
   uv pip install -e .
   ```

8.Set up environment variables:

   ```sh
   cp sample.env .env && vi .env
   ```

> Press `Ctrl+C` when you're done with editing env and `:wq` to save the environment variables.

9.Finally, run the bot by:

   ```sh
   tgmusicbot
   ```

> For getting out from tmux session: Press `Ctrl+b` and then `d`.

</details>

<details>
  <summary><strong>Deploy on Heroku (<small>Click to expand</small>)</strong></summary>
  <p align="center">
    <a href="https://heroku.com/deploy?template=https://github.com/AshokShau/TgMusicBot">
      <img src="https://img.shields.io/badge/Deploy%20On%20Heroku-black?style=for-the-badge&logo=heroku" width="220" height="38.45" alt="Deploy">
    </a>
  </p>
</details>

---

## **Configuration**

<details>
<summary><strong>📌 Environment Variables (<small>Click to expand</small>)</strong></summary>

### 🔑 Required Variables

- **API_ID** – Get from [my.telegram.org](https://my.telegram.org/apps)
- **API_HASH** – Get from [my.telegram.org](https://my.telegram.org/apps)
- **TOKEN** – Get from [@BotFather](https://t.me/BotFather)

### 🔗 String Sessions

- **STRING** - Pyrogram String Session, STRING2 ... STRING10

> Get from [@StringFatherBot](https://t.me/StringFatherBot)

### 🛠️ Additional Configuration

- **OWNER_ID** – Your Telegram User ID
- **MONGO_URI** – Get from [MongoDB Cloud](https://cloud.mongodb.com)
- **API_URL** – Buy from [@AshokShau](https://t.me/AshokShau) (Spotify API for unlimited downloads)
- **API_KEY** – Required for API_URL
- **DOWNLOADS_DIR** – Directory for downloads and TDLib database
- **SUPPORT_GROUP** – Support Group Link
- **SUPPORT_CHANNEL** – Support Channel Link
- **IGNORE_BACKGROUND_UPDATES** – Ignore background updates

### 🎵 Music Download Options

- **PROXY_URL** – Optional; Proxy URL for yt-dlp
- **DEFAULT_SERVICE** – Default search platform (Options: `youtube`, `spotify`, `jiosaavn`)
- **DOWNLOADS_DIR** – Directory for downloads and TDLib database

### 🍪 Cookies

- **COOKIES_URL** – URLs for downloading cookies (More
  info [here](https://github.com/AshokShau/TgMusicBot/blob/master/cookies/README.md))

</details>

---

## **🎮 Usage**

1. **Add [@FallenBeatzBot](https://t.me/FallenBeatzBot) to a group** and grant **admin permissions**.
2. Use `/start` to **initialize** the bot.
3. Use `/help` to view the **list of available commands**.

---

## **Contributing**

Contributions are welcome! If you'd like to contribute:

1. **Fork** the [repository](https://github.com/AshokShau/TgMusicBot).
2. **Make meaningful changes** – improve features, fix bugs, or optimize performance.
3. **Submit a pull request** with a clear explanation of your changes.

🔹 _Avoid submitting minor PRs for small typos or README tweaks unless they significantly improve clarity._

---

## **License**

This project is licensed under the **AGPL-3.0 License**. See the [LICENSE](/LICENSE) file for details.

---

## **Credits**

- [AshokShau](https://github.com/AshokShau) - Creator & Maintainer
- Thanks to **all contributors & bug hunters** for improving the project!
- Special thanks to **[PyTgCalls](https://github.com/pytgcalls)** for their outstanding work.

---

## **💖 Support the Project**

Love **TgMusicBot**? Help keep it running!

💰 **Donate via Crypto, PayPal, or UPI** – [Contact me on Telegram](https://t.me/AshokShau) for details.

Every contribution helps! ❤️

---

## **🔗 Links**

> **Follow** me on [GitHub](https://github.com/AshokShau) for updates.  
> **Star** the repository on [GitHub](https://github.com/AshokShau/TgMusicBot) to support the project.

📢 **Join our Telegram community:**  
[![Telegram Group](https://img.shields.io/badge/Telegram%20Group-Join%20Now-blue?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/GuardxSupport)  
[![Telegram Channel](https://img.shields.io/badge/Telegram%20Channel-Join%20Now-blue?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/FallenProjects)

---
