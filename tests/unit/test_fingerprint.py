"""Unit tests for the BehavioralFingerprinter."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from nim_audit.core.fingerprint import BehavioralFingerprinter
from nim_audit.core.image import NIMImage
from nim_audit.models.fingerprint import BehavioralSignature, PromptResponse


class TestBehavioralFingerprinter:
    """Tests for BehavioralFingerprinter."""

    def test_init_default_prompts(self):
        """Test that default prompts are used when none provided."""
        fp = BehavioralFingerprinter()
        assert len(fp._prompts) == len(fp.STANDARD_PROMPTS)
        assert fp._timeout == 30.0

    def test_init_custom_prompts(self):
        """Test initialization with custom prompts."""
        custom_prompts = [("test", "Test prompt")]
        fp = BehavioralFingerprinter(prompts=custom_prompts, timeout_seconds=60.0)
        assert fp._prompts == custom_prompts
        assert fp._timeout == 60.0

    def test_generate_without_endpoint(self, sample_nim_image: NIMImage):
        """Test generate returns error when no endpoint provided."""
        fp = BehavioralFingerprinter()
        result = fp.generate(sample_nim_image)

        assert not result.success
        assert result.fingerprint is None
        assert len(result.errors) == 1
        assert result.errors[0].code == "NOT_IMPLEMENTED"

    @patch("httpx.Client")
    def test_generate_with_endpoint(self, mock_client, sample_nim_image: NIMImage):
        """Test generate with a mocked endpoint."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello! I'm fine."}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5},
        }
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__ = MagicMock(return_value=mock_client_instance)
        mock_client_instance.__exit__ = MagicMock(return_value=False)
        mock_client.return_value = mock_client_instance

        fp = BehavioralFingerprinter()
        result = fp.generate(sample_nim_image, endpoint="http://localhost:8000")

        assert result.success
        assert result.fingerprint is not None
        assert len(result.fingerprint.responses) == len(fp.STANDARD_PROMPTS)

    def test_compare_identical_fingerprints(self):
        """Test comparing identical fingerprints."""
        responses = [
            PromptResponse(
                prompt_id="greeting",
                prompt="Hello!",
                response="Hi there!",
                tokens_in=5,
                tokens_out=3,
                latency_ms=100.0,
                response_hash="abc123",
            )
        ]
        fp1 = BehavioralSignature(
            image_reference="test:1.0",
            fingerprint_id="fp1",
            generated_at=datetime.utcnow(),
            responses=responses,
            avg_latency_ms=100.0,
            total_tokens_in=5,
            total_tokens_out=3,
            env_config={},
        )
        fp2 = BehavioralSignature(
            image_reference="test:1.1",
            fingerprint_id="fp2",
            generated_at=datetime.utcnow(),
            responses=responses,
            avg_latency_ms=100.0,
            total_tokens_in=5,
            total_tokens_out=3,
            env_config={},
        )

        fingerprinter = BehavioralFingerprinter()
        comparison = fingerprinter.compare(fp1, fp2)

        assert comparison.identical_responses == 1
        assert comparison.different_responses == 0
        assert comparison.similarity_score == 1.0

    def test_compare_different_fingerprints(self):
        """Test comparing different fingerprints."""
        responses1 = [
            PromptResponse(
                prompt_id="greeting",
                prompt="Hello!",
                response="Hi there!",
                tokens_in=5,
                tokens_out=3,
                latency_ms=100.0,
                response_hash="abc123",
            )
        ]
        responses2 = [
            PromptResponse(
                prompt_id="greeting",
                prompt="Hello!",
                response="Hello!",
                tokens_in=5,
                tokens_out=2,
                latency_ms=120.0,
                response_hash="def456",
            )
        ]
        fp1 = BehavioralSignature(
            image_reference="test:1.0",
            fingerprint_id="fp1",
            generated_at=datetime.utcnow(),
            responses=responses1,
            avg_latency_ms=100.0,
            total_tokens_in=5,
            total_tokens_out=3,
            env_config={},
        )
        fp2 = BehavioralSignature(
            image_reference="test:1.1",
            fingerprint_id="fp2",
            generated_at=datetime.utcnow(),
            responses=responses2,
            avg_latency_ms=120.0,
            total_tokens_in=5,
            total_tokens_out=2,
            env_config={},
        )

        fingerprinter = BehavioralFingerprinter()
        comparison = fingerprinter.compare(fp1, fp2)

        assert comparison.identical_responses == 0
        assert comparison.different_responses == 1
        assert comparison.similarity_score == 0.0
        assert len(comparison.response_diffs) == 1
        assert comparison.latency_change_percent == 20.0

    def test_compare_missing_responses(self):
        """Test comparison when one fingerprint has missing responses."""
        responses1 = [
            PromptResponse(
                prompt_id="greeting",
                prompt="Hello!",
                response="Hi!",
                tokens_in=5,
                tokens_out=2,
                latency_ms=100.0,
                response_hash="abc",
            ),
            PromptResponse(
                prompt_id="math",
                prompt="2+2?",
                response="4",
                tokens_in=3,
                tokens_out=1,
                latency_ms=50.0,
                response_hash="def",
            ),
        ]
        responses2 = [
            PromptResponse(
                prompt_id="greeting",
                prompt="Hello!",
                response="Hi!",
                tokens_in=5,
                tokens_out=2,
                latency_ms=100.0,
                response_hash="abc",
            ),
        ]
        fp1 = BehavioralSignature(
            image_reference="test:1.0",
            fingerprint_id="fp1",
            generated_at=datetime.utcnow(),
            responses=responses1,
            avg_latency_ms=75.0,
            total_tokens_in=8,
            total_tokens_out=3,
            env_config={},
        )
        fp2 = BehavioralSignature(
            image_reference="test:1.1",
            fingerprint_id="fp2",
            generated_at=datetime.utcnow(),
            responses=responses2,
            avg_latency_ms=100.0,
            total_tokens_in=5,
            total_tokens_out=2,
            env_config={},
        )

        fingerprinter = BehavioralFingerprinter()
        comparison = fingerprinter.compare(fp1, fp2)

        assert comparison.identical_responses == 1
        assert comparison.different_responses == 1
        assert comparison.similarity_score == 0.5

    def test_save_and_load_fingerprint(self, tmp_path):
        """Test saving and loading fingerprint."""
        fp = BehavioralSignature(
            image_reference="test:1.0",
            fingerprint_id="test-fp",
            generated_at=datetime(2024, 1, 1, 12, 0, 0),
            responses=[
                PromptResponse(
                    prompt_id="test",
                    prompt="Test prompt",
                    response="Test response",
                    tokens_in=5,
                    tokens_out=5,
                    latency_ms=100.0,
                    response_hash="abc123",
                )
            ],
            avg_latency_ms=100.0,
            total_tokens_in=5,
            total_tokens_out=5,
            env_config={"KEY": "value"},
        )

        fingerprinter = BehavioralFingerprinter()
        file_path = str(tmp_path / "fingerprint.json")

        fingerprinter.save_fingerprint(fp, file_path)
        loaded = fingerprinter.load_fingerprint(file_path)

        assert loaded.fingerprint_id == fp.fingerprint_id
        assert loaded.image_reference == fp.image_reference
        assert len(loaded.responses) == 1
        assert loaded.responses[0].prompt_id == "test"
