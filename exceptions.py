# Define base exception classes (optional, inherit from Exception)
class EventValidationError(Exception):
    """Raised when event validation fails"""
    def __init__(self, message="Event validation error"):
        super().__init__(message)

class ICSGenerationError(Exception):
    """Raised when ICS content generation fails"""
    def __init__(self, message="ICS generation error"):
        super().__init__(message)

class ICSImportValidationError(Exception):
    """Raised when ICS import validation fails"""
    def __init__(self, message="ICS import validation error"):
        super().__init__(message)
