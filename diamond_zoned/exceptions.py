class DiamondZonedError(Exception):
    """Base error for this package."""


class ValidationError(DiamondZonedError):
    """User input or configuration failed validation."""


class OllamaTransportError(DiamondZonedError):
    """HTTP or Ollama API failure after retries/timeouts."""


class CertificationParseError(DiamondZonedError):
    """Model output was not valid JSON or failed schema checks."""
