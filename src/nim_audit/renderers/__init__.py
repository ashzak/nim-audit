"""Output format renderers."""

from nim_audit.renderers.base import BaseRenderer, OutputFormat, RenderContext, Renderer
from nim_audit.renderers.json import JSONRenderer, JSONLRenderer
from nim_audit.renderers.markdown import MarkdownRenderer
from nim_audit.renderers.html import HTMLRenderer
from nim_audit.renderers.terminal import TerminalRenderer

__all__ = [
    "BaseRenderer",
    "OutputFormat",
    "RenderContext",
    "Renderer",
    "JSONRenderer",
    "JSONLRenderer",
    "MarkdownRenderer",
    "HTMLRenderer",
    "TerminalRenderer",
]


def get_renderer(format: OutputFormat | str) -> BaseRenderer:
    """Get a renderer for the specified format.

    Args:
        format: Output format (OutputFormat enum or string)

    Returns:
        Appropriate renderer instance

    Raises:
        ValueError: If format is not supported
    """
    if isinstance(format, str):
        format = OutputFormat(format)

    renderers = {
        OutputFormat.JSON: JSONRenderer,
        OutputFormat.MARKDOWN: MarkdownRenderer,
        OutputFormat.HTML: HTMLRenderer,
        OutputFormat.TERMINAL: TerminalRenderer,
    }

    renderer_class = renderers.get(format)
    if renderer_class is None:
        raise ValueError(f"Unsupported format: {format}")

    return renderer_class()
