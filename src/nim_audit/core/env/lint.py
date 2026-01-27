"""Environment variable linting with rule-based validation."""

from __future__ import annotations

import re
from typing import Any

import yaml

from nim_audit.models.env import Finding, LintResult, Registry, RegistryEntry, Severity
from nim_audit.core.env.cel import eval_cel, CelError


def _match_value(val: str | None, cond: dict[str, Any]) -> bool:
    """Check if a value matches a condition."""
    if val is None:
        return False
    if "equals" in cond:
        return str(val) == str(cond["equals"])
    if "not_equals" in cond:
        return str(val) != str(cond["not_equals"])
    if "matches" in cond:
        return re.search(str(cond["matches"]), str(val)) is not None
    return False


def _eval_cond(effective: dict[str, str], cond: dict[str, Any]) -> bool:
    """Evaluate a single condition against effective environment."""
    env = cond.get("env")
    if not env:
        return False
    key = str(env)
    val = effective.get(key)
    if cond.get("set") is True:
        return key in effective
    if cond.get("not_set") is True:
        return key not in effective
    if "equals" in cond or "not_equals" in cond or "matches" in cond:
        return _match_value(val, cond)
    return False


def _eval_when(effective: dict[str, str], when: dict[str, Any]) -> bool:
    """Evaluate a when clause with any/all support."""
    if "any" in when:
        items = when.get("any") or []
        return any(
            _eval_when(effective, x) if isinstance(x, dict) and ("any" in x or "all" in x) else _eval_cond(effective, x)
            for x in items
        )
    if "all" in when:
        items = when.get("all") or []
        return all(
            _eval_when(effective, x) if isinstance(x, dict) and ("any" in x or "all" in x) else _eval_cond(effective, x)
            for x in items
        )
    return _eval_cond(effective, when)


def load_rules(path: str | None) -> dict[str, Any]:
    """
    Load lint rules from a YAML file.

    Args:
        path: Path to rules YAML file

    Returns:
        Rules document with schema_version and rules list
    """
    if not path:
        return {"schema_version": "nim-audit/env-rules/v1", "rules": []}
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    # Allow list form
    if isinstance(raw, list):
        return {"schema_version": "nim-audit/env-rules/v1", "rules": [r for r in raw if isinstance(r, dict)]}
    if not isinstance(raw, dict):
        return {"schema_version": "nim-audit/env-rules/v1", "rules": []}
    rules = raw.get("rules")
    if rules is None and any(k in raw for k in ("when", "then", "id")):
        rules = [raw]
    if not isinstance(rules, list):
        rules = []
    raw["rules"] = [r for r in rules if isinstance(r, dict)]
    raw.setdefault("schema_version", "nim-audit/env-rules/v1")
    return raw


def _lint_unknown_keys(
    env_file_vars: dict[str, str],
    discovered_vars: list[str],
    reg: Registry,
) -> list[Finding]:
    """Find variables that are not in registry and not discovered."""
    findings: list[Finding] = []
    discovered_set = set(discovered_vars)
    registry_set = set(reg.entries.keys())
    for k in sorted(env_file_vars.keys()):
        if k not in registry_set and k not in discovered_set:
            findings.append(
                Finding(
                    id="ENV-UNKNOWN",
                    severity=Severity.WARN,
                    env=k,
                    message="Env var not recognized (not in registry and not discovered in image).",
                )
            )
    return findings


def _lint_registry_heuristics(
    env_file_vars: dict[str, str],
    reg: Registry,
) -> list[Finding]:
    """Apply registry-based heuristics for warnings."""
    findings: list[Finding] = []
    for k in sorted(env_file_vars.keys()):
        ent: RegistryEntry | None = reg.entries.get(k)
        if not ent:
            continue
        for a in ent.affects:
            if a.metric.value == "determinism" and a.impact.value in ("-", "--"):
                findings.append(
                    Finding(
                        id="ENV-DETERMINISM",
                        severity=Severity.WARN,
                        env=k,
                        message="Registry marks this as reducing determinism.",
                    )
                )
            if a.metric.value == "memory" and a.impact.value in ("+", "++"):
                findings.append(
                    Finding(
                        id="ENV-MEMORY",
                        severity=Severity.WARN,
                        env=k,
                        message="Registry marks this as increasing memory usage.",
                    )
                )
            if a.metric.value == "compatibility" and a.impact.value in ("-", "--"):
                findings.append(
                    Finding(
                        id="ENV-COMPAT",
                        severity=Severity.WARN,
                        env=k,
                        message="Registry marks this as reducing compatibility across GPUs/drivers.",
                    )
                )
    return findings


def _lint_rules_v1(
    effective: dict[str, str],
    rules: list[dict[str, Any]],
) -> list[Finding]:
    """Evaluate v1 DSL rules."""
    findings: list[Finding] = []
    for r in rules:
        rid = str(r.get("id") or "RULE")
        when = r.get("when") or {}
        if not isinstance(when, dict):
            continue
        if _eval_when(effective, when):
            then = r.get("then") or {}
            if not isinstance(then, dict):
                continue
            if "fail" in then:
                findings.append(Finding(id=rid, severity=Severity.FAIL, env=None, message=str(then["fail"])))
            elif "warn" in then:
                findings.append(Finding(id=rid, severity=Severity.WARN, env=None, message=str(then["warn"])))
            elif "info" in then:
                findings.append(Finding(id=rid, severity=Severity.INFO, env=None, message=str(then["info"])))
    return findings


def _lint_rules_v2_cel(
    effective: dict[str, str],
    overlay: dict[str, str],
    meta: dict[str, Any],
    rules: list[dict[str, Any]],
) -> list[Finding]:
    """Evaluate v2 CEL rules."""
    findings: list[Finding] = []
    ctx = {"env": effective, "overlay": overlay, "meta": meta}
    for r in rules:
        rid = str(r.get("id") or "RULE")
        sev_str = str(r.get("severity") or "WARN").upper()
        try:
            sev = Severity(sev_str)
        except ValueError:
            sev = Severity.WARN
        expr = r.get("when_cel")
        msg = r.get("message") or ""
        if not isinstance(expr, str):
            continue
        try:
            if eval_cel(expr, ctx):
                findings.append(Finding(id=rid, severity=sev, env=None, message=str(msg)))
        except CelError as e:
            findings.append(Finding(id=rid, severity=Severity.WARN, env=None, message=f"Rule evaluation error: {e}"))
    return findings


def lint_env(
    effective: dict[str, str],
    env_file_vars: dict[str, str],
    discovered_vars: list[str],
    reg: Registry,
    rules_doc: dict[str, Any],
) -> LintResult:
    """
    Lint environment variables against registry and rules.

    Args:
        effective: Effective environment (merged defaults + overlay)
        env_file_vars: Variables from user env file
        discovered_vars: Variables discovered in container
        reg: Environment variable registry
        rules_doc: Rules document from load_rules()

    Returns:
        LintResult with findings and overall status
    """
    findings: list[Finding] = []
    findings.extend(_lint_unknown_keys(env_file_vars, discovered_vars, reg))
    findings.extend(_lint_registry_heuristics(env_file_vars, reg))

    schema = str(rules_doc.get("schema_version") or "nim-audit/env-rules/v1")
    rules = rules_doc.get("rules") or []
    if not isinstance(rules, list):
        rules = []

    if schema.endswith("/v2") or any("when_cel" in r for r in rules if isinstance(r, dict)):
        known_vars = sorted(set(discovered_vars) | set(reg.entries.keys()))
        meta = {"known_vars": known_vars}
        findings.extend(_lint_rules_v2_cel(effective, env_file_vars, meta, rules))
    else:
        findings.extend(_lint_rules_v1(effective, rules))

    overall = "PASS"
    if any(f.severity == Severity.FAIL for f in findings):
        overall = "FAIL"
    elif any(f.severity == Severity.WARN for f in findings):
        overall = "WARN"

    counts = {
        "info": sum(1 for f in findings if f.severity == Severity.INFO),
        "warn": sum(1 for f in findings if f.severity == Severity.WARN),
        "fail": sum(1 for f in findings if f.severity == Severity.FAIL),
    }

    return LintResult(overall=overall, findings=findings, counts=counts)
