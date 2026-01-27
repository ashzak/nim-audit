"""ConfigAnalyzer for analyzing NIM container configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nim_audit.models.common import AuditError
from nim_audit.models.config import (
    ConfigEntry,
    ConfigImpact,
    ConfigReport,
    ConfigResult,
    ImpactLevel,
)

if TYPE_CHECKING:
    from nim_audit.core.image import NIMImage


class ConfigAnalyzer:
    """Analyzer for NIM container configuration.

    The ConfigAnalyzer examines environment variables and configuration
    options for a NIM container, providing impact analysis and recommendations.

    Example:
        analyzer = ConfigAnalyzer()
        result = analyzer.analyze(
            image,
            env={"NIM_MAX_BATCH_SIZE": "64", "NIM_LOG_LEVEL": "debug"}
        )

        if result.success:
            for entry in result.report.entries:
                print(f"{entry.name}: {entry.impact.description}")
    """

    def __init__(self) -> None:
        """Initialize the config analyzer."""
        # Import knowledge base lazily to avoid circular imports
        from nim_audit.knowledge.env_vars import get_env_var_knowledge

        self._knowledge = get_env_var_knowledge()

    def analyze(
        self,
        image: "NIMImage",
        env: dict[str, str] | None = None,
        env_file: str | None = None,
    ) -> ConfigResult:
        """Analyze configuration for a NIM image.

        Args:
            image: The NIM image to analyze
            env: Environment variables to analyze (overrides defaults)
            env_file: Path to an env file to load

        Returns:
            ConfigResult with analysis report or errors
        """
        try:
            # Load env file if provided
            loaded_env: dict[str, str] = {}
            if env_file:
                loaded_env = self._load_env_file(env_file)

            # Merge: image defaults < loaded file < explicit env
            effective_env = {**image.metadata.env}
            effective_env.update(loaded_env)
            if env:
                effective_env.update(env)

            # Analyze each known configuration
            entries: list[ConfigEntry] = []
            warnings: list[str] = []
            recommendations: list[str] = []

            for var_name, var_info in self._knowledge.items():
                value = effective_env.get(var_name)
                default = image.metadata.env.get(var_name) or var_info.get("default")

                impact = None
                if var_info.get("impact"):
                    impact = ConfigImpact(
                        level=ImpactLevel(var_info["impact"].get("level", "low")),
                        description=var_info["impact"].get("description", ""),
                        affects=var_info["impact"].get("affects", []),
                    )

                entry = ConfigEntry(
                    name=var_name,
                    value=value,
                    default_value=default,
                    description=var_info.get("description", ""),
                    impact=impact,
                    is_required=var_info.get("required", False),
                    is_deprecated=var_info.get("deprecated", False),
                    deprecated_message=var_info.get("deprecated_message"),
                    valid_values=var_info.get("valid_values"),
                    validation_pattern=var_info.get("validation_pattern"),
                )
                entries.append(entry)

                # Add warnings for deprecated configs
                if entry.is_deprecated and entry.is_set:
                    msg = f"Deprecated: {var_name}"
                    if entry.deprecated_message:
                        msg += f" - {entry.deprecated_message}"
                    warnings.append(msg)

                # Add recommendations based on impact
                if entry.is_set and impact and impact.level in (
                    ImpactLevel.HIGH,
                    ImpactLevel.CRITICAL,
                ):
                    recommendations.append(
                        f"Review {var_name}: {impact.description}"
                    )

            # Also include unknown environment variables from effective_env
            known_vars = set(self._knowledge.keys())
            for var_name, value in effective_env.items():
                if var_name not in known_vars and var_name.startswith("NIM_"):
                    entries.append(
                        ConfigEntry(
                            name=var_name,
                            value=value,
                            description="Unknown NIM configuration variable",
                        )
                    )

            # Check for required but missing configs
            for entry in entries:
                if entry.is_required and not entry.is_set:
                    warnings.append(f"Required config missing: {entry.name}")

            report = ConfigReport(
                image_reference=image.reference,
                entries=entries,
                warnings=warnings,
                recommendations=recommendations,
            )

            return ConfigResult.ok(report)

        except Exception as e:
            return ConfigResult.fail(
                [
                    AuditError(
                        code="CONFIG_ERROR",
                        message=f"Failed to analyze config: {e}",
                        details={"image": image.reference},
                    )
                ]
            )

    def _load_env_file(self, path: str) -> dict[str, str]:
        """Load environment variables from a file.

        Supports standard .env file format:
        - KEY=value
        - KEY="quoted value"
        - # comments
        - Empty lines are ignored
        """
        env: dict[str, str] = {}

        with open(path, "r") as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()

                # Skip empty lines and comments
                if not line or line.startswith("#"):
                    continue

                # Parse KEY=value
                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                # Remove quotes
                if value.startswith('"') and value.endswith('"'):
                    value = value[1:-1]
                elif value.startswith("'") and value.endswith("'"):
                    value = value[1:-1]

                env[key] = value

        return env

    def validate(
        self,
        image: "NIMImage",
        env: dict[str, str] | None = None,
    ) -> list[str]:
        """Validate configuration values.

        Args:
            image: The NIM image
            env: Environment variables to validate

        Returns:
            List of validation error messages
        """
        errors: list[str] = []
        result = self.analyze(image, env)

        if not result.success:
            return [str(e) for e in result.errors]

        if result.report:
            for entry in result.report.entries:
                if entry.value and entry.valid_values:
                    if entry.value not in entry.valid_values:
                        errors.append(
                            f"{entry.name}: invalid value '{entry.value}'. "
                            f"Must be one of: {', '.join(entry.valid_values)}"
                        )

                if entry.value and entry.validation_pattern:
                    import re

                    if not re.match(entry.validation_pattern, entry.value):
                        errors.append(
                            f"{entry.name}: value '{entry.value}' does not match "
                            f"pattern '{entry.validation_pattern}'"
                        )

        return errors
