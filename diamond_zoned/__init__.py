"""Diamond-zoned: Ollama-backed certification against Diamond Sutra thematic principles."""

from diamond_zoned.certifier import certify
from diamond_zoned.exceptions import CertificationParseError, OllamaTransportError, ValidationError
from diamond_zoned.models import CertificationResult, PrincipleCheck

__all__ = [
    "certify",
    "CertificationResult",
    "PrincipleCheck",
    "CertificationParseError",
    "OllamaTransportError",
    "ValidationError",
]

__version__ = "0.1.0"
