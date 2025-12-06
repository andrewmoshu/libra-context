"""Custom exceptions for libra."""


class LibraError(Exception):
    """Base exception for libra."""

    pass


class ContextNotFoundError(LibraError):
    """Raised when a context is not found."""

    def __init__(self, context_id: str):
        self.context_id = context_id
        super().__init__(f"Context not found: {context_id}")


class EmbeddingError(LibraError):
    """Raised when embedding generation fails."""

    def __init__(self, message: str, original_error: Exception | None = None):
        self.original_error = original_error
        super().__init__(message)


class StorageError(LibraError):
    """Raised when storage operations fail."""

    pass


class ConfigurationError(LibraError):
    """Raised when configuration is invalid."""

    pass


class LibrarianError(LibraError):
    """Raised when Librarian operations fail."""

    pass


class IngestionError(LibraError):
    """Raised when content ingestion fails."""

    def __init__(self, source: str, message: str):
        self.source = source
        super().__init__(f"Failed to ingest '{source}': {message}")
