class RerankerError(RuntimeError):
    """A sanitized reranker failure safe for logs and diagnostics."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)
