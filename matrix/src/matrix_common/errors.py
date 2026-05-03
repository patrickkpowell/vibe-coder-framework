class MatrixError(Exception):
    """Base error for all Matrix failures."""


class MatrixAuthError(MatrixError):
    """Bot access token rejected or expired."""


class MatrixSendError(MatrixError):
    def __init__(self, msg: str, status_code: int | None = None) -> None:
        super().__init__(msg)
        self.status_code = status_code


class MatrixHomeserverError(MatrixError):
    """Homeserver unreachable or returned an unexpected response."""


class DestinationNotFoundError(MatrixError):
    def __init__(self, destination: str) -> None:
        super().__init__(f"Unknown destination: {destination!r}")
        self.destination = destination


class TemplateNotFoundError(MatrixError):
    def __init__(self, template: str) -> None:
        super().__init__(f"Unknown template: {template!r}")
        self.template = template
