FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv==0.7.0

COPY . /app/

RUN uv pip install -e . --system

CMD ["tgmusic"]
