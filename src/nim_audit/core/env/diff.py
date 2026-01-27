"""Environment variable surface diffing and risk assessment."""

from __future__ import annotations

from typing import Any

from nim_audit.models.env import EnvDiff, EnvSurface, Registry


def env_surface(
    discovered: list[str],
    defaults: dict[str, str],
    runtime_params_env: dict[str, str],
) -> EnvSurface:
    """
    Build an environment surface from discovered vars, defaults, and runtime params.

    Args:
        discovered: List of discovered variable names
        defaults: Default values from container
        runtime_params_env: Runtime parameter environment variables

    Returns:
        EnvSurface with all known variables
    """
    out: dict[str, Any] = dict(defaults or {})
    for k, v in (runtime_params_env or {}).items():
        out[k] = str(v)
    for v in discovered:
        out.setdefault(v, None)
    return EnvSurface(vars=out)


def diff_surfaces(a: EnvSurface, b: EnvSurface) -> EnvDiff:
    """
    Diff two environment surfaces.

    Args:
        a: First surface (typically old/baseline)
        b: Second surface (typically new/target)

    Returns:
        EnvDiff with added, removed, and changed variables
    """
    keys = set(a.vars.keys()) | set(b.vars.keys())
    added = sorted([k for k in keys if k not in a.vars])
    removed = sorted([k for k in keys if k not in b.vars])
    changed: dict[str, list[Any]] = {}
    for k in sorted(keys):
        if a.vars.get(k) != b.vars.get(k):
            changed[k] = [a.vars.get(k), b.vars.get(k)]
    return EnvDiff(added=added, removed=removed, changed=changed, risky_changed=0)


def risk_delta(changed_keys: list[str], reg: Registry) -> int:
    """
    Calculate the number of risky changes based on registry metadata.

    Args:
        changed_keys: List of changed variable names
        reg: Environment variable registry

    Returns:
        Count of variables that affect determinism or memory negatively
    """
    risky = 0
    for k in changed_keys:
        ent = reg.entries.get(k)
        if not ent:
            continue
        for a in ent.affects:
            if (a.metric.value == "determinism" and a.impact.value in ("-", "--")) or (
                a.metric.value == "memory" and a.impact.value in ("+", "++")
            ):
                risky += 1
                break
    return risky
