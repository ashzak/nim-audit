"""Base renderer protocol and types."""

from enum import Enum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, Field


class OutputFormat(str, Enum):
    """Supported output formats."""

    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    TERMINAL = "terminal"


class RenderContext(BaseModel):
    """Context for rendering operations."""

    model_config = {"frozen": True}

    format: OutputFormat = Field(default=OutputFormat.TERMINAL, description="Output format")
    output_path: Path | None = Field(default=None, description="Output file path")
    verbose: bool = Field(default=False, description="Verbose output")
    color: bool = Field(default=True, description="Enable color output (terminal only)")
    template: str | None = Field(default=None, description="Custom template path")

    # Formatting options
    indent: int = Field(default=2, description="JSON indentation")
    include_raw: bool = Field(default=False, description="Include raw data in output")


@runtime_checkable
class Renderer(Protocol):
    """Protocol for output renderers.

    Renderers are responsible for converting audit results into
    human-readable or machine-readable output formats.

    To implement a custom renderer:
    1. Create a class that implements this protocol
    2. Handle the specific output format appropriately

    Example:
        class MyRenderer:
            @property
            def format(self) -> OutputFormat:
                return OutputFormat.JSON

            def render(self, data: Any, context: RenderContext) -> str:
                return json.dumps(data, indent=context.indent)

            def render_to_file(self, data: Any, context: RenderContext) -> None:
                content = self.render(data, context)
                context.output_path.write_text(content)
    """

    @property
    def format(self) -> OutputFormat:
        """The output format this renderer produces."""
        ...

    def render(self, data: Any, context: RenderContext) -> str:
        """Render data to a string.

        Args:
            data: The data to render (typically a Pydantic model)
            context: Rendering context with options

        Returns:
            Rendered string output
        """
        ...

    def render_to_file(self, data: Any, context: RenderContext) -> None:
        """Render data directly to a file.

        Args:
            data: The data to render
            context: Rendering context (must have output_path set)

        Raises:
            ValueError: If context.output_path is not set
        """
        ...


class BaseRenderer:
    """Base implementation with common functionality.

    Provides default implementation of render_to_file.
    Subclasses should implement format property and render method.
    """

    def render_to_file(self, data: Any, context: RenderContext) -> None:
        """Render data directly to a file.

        Args:
            data: The data to render
            context: Rendering context (must have output_path set)

        Raises:
            ValueError: If context.output_path is not set
        """
        if context.output_path is None:
            raise ValueError("output_path must be set in context for file rendering")

        content = self.render(data, context)
        context.output_path.write_text(content)

    def render(self, data: Any, context: RenderContext) -> str:
        """Render data to a string. Must be implemented by subclasses."""
        raise NotImplementedError
