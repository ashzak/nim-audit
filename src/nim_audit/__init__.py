"""nim-audit: A professional tool for auditing NVIDIA NIM containers.

This package provides comprehensive auditing capabilities for NVIDIA NIM
(NVIDIA Inference Microservices) containers, including:

- **Diff Engine**: Compare two NIM container versions to detect changes
- **Config Analyzer**: Analyze environment variables and configuration impacts
- **Compatibility Checker**: Verify GPU and driver compatibility
- **Policy Linter**: Validate containers against enterprise policies
- **Behavioral Fingerprinting**: Generate and compare runtime signatures

Usage:
    # Library API
    from nim_audit import NIMImage, DiffEngine, ConfigAnalyzer, CompatChecker

    # Load images
    img1 = NIMImage.from_local("nvcr.io/nim/llama3:1.5.0")
    img2 = NIMImage.from_local("nvcr.io/nim/llama3:1.6.0")

    # Diff
    engine = DiffEngine()
    result = engine.diff(img1, img2)
    print(result.report.breaking_changes)

    # Config analysis
    analyzer = ConfigAnalyzer()
    result = analyzer.analyze(img2, env={"NIM_MAX_BATCH_SIZE": "64"})

    # Compatibility check
    checker = CompatChecker()
    result = checker.check(img2, gpu="A10", driver_version="550.54")

CLI:
    nim-audit diff <image1> <image2>
    nim-audit config --image <image>
    nim-audit compat --image <image> --gpu <gpu>
    nim-audit lint --image <image> --policy <policy.yaml>
    nim-audit fingerprint --image <image>
    nim-audit cluster --image <image>
"""

__version__ = "0.1.0"

# Core classes
from nim_audit.core.image import NIMImage
from nim_audit.core.diff import DiffEngine
from nim_audit.core.config import ConfigAnalyzer
from nim_audit.core.compat import CompatChecker
from nim_audit.core.fingerprint import BehavioralFingerprinter
from nim_audit.core.lint import PolicyLinter

# Models (commonly used)
from nim_audit.models.diff import DiffResult, DiffReport, BreakingChange
from nim_audit.models.config import ConfigResult, ConfigReport
from nim_audit.models.compat import CompatResult, CompatReport, GPUInfo, GPURequirements
from nim_audit.models.fingerprint import FingerprintResult, BehavioralSignature
from nim_audit.models.policy import LintResult, Policy, Rule
from nim_audit.models.image import ImageMetadata

# Extractors
from nim_audit.extractors.base import Extractor, ExtractorResult
from nim_audit.extractors.registry import ExtractorRegistry, get_default_registry

# Renderers
from nim_audit.renderers.base import Renderer, RenderContext, OutputFormat

__all__ = [
    # Version
    "__version__",
    # Core
    "NIMImage",
    "DiffEngine",
    "ConfigAnalyzer",
    "CompatChecker",
    "BehavioralFingerprinter",
    "PolicyLinter",
    # Models - Diff
    "DiffResult",
    "DiffReport",
    "BreakingChange",
    # Models - Config
    "ConfigResult",
    "ConfigReport",
    # Models - Compat
    "CompatResult",
    "CompatReport",
    "GPUInfo",
    "GPURequirements",
    # Models - Fingerprint
    "FingerprintResult",
    "BehavioralSignature",
    # Models - Policy
    "LintResult",
    "Policy",
    "Rule",
    # Models - Image
    "ImageMetadata",
    # Extractors
    "Extractor",
    "ExtractorResult",
    "ExtractorRegistry",
    "get_default_registry",
    # Renderers
    "Renderer",
    "RenderContext",
    "OutputFormat",
]
