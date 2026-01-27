"""Environment variable discovery from container filesystems."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Callable

from nim_audit.models.env import DiscoveredVar, DiscoveryResult, Evidence

DEFAULT_PREFIXES = ["NIM", "TRT", "CUDA", "NCCL"]
SCAN_EXTS = (".sh", ".bash", ".py", ".json", ".yaml", ".yml", ".toml", ".ini", ".conf", ".txt")
SCAN_ROOT_HINTS = ("/etc/nim/", "/opt/nim/", "/usr/local/bin/", "/bin/", "/app/")


class ExtractedFile:
    """Represents a file extracted from a container layer."""

    def __init__(self, path: str, content: bytes):
        self.path = path
        self.content = content


class FilesystemView(ABC):
    """Abstract filesystem view for reading container layers."""

    @abstractmethod
    def search_filenames(self, predicate: Callable[[str], bool]) -> list[str]:
        """Search for files matching a predicate."""
        ...

    @abstractmethod
    def find_latest_file(self, path: str) -> ExtractedFile | None:
        """Get the latest version of a file from the layers."""
        ...


class MemoryFilesystemView(FilesystemView):
    """In-memory filesystem view for testing."""

    def __init__(self, files: dict[str, bytes]):
        self._files = files

    def search_filenames(self, predicate: Callable[[str], bool]) -> list[str]:
        return [p for p in self._files.keys() if predicate(p)]

    def find_latest_file(self, path: str) -> ExtractedFile | None:
        if path in self._files:
            return ExtractedFile(path, self._files[path])
        return None


def _boost_for_path(p: str) -> float:
    """Calculate a path boost score based on location."""
    b = 0.0
    if p.startswith(("/bin/", "/usr/local/bin/", "/opt/nim/bin/")):
        b += 3.0
    if p.startswith(("/etc/nim/", "/opt/nim/")):
        b += 2.0
    if p.endswith((".sh", ".bash")):
        b += 1.5
    return b


def _signals(text: str, var: str) -> dict[str, int]:
    """Extract signal types for a variable from text."""
    cond = len(re.findall(r"\$\{\s*%s\s*[:-]" % re.escape(var), text))
    defaults = len(re.findall(r"\b(export\s+)?%s\s*=" % re.escape(var), text))
    help_hits = len(re.findall(r"(--help|usage:|Options:)", text, flags=re.IGNORECASE))
    return {"conditional": cond, "assignment": defaults, "help_context": help_hits}


def discover_env_vars(
    fs: FilesystemView,
    include_prefixes: list[str] | None = None,
    max_files: int = 400,
) -> DiscoveryResult:
    """
    Discover environment variables from a container filesystem.

    Args:
        fs: Filesystem view to scan
        include_prefixes: Variable prefixes to search for (default: NIM, TRT, CUDA, NCCL)
        max_files: Maximum number of files to scan

    Returns:
        DiscoveryResult with discovered variables and their evidence
    """
    prefixes = include_prefixes or DEFAULT_PREFIXES
    prefixes = [p.strip().upper() for p in prefixes if p and p.strip()]
    if not prefixes:
        prefixes = DEFAULT_PREFIXES

    var_regex = re.compile(
        r"\b(" + "|".join(re.escape(p) for p in prefixes) + r")_[A-Z0-9_]{2,}\b"
    )

    # Find candidate files
    candidates = fs.search_filenames(
        lambda p: p.endswith(SCAN_EXTS) and any(p.startswith(h) for h in SCAN_ROOT_HINTS)
    )
    special = fs.search_filenames(
        lambda p: "runtime_params" in p or "model_manifest" in p
    )
    for p in special:
        if p not in candidates:
            candidates.append(p)
    candidates = sorted(candidates)[:max_files]

    agg: dict[str, list[Evidence]] = {}
    files_scanned = 0

    for path in candidates:
        ef = fs.find_latest_file(path)
        if not ef:
            continue
        files_scanned += 1
        text = ef.content.decode("utf-8", errors="ignore")
        matches = list(var_regex.finditer(text))
        if not matches:
            continue

        per: dict[str, int] = {}
        for m in matches:
            v = m.group(0)
            per[v] = per.get(v, 0) + 1

        for v, cnt in per.items():
            sig = _signals(text, v)
            snippets: list[str] = []
            for m in matches[:10]:
                if m.group(0) != v:
                    continue
                start = max(0, m.start() - 40)
                end = min(len(text), m.end() + 40)
                snippet = text[start:end].replace("\n", " ")[:160]
                snippets.append(snippet)
                if len(snippets) >= 3:
                    break
            score = (
                float(cnt)
                + _boost_for_path(path)
                + 1.0 * sig["assignment"]
                + 1.5 * sig["conditional"]
                + (0.5 if sig["help_context"] else 0.0)
            )
            evidence = Evidence(
                path=path,
                count=cnt,
                score=score,
                sample_snippets=snippets,
                signals=sig,
            )
            agg.setdefault(v, []).append(evidence)

    vars_out: list[DiscoveredVar] = []
    for v, evs in agg.items():
        total = sum(e.score for e in evs)
        sorted_evs = sorted(evs, key=lambda e: e.score, reverse=True)
        vars_out.append(DiscoveredVar(name=v, score=total, evidences=sorted_evs))

    vars_out = sorted(vars_out, key=lambda x: x.score, reverse=True)
    return DiscoveryResult(prefixes=prefixes, vars=vars_out, files_scanned=files_scanned)
