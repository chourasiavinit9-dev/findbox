"""
sloth_box.errors
Domain error hierarchy for resilient, typed exception handling.
"""

class SlothBoxError(Exception):
    """Base exception for all findbox / SlothBox operations."""
    def __init__(self, message, code="SLOTH_GENERIC_ERROR"):
        super().__init__(message)
        self.message = message
        self.code = code


class ValidationError(SlothBoxError):
    """Raised when an input or parameter fails validation."""
    def __init__(self, message):
        super().__init__(message, code="VALIDATION_ERROR")


class SecurityViolationError(SlothBoxError):
    """Raised when an unsafe path, XSS attempt, or malicious binary is detected."""
    def __init__(self, message):
        super().__init__(message, code="SECURITY_VIOLATION")


class ExtractionError(SlothBoxError):
    """Raised when file content extraction encounters an unrecoverable format issue."""
    def __init__(self, message):
        super().__init__(message, code="EXTRACTION_ERROR")


class DatabaseError(SlothBoxError):
    """Raised when an SQLite database or FTS5 operation fails."""
    def __init__(self, message):
        super().__init__(message, code="DATABASE_ERROR")


class AIInferenceError(SlothBoxError):
    """Raised when model inference or parsing fails and requires fallback."""
    def __init__(self, message):
        super().__init__(message, code="AI_INFERENCE_ERROR")
