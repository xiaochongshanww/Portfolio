import contextvars
import re
import uuid


request_id_var = contextvars.ContextVar("request_id", default="")
REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def new_request_id() -> str:
    return uuid.uuid4().hex


def normalize_request_id(value: str | None) -> str:
    candidate = (value or "").strip()
    return candidate if REQUEST_ID_RE.fullmatch(candidate) else new_request_id()


def set_request_id(request_id: str) -> contextvars.Token:
    return request_id_var.set(request_id)


def reset_request_id(token: contextvars.Token) -> None:
    request_id_var.reset(token)


def current_request_id() -> str:
    return request_id_var.get()


def get_request_id() -> str:
    return request_id_var.get() or new_request_id()

