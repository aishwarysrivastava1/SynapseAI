import json
import time
import logging
from typing import Any
from contextvars import ContextVar
import datetime

# Global context bound request_id mapping
request_id_var: ContextVar[str] = ContextVar("request_id", default="UNKNOWN_REQ")

import re

def mask_pii(text: Any) -> str:
    if not isinstance(text, str):
        return str(text)
    # Simple email mask: test@example.com -> t***@e*****.com
    email_pattern = r"([a-zA-Z0-9_.+-])([a-zA-Z0-9_.+-]{2,})@([a-zA-Z0-9-]+)\.([a-zA-Z0-9-.]+)"
    def repl(m):
        return f"{m.group(1)}***@{m.group(3)[0]}*****.{m.group(4)}"
    return re.sub(email_pattern, repl, text)

class OTELJsonFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "message": mask_pii(record.getMessage()),
            "logger": record.name,
            "request_id": request_id_var.get(),
            "trace": True # Identify as structured trace
        }
        if hasattr(record, "telemetry"):
            # Mask sensitive telemetry fields
            masked_telemetry = {k: mask_pii(v) for k, v in record.telemetry.items()}
            log_entry.update(masked_telemetry)
        if record.exc_info:
            log_entry["exception"] = mask_pii(self.formatException(record.exc_info))
        return json.dumps(log_entry)

# Setup specialized trace logger
trace_logger = logging.getLogger("chatbot.trace")
trace_logger.setLevel(logging.INFO)
trace_logger.propagate = False # Prevent double logging
handler = logging.StreamHandler()
handler.setFormatter(OTELJsonFormatter())
if not trace_logger.handlers:
    trace_logger.addHandler(handler)

class Tracer:
    """
    OpenTelemetry compatible span tracker handling execution boundaries elegantly.
    """
    def __init__(self, name: str, session_id: str = "anon", user_id: str = "anon"):
        self.name = name
        self.session_id = session_id
        self.user_id = user_id
        self.start_time = None
        self.telemetry_data = {}

    def __enter__(self):
        self.start_time = time.monotonic()
        return self

    def add_event(self, key, value):
        self.telemetry_data[key] = value

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.monotonic() - self.start_time) * 1000)
        status = "ERROR" if exc_type else "OK"
        
        telemetry = {
            "span_name": self.name,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "duration_ms": duration_ms,
            "status": status,
            **self.telemetry_data
        }
        
        if exc_type:
            trace_logger.error(f"Span {self.name} failed", extra={"telemetry": telemetry}, exc_info=True)
        else:
            trace_logger.info(f"Span {self.name} completed", extra={"telemetry": telemetry})
