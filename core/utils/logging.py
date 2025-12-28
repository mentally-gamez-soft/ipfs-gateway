import json
import logging
import os
import uuid
from logging.handlers import RotatingFileHandler
from flask import g, has_request_context, request


class RequestIdFilter(logging.Filter):
    def filter(self, record):
        if has_request_context():
            record.request_id = getattr(g, "request_id", None)
        else:
            record.request_id = None
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "request_id": getattr(record, "request_id", None),
        }
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(app):
    log_dir = app.config.get("LOG_DIR", "logs")
    log_file = app.config.get("LOG_FILE", "app.log")
    level = getattr(logging, app.config.get("LOG_LEVEL", "INFO"), logging.INFO)

    os.makedirs(log_dir, exist_ok=True)

    handler = RotatingFileHandler(os.path.join(log_dir, log_file), maxBytes=2_000_000, backupCount=5)
    handler.setLevel(level)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestIdFilter())

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(handler)


def init_request_hooks(app):
    @app.before_request
    def assign_request_id():
        g.request_id = str(uuid.uuid4())

    @app.after_request
    def log_response(resp):
        logging.getLogger("app.requests").info(
            f"{request.method} {request.path} -> {resp.status_code}"
        )
        return resp
