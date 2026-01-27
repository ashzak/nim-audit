"""Data models for nim-audit.

All models are Pydantic BaseModel with frozen=True for immutability.
"""

from nim_audit.models.image import (
    ImageDigest,
    ImageManifest,
    ImageMetadata,
    LayerInfo,
)
from nim_audit.models.diff import (
    BreakingChange,
    ChangeCategory,
    ChangeType,
    DiffEntry,
    DiffReport,
    DiffResult,
    Severity,
)
from nim_audit.models.config import (
    ConfigEntry,
    ConfigImpact,
    ConfigReport,
    ConfigResult,
    ImpactLevel,
)
from nim_audit.models.compat import (
    CompatReport,
    CompatResult,
    GPUInfo,
    GPURequirements,
)
from nim_audit.models.fingerprint import (
    BehavioralSignature,
    FingerprintComparison,
    FingerprintResult,
    PromptResponse,
)
from nim_audit.models.policy import (
    LintResult,
    LintViolation,
    Policy,
    Rule,
    RuleSeverity,
)
from nim_audit.models.common import AuditError

__all__ = [
    # Image
    "ImageDigest",
    "ImageManifest",
    "ImageMetadata",
    "LayerInfo",
    # Diff
    "BreakingChange",
    "ChangeCategory",
    "ChangeType",
    "DiffEntry",
    "DiffReport",
    "DiffResult",
    "Severity",
    # Config
    "ConfigEntry",
    "ConfigImpact",
    "ConfigReport",
    "ConfigResult",
    "ImpactLevel",
    # Compat
    "CompatReport",
    "CompatResult",
    "GPUInfo",
    "GPURequirements",
    # Fingerprint
    "BehavioralSignature",
    "FingerprintComparison",
    "FingerprintResult",
    "PromptResponse",
    # Policy
    "LintResult",
    "LintViolation",
    "Policy",
    "Rule",
    "RuleSeverity",
    # Common
    "AuditError",
]
