FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN useradd \
    --create-home \
    --uid 10001 \
    agent

COPY requirements.txt .

RUN python -m pip install \
    --upgrade pip \
    && python -m pip install \
    -r requirements.txt

COPY . .

RUN mkdir -p \
    /data/workspace \
    /data/knowledge \
    && chown -R agent:agent \
    /app \
    /data

USER agent

EXPOSE 8000

CMD [
    "gunicorn",
    "--config",
    "gunicorn.conf.py",
    "wsgi:app"
]
