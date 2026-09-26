import os


bind = os.getenv(
    "PAI_GUNICORN_BIND",
    "127.0.0.1:8000",
)

worker_class = "gthread"
workers = 1
threads = 4
timeout = 300
graceful_timeout = 30
keepalive = 5
accesslog = None
errorlog = "-"
capture_output = True
