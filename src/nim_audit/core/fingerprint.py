"""BehavioralFingerprinter for runtime behavior analysis."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from nim_audit.models.common import AuditError
from nim_audit.models.fingerprint import (
    BehavioralSignature,
    FingerprintComparison,
    FingerprintResult,
    PromptResponse,
)

if TYPE_CHECKING:
    from nim_audit.core.image import NIMImage


class BehavioralFingerprinter:
    """Generator for behavioral fingerprints of NIM containers.

    The BehavioralFingerprinter runs a standard suite of prompts against
    a NIM container to generate a behavioral signature that can be used
    to compare model behavior across versions.

    Example:
        fingerprinter = BehavioralFingerprinter()

        # Generate fingerprint
        result = fingerprinter.generate(image)
        if result.success:
            fingerprint = result.fingerprint
            print(f"Generated fingerprint: {fingerprint.fingerprint_id}")

        # Compare fingerprints
        comparison = fingerprinter.compare(fp1, fp2)
        print(f"Similarity: {comparison.similarity_score:.2%}")
    """

    # Standard prompt suite for fingerprinting
    STANDARD_PROMPTS = [
        ("greeting", "Hello! How are you today?"),
        ("factual", "What is the capital of France?"),
        ("math", "What is 15 + 27?"),
        ("reasoning", "If all cats are animals and some animals are dogs, can we conclude that some cats are dogs?"),
        ("creative", "Write a haiku about programming."),
        ("instruction", "List three benefits of exercise."),
        ("code", "Write a Python function that adds two numbers."),
        ("summarize", "Summarize in one sentence: Machine learning is a subset of artificial intelligence."),
    ]

    def __init__(
        self,
        prompts: list[tuple[str, str]] | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        """Initialize the fingerprinter.

        Args:
            prompts: Custom prompts to use instead of standard suite
            timeout_seconds: Timeout for each prompt
        """
        self._prompts = prompts or self.STANDARD_PROMPTS
        self._timeout = timeout_seconds

    def generate(
        self,
        image: "NIMImage",
        endpoint: str | None = None,
        env: dict[str, str] | None = None,
    ) -> FingerprintResult:
        """Generate a behavioral fingerprint for a NIM image.

        Args:
            image: The NIM image to fingerprint
            endpoint: NIM endpoint URL (if already running)
            env: Environment variables for the container

        Returns:
            FingerprintResult with the behavioral signature or errors
        """
        try:
            responses: list[PromptResponse] = []
            total_latency = 0.0
            total_tokens_in = 0
            total_tokens_out = 0

            # If endpoint provided, use it; otherwise start container
            if endpoint:
                responses = self._run_prompts(endpoint)
            else:
                # Would start container and run prompts
                # For now, return placeholder
                return FingerprintResult.fail(
                    [
                        AuditError(
                            code="NOT_IMPLEMENTED",
                            message="Container startup not yet implemented. Provide endpoint URL.",
                        )
                    ]
                )

            # Calculate aggregates
            if responses:
                total_latency = sum(r.latency_ms for r in responses)
                total_tokens_in = sum(r.tokens_in for r in responses)
                total_tokens_out = sum(r.tokens_out for r in responses)

            signature = BehavioralSignature(
                image_reference=image.reference,
                fingerprint_id=str(uuid.uuid4()),
                generated_at=datetime.utcnow(),
                responses=responses,
                avg_latency_ms=total_latency / len(responses) if responses else 0.0,
                total_tokens_in=total_tokens_in,
                total_tokens_out=total_tokens_out,
                env_config=env or {},
            )

            return FingerprintResult.ok(fingerprint=signature)

        except Exception as e:
            return FingerprintResult.fail(
                [
                    AuditError(
                        code="FINGERPRINT_ERROR",
                        message=f"Failed to generate fingerprint: {e}",
                        details={"image": image.reference},
                    )
                ]
            )

    def _run_prompts(self, endpoint: str) -> list[PromptResponse]:
        """Run prompts against a NIM endpoint.

        Args:
            endpoint: The NIM endpoint URL

        Returns:
            List of prompt responses
        """
        import time

        import httpx

        responses: list[PromptResponse] = []

        for prompt_id, prompt_text in self._prompts:
            try:
                start_time = time.time()

                # Make request to NIM endpoint (OpenAI-compatible API)
                with httpx.Client(timeout=self._timeout) as client:
                    response = client.post(
                        f"{endpoint.rstrip('/')}/v1/chat/completions",
                        json={
                            "model": "nim",
                            "messages": [{"role": "user", "content": prompt_text}],
                            "max_tokens": 256,
                        },
                    )
                    response.raise_for_status()
                    data = response.json()

                latency_ms = (time.time() - start_time) * 1000

                # Extract response
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                usage = data.get("usage", {})

                response_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

                responses.append(
                    PromptResponse(
                        prompt_id=prompt_id,
                        prompt=prompt_text,
                        response=content,
                        tokens_in=usage.get("prompt_tokens", 0),
                        tokens_out=usage.get("completion_tokens", 0),
                        latency_ms=latency_ms,
                        response_hash=response_hash,
                    )
                )

            except Exception as e:
                # Record error as response
                responses.append(
                    PromptResponse(
                        prompt_id=prompt_id,
                        prompt=prompt_text,
                        response=f"ERROR: {e}",
                        latency_ms=0,
                    )
                )

        return responses

    def compare(
        self,
        source: BehavioralSignature,
        target: BehavioralSignature,
        tolerance: float = 0.05,
    ) -> FingerprintComparison:
        """Compare two behavioral fingerprints.

        Args:
            source: The source (baseline) fingerprint
            target: The target fingerprint to compare
            tolerance: Tolerance for similarity comparison

        Returns:
            FingerprintComparison with detailed comparison results
        """
        identical = 0
        different = 0
        response_diffs: list[dict[str, str]] = []

        # Build lookup by prompt_id
        source_by_id = {r.prompt_id: r for r in source.responses}
        target_by_id = {r.prompt_id: r for r in target.responses}

        all_ids = set(source_by_id.keys()) | set(target_by_id.keys())

        for prompt_id in all_ids:
            source_resp = source_by_id.get(prompt_id)
            target_resp = target_by_id.get(prompt_id)

            if source_resp and target_resp:
                if source_resp.response_hash == target_resp.response_hash:
                    identical += 1
                else:
                    different += 1
                    response_diffs.append(
                        {
                            "prompt_id": prompt_id,
                            "source": source_resp.response[:100],
                            "target": target_resp.response[:100],
                        }
                    )
            else:
                different += 1
                response_diffs.append(
                    {
                        "prompt_id": prompt_id,
                        "source": source_resp.response[:100] if source_resp else "MISSING",
                        "target": target_resp.response[:100] if target_resp else "MISSING",
                    }
                )

        total = identical + different
        similarity = identical / total if total > 0 else 0.0

        # Calculate latency change
        latency_change = 0.0
        if source.avg_latency_ms > 0:
            latency_change = (
                (target.avg_latency_ms - source.avg_latency_ms) / source.avg_latency_ms * 100
            )

        return FingerprintComparison(
            source=source,
            target=target,
            identical_responses=identical,
            different_responses=different,
            similarity_score=similarity,
            response_diffs=response_diffs,
            latency_change_percent=latency_change,
        )

    def load_fingerprint(self, path: str) -> BehavioralSignature:
        """Load a fingerprint from a JSON file.

        Args:
            path: Path to the fingerprint file

        Returns:
            BehavioralSignature loaded from file
        """
        import json

        with open(path, "r") as f:
            data = json.load(f)
        return BehavioralSignature.model_validate(data)

    def save_fingerprint(self, fingerprint: BehavioralSignature, path: str) -> None:
        """Save a fingerprint to a JSON file.

        Args:
            fingerprint: The fingerprint to save
            path: Path to save to
        """
        import json

        with open(path, "w") as f:
            json.dump(fingerprint.model_dump(mode="json"), f, indent=2, default=str)
