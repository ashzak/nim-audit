"""NIM-specific knowledge base.

Contains curated information about NIM environment variables,
GPU compatibility, and optimized profiles.
"""

from nim_audit.knowledge.env_vars import get_env_var_knowledge
from nim_audit.knowledge.gpu_matrix import get_gpu_matrix
from nim_audit.knowledge.profiles import get_profiles

__all__ = [
    "get_env_var_knowledge",
    "get_gpu_matrix",
    "get_profiles",
]
