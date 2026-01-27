"""Container registry clients."""

from nim_audit.registry.base import (
    Registry,
    RegistryAuth,
    RegistryAuthError,
    RegistryError,
    RegistryNotFoundError,
)
from nim_audit.registry.docker import DockerRegistry
from nim_audit.registry.oci import OCIRegistry
from nim_audit.registry.ngc import NGCRegistry

__all__ = [
    "Registry",
    "RegistryAuth",
    "RegistryAuthError",
    "RegistryError",
    "RegistryNotFoundError",
    "DockerRegistry",
    "OCIRegistry",
    "NGCRegistry",
]
