import contextvars
import uuid


request_id_var = contextvars.ContextVar("request_id", default="")


def new_request_id() -> str:
    return uuid.uuid4().hex


def set_request_id(request_id: str) -> None:
    request_id_var.set(request_id)


def get_request_id() -> str:
    return request_id_var.get() or new_request_id()

