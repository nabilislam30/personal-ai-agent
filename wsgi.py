import logging

from agent import preload_model
from config import (
    PRELOAD_MODEL,
    WEB_HOST,
)
from observability import configure_logging
from security import (
    validate_security_configuration,
)
from web_app import app


configure_logging()
logger = logging.getLogger(
    "personal_ai_agent.wsgi"
)

validate_security_configuration(
    WEB_HOST
)

if PRELOAD_MODEL:
    logger.info(
        preload_model(),
        extra={
            "event": "model_preload",
        },
    )
