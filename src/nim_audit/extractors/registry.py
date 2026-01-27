"""Extractor registry for managing and discovering extractors."""

from typing import Iterator

from nim_audit.extractors.base import Extractor


class ExtractorRegistry:
    """Registry for managing artifact extractors.

    The registry allows dynamic registration and discovery of extractors.
    It supports filtering extractors by capability.

    Example:
        registry = ExtractorRegistry()
        registry.register(MetadataExtractor())
        registry.register(ModelExtractor())

        # Get all extractors that can handle an image
        for extractor in registry.extractors_for("nvcr.io/nim/llama3:1.5.0"):
            result = extractor.extract(image_id)
    """

    def __init__(self) -> None:
        """Initialize an empty registry."""
        self._extractors: dict[str, Extractor] = {}

    def register(self, extractor: Extractor) -> None:
        """Register an extractor.

        Args:
            extractor: The extractor to register

        Raises:
            ValueError: If an extractor with the same name is already registered
        """
        if extractor.name in self._extractors:
            raise ValueError(f"Extractor '{extractor.name}' is already registered")
        self._extractors[extractor.name] = extractor

    def unregister(self, name: str) -> None:
        """Unregister an extractor by name.

        Args:
            name: Name of the extractor to unregister

        Raises:
            KeyError: If no extractor with that name is registered
        """
        if name not in self._extractors:
            raise KeyError(f"No extractor named '{name}' is registered")
        del self._extractors[name]

    def get(self, name: str) -> Extractor | None:
        """Get an extractor by name.

        Args:
            name: Name of the extractor

        Returns:
            The extractor or None if not found
        """
        return self._extractors.get(name)

    def __getitem__(self, name: str) -> Extractor:
        """Get an extractor by name.

        Args:
            name: Name of the extractor

        Returns:
            The extractor

        Raises:
            KeyError: If no extractor with that name is registered
        """
        if name not in self._extractors:
            raise KeyError(f"No extractor named '{name}' is registered")
        return self._extractors[name]

    def __contains__(self, name: str) -> bool:
        """Check if an extractor is registered.

        Args:
            name: Name of the extractor

        Returns:
            True if registered
        """
        return name in self._extractors

    def __iter__(self) -> Iterator[Extractor]:
        """Iterate over all registered extractors."""
        return iter(self._extractors.values())

    def __len__(self) -> int:
        """Get number of registered extractors."""
        return len(self._extractors)

    @property
    def names(self) -> list[str]:
        """Get names of all registered extractors."""
        return list(self._extractors.keys())

    def extractors_for(self, image_id: str) -> Iterator[Extractor]:
        """Get extractors that can handle the given image.

        Args:
            image_id: Image identifier

        Yields:
            Extractors that can extract from the image
        """
        for extractor in self._extractors.values():
            if extractor.can_extract(image_id):
                yield extractor

    def clear(self) -> None:
        """Remove all registered extractors."""
        self._extractors.clear()


# Global default registry
_default_registry: ExtractorRegistry | None = None


def get_default_registry() -> ExtractorRegistry:
    """Get the default global extractor registry.

    Returns:
        The default ExtractorRegistry instance
    """
    global _default_registry
    if _default_registry is None:
        _default_registry = ExtractorRegistry()
    return _default_registry
