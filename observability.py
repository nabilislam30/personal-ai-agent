import json
import logging
import sys
from datetime import datetime, timezone


class JsonFormatter(
    logging.Formatter
):
    """
    Minimal structured formatter that deliberately excludes prompt content.
    """

    def format(
        self,
        record: logging.LogRecord,
    ) -> str:
        payload = {
            "timestamp": (
                datetime.now(
                    timezone.utc
                ).isoformat()
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": (
                record.getMessage()
            ),
        }

        for field in (
            "event",
            "request_id",
            "method",
            "path",
            "status",
            "duration_ms",
            "route_name",
            "tool_calls",
            "first_token_ms",
            "model_ms",
            "total_ms",
        ):
            value = getattr(
                record,
                field,
                None,
            )

            if value is not None:
                payload[field] = value

        return json.dumps(
            payload,
            ensure_ascii=False,
        )


def configure_logging() -> None:
    root = logging.getLogger()

    if getattr(
        root,
        "_pai_configured",
        False,
    ):
        return

    handler = logging.StreamHandler(
        sys.stdout
    )
    handler.setFormatter(
        JsonFormatter()
    )

    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(
        logging.INFO
    )
    root._pai_configured = True
