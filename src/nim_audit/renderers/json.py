"""JSON renderer for nim-audit output."""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from nim_audit.renderers.base import BaseRenderer, OutputFormat, RenderContext


class JSONRenderer(BaseRenderer):
    """Renderer for JSON output format.

    Converts audit results to JSON with configurable formatting.

    Example:
        renderer = JSONRenderer()
        json_str = renderer.render(diff_report, context)
    """

    @property
    def format(self) -> OutputFormat:
        """The output format this renderer produces."""
        return OutputFormat.JSON

    def render(self, data: Any, context: RenderContext) -> str:
        """Render data to a JSON string.

        Args:
            data: The data to render (typically a Pydantic model)
            context: Rendering context with options

        Returns:
            JSON string
        """
        # Convert to dict if Pydantic model
        if isinstance(data, BaseModel):
            dict_data = data.model_dump(mode="json")
        else:
            dict_data = data

        return json.dumps(
            dict_data,
            indent=context.indent if context.indent else None,
            default=self._json_serializer,
            ensure_ascii=False,
        )

    def render_to_file(self, data: Any, context: RenderContext) -> None:
        """Render data directly to a JSON file.

        Args:
            data: The data to render
            context: Rendering context (must have output_path set)

        Raises:
            ValueError: If context.output_path is not set
        """
        if context.output_path is None:
            raise ValueError("output_path must be set in context for file rendering")

        content = self.render(data, context)
        context.output_path.write_text(content, encoding="utf-8")

    @staticmethod
    def _json_serializer(obj: Any) -> Any:
        """Custom JSON serializer for non-standard types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, set):
            return list(obj)
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class JSONLRenderer(BaseRenderer):
    """Renderer for JSON Lines (JSONL) output format.

    Outputs one JSON object per line, useful for streaming
    and log processing.

    Example:
        renderer = JSONLRenderer()
        jsonl_str = renderer.render(list_of_items, context)
    """

    @property
    def format(self) -> OutputFormat:
        """The output format this renderer produces."""
        return OutputFormat.JSON

    def render(self, data: Any, context: RenderContext) -> str:
        """Render data to JSONL string.

        Args:
            data: List of items to render (one per line)
            context: Rendering context

        Returns:
            JSONL string (one JSON object per line)
        """
        if not isinstance(data, (list, tuple)):
            data = [data]

        lines = []
        for item in data:
            if isinstance(item, BaseModel):
                dict_data = item.model_dump(mode="json")
            else:
                dict_data = item

            line = json.dumps(
                dict_data,
                default=JSONRenderer._json_serializer,
                ensure_ascii=False,
            )
            lines.append(line)

        return "\n".join(lines)
