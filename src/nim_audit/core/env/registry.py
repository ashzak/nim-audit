"""Environment variable registry loading and management."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from nim_audit.models.env import (
    Affect,
    ImpactLevel,
    ImpactMetric,
    InteractionEdge,
    Registry,
    RegistryEntry,
)

CONTROLLED_METRICS = ["latency", "throughput", "memory", "determinism", "numerics", "compatibility"]
CONTROLLED_IMPACTS = ["++", "+", "±", "-", "--", "none"]


def get_default_registry_path() -> str | None:
    """Get the default registry path from the package data directory."""
    data_dir = Path(__file__).parent.parent.parent / "data"
    registry_path = data_dir / "env_registry.v1.yaml"
    if registry_path.exists():
        return str(registry_path)
    return None


def get_default_interactions_path() -> str | None:
    """Get the default interactions path from the package data directory."""
    data_dir = Path(__file__).parent.parent.parent / "data"
    interactions_path = data_dir / "interactions.v1.yaml"
    if interactions_path.exists():
        return str(interactions_path)
    return None


def _parse_affect_item(it: Any) -> Affect | None:
    """Parse an affect item from various formats.

    Supported formats:
    - String: "latency:+"
    - Dict with metric/impact keys: {metric: "latency", impact: "+"}
    - Dict with metric as key: {latency: "+"}
    """
    if isinstance(it, str) and ":" in it:
        m, imp = it.split(":", 1)
        metric_str = str(m).strip().lower()
        impact_str = str(imp).strip()
        try:
            metric = ImpactMetric(metric_str)
            impact = ImpactLevel(impact_str)
            return Affect(metric=metric, impact=impact)
        except ValueError:
            return Affect(
                metric=ImpactMetric(metric_str) if metric_str in [e.value for e in ImpactMetric] else ImpactMetric.LATENCY,
                impact=ImpactLevel(impact_str) if impact_str in [e.value for e in ImpactLevel] else ImpactLevel.NONE,
            )
    if isinstance(it, dict):
        # Format: {metric: "latency", impact: "+"}
        if "metric" in it and "impact" in it:
            metric_str = str(it["metric"]).lower()
            impact_str = str(it["impact"])
            try:
                metric = ImpactMetric(metric_str)
                impact = ImpactLevel(impact_str)
                return Affect(metric=metric, impact=impact)
            except ValueError:
                return None
        # Format: {latency: "+"} - single key-value where key is metric
        if len(it) == 1:
            for metric_key, impact_val in it.items():
                metric_str = str(metric_key).lower()
                impact_str = str(impact_val)
                try:
                    metric = ImpactMetric(metric_str)
                    impact = ImpactLevel(impact_str)
                    return Affect(metric=metric, impact=impact)
                except ValueError:
                    return None
    return None


def _normalize_affects(raw: Any, warnings: list[str], var: str) -> list[Affect]:
    """Normalize affects list from raw YAML data."""
    out: list[Affect] = []
    if raw is None:
        return out
    if not isinstance(raw, list):
        warnings.append(f"{var}: affects should be a list")
        return out
    for it in raw:
        a = _parse_affect_item(it)
        if not a:
            warnings.append(f"{var}: invalid affects item {it!r}")
            continue
        if a.metric.value not in CONTROLLED_METRICS:
            warnings.append(f"{var}: affects.metric '{a.metric.value}' not in {CONTROLLED_METRICS}")
        if a.impact.value not in CONTROLLED_IMPACTS:
            warnings.append(f"{var}: affects.impact '{a.impact.value}' not in {CONTROLLED_IMPACTS}")
        out.append(a)
    # Deduplicate
    seen: set[tuple[str, str]] = set()
    unique: list[Affect] = []
    for a in out:
        key = (a.metric.value, a.impact.value)
        if key not in seen:
            seen.add(key)
            unique.append(a)
    return unique


def load_registry(
    registry_path: str | None = None,
    interactions_path: str | None = None,
) -> Registry:
    """
    Load the environment variable registry from YAML files.

    Args:
        registry_path: Path to registry YAML file (uses default if None)
        interactions_path: Path to interactions YAML file (uses default if None)

    Returns:
        Registry with entries and interactions
    """
    warnings: list[str] = []
    entries: dict[str, RegistryEntry] = {}
    edges: list[InteractionEdge] = []

    # Use defaults if not provided
    if registry_path is None:
        registry_path = get_default_registry_path()
    if interactions_path is None:
        interactions_path = get_default_interactions_path()

    raw: dict[str, Any] = {}
    if registry_path and os.path.exists(registry_path):
        with open(registry_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    items = raw.get("vars") if isinstance(raw, dict) else raw
    if items is None:
        items = []
    if not isinstance(items, list):
        warnings.append("registry: expected top-level 'vars' list")
        items = []

    for it in items:
        if not isinstance(it, dict) or "name" not in it:
            continue
        name = str(it["name"]).strip()
        affects = _normalize_affects(it.get("affects"), warnings, name)
        confidence = str(it.get("confidence") or "LOW").upper()
        if confidence not in ("HIGH", "MED", "LOW"):
            warnings.append(f"{name}: confidence '{confidence}' not in HIGH|MED|LOW")
            confidence = "LOW"
        entries[name] = RegistryEntry(
            name=name,
            type=str(it.get("type")) if it.get("type") is not None else None,
            scope=str(it.get("scope")) if it.get("scope") is not None else None,
            precedence=str(it.get("precedence")) if it.get("precedence") is not None else None,
            default=str(it.get("default")) if it.get("default") is not None else None,
            affects=affects,
            determinism=str(it.get("determinism")) if it.get("determinism") is not None else None,
            interactions=list(it.get("interactions") or []),
            failure_modes=[str(x) for x in (it.get("failure_modes") or [])],
            confidence=confidence,
            evidence=list(it.get("evidence") or []),
        )

    if interactions_path and os.path.exists(interactions_path):
        with open(interactions_path, "r", encoding="utf-8") as f:
            iraw = yaml.safe_load(f) or {}
        ed_items = iraw.get("edges") if isinstance(iraw, dict) else iraw
        if ed_items is None:
            ed_items = []
        if isinstance(ed_items, list):
            for e in ed_items:
                if not isinstance(e, dict):
                    continue
                if not all(k in e for k in ("var_a", "var_b", "interaction_type", "description")):
                    continue
                edges.append(
                    InteractionEdge(
                        var_a=str(e["var_a"]),
                        var_b=str(e["var_b"]),
                        interaction_type=str(e["interaction_type"]),
                        description=str(e["description"]),
                    )
                )
        else:
            warnings.append("interactions: expected top-level 'edges' list")

    return Registry(entries=entries, interactions=edges, warnings=warnings)


def interactions_for(var: str, reg: Registry) -> list[dict[str, str]]:
    """
    Get all interactions for a given variable.

    Args:
        var: Variable name
        reg: Registry to search

    Returns:
        List of interaction dicts with keys: with, type, description
    """
    out = []
    for e in reg.interactions:
        if e.var_a == var or e.var_b == var:
            other = e.var_b if e.var_a == var else e.var_a
            out.append({"with": other, "type": e.interaction_type, "description": e.description})
    return out
