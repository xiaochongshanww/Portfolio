class RerankerError(RuntimeError):
    """A sanitized reranker failure safe for logs and diagnostics."""

    def __init__(self, code: str, message: str, *, http_status: int | None = None):
        self.code = code
        self.http_status = http_status
        super().__init__(message)
