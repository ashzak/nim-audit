"""Behavioral fingerprinting data models."""

from datetime import datetime

from pydantic import BaseModel, Field

from nim_audit.models.common import AuditError


class PromptResponse(BaseModel):
    """A single prompt-response pair for fingerprinting."""

    model_config = {"frozen": True}

    prompt_id: str = Field(description="Identifier for this prompt")
    prompt: str = Field(description="The input prompt")
    response: str = Field(description="The model response")
    tokens_in: int = Field(default=0, description="Input token count")
    tokens_out: int = Field(default=0, description="Output token count")
    latency_ms: float = Field(default=0.0, description="Response latency in milliseconds")
    response_hash: str | None = Field(default=None, description="Hash of the response for comparison")


class BehavioralSignature(BaseModel):
    """Behavioral signature of a NIM container."""

    model_config = {"frozen": True}

    # Identity
    image_reference: str = Field(description="Image reference")
    fingerprint_id: str = Field(description="Unique fingerprint identifier")
    generated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Generation timestamp",
    )

    # Responses
    responses: list[PromptResponse] = Field(
        default_factory=list,
        description="Prompt-response pairs",
    )

    # Aggregate metrics
    avg_latency_ms: float = Field(default=0.0, description="Average response latency")
    total_tokens_in: int = Field(default=0, description="Total input tokens")
    total_tokens_out: int = Field(default=0, description="Total output tokens")

    # Configuration used
    env_config: dict[str, str] = Field(
        default_factory=dict,
        description="Environment configuration used",
    )
    gpu_info: str | None = Field(default=None, description="GPU used for fingerprinting")


class FingerprintComparison(BaseModel):
    """Comparison between two behavioral fingerprints."""

    model_config = {"frozen": True}

    source: BehavioralSignature = Field(description="Source fingerprint")
    target: BehavioralSignature = Field(description="Target fingerprint")

    # Comparison results
    identical_responses: int = Field(default=0, description="Number of identical responses")
    different_responses: int = Field(default=0, description="Number of different responses")
    similarity_score: float = Field(
        default=0.0,
        description="Overall similarity score (0.0 to 1.0)",
    )

    # Detailed differences
    response_diffs: list[dict[str, str]] = Field(
        default_factory=list,
        description="Detailed response differences",
    )

    # Performance comparison
    latency_change_percent: float = Field(
        default=0.0,
        description="Percentage change in average latency",
    )

    @property
    def is_similar(self) -> bool:
        """Check if fingerprints are similar (>95% similarity)."""
        return self.similarity_score >= 0.95


class FingerprintResult(BaseModel):
    """Result of a fingerprint operation."""

    model_config = {"frozen": True}

    success: bool = Field(description="Whether the operation succeeded")
    fingerprint: BehavioralSignature | None = Field(
        default=None,
        description="The fingerprint if successful",
    )
    comparison: FingerprintComparison | None = Field(
        default=None,
        description="Comparison result if comparing fingerprints",
    )
    errors: list[AuditError] = Field(default_factory=list, description="Errors that occurred")

    @classmethod
    def ok(
        cls,
        fingerprint: BehavioralSignature | None = None,
        comparison: FingerprintComparison | None = None,
    ) -> "FingerprintResult":
        """Create a successful result."""
        return cls(success=True, fingerprint=fingerprint, comparison=comparison)

    @classmethod
    def fail(cls, errors: list[AuditError]) -> "FingerprintResult":
        """Create a failed result."""
        return cls(success=False, errors=errors)
