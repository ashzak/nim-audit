# nim-audit

A professional, modular Python tool for auditing NVIDIA NIM containers with CLI + library interfaces.

## Project Overview

nim-audit provides comprehensive auditing capabilities for NVIDIA NIM (NVIDIA Inference Microservices) containers, including:

- **Diff Engine**: Compare two NIM container versions to detect changes and breaking changes
- **Config Analyzer**: Analyze environment variables and configuration impacts
- **Compatibility Checker**: Verify GPU and driver compatibility
- **Policy Linter**: Validate containers against enterprise policies
- **Behavioral Fingerprinting**: Generate and compare runtime behavioral signatures

## Architecture

The project follows a modular, protocol-based architecture:

- **CLI Layer** (`cli/`): Typer-based command-line interface
- **Core Layer** (`core/`): Domain logic exposed as library API
- **Extractors** (`extractors/`): Pluggable artifact extractors from containers
- **Registry Clients** (`registry/`): Container registry integrations (Docker, OCI, NGC)
- **Renderers** (`renderers/`): Output format handlers (JSON, Markdown, HTML, Terminal)
- **Models** (`models/`): Pydantic data models (immutable/frozen)
- **Knowledge Base** (`knowledge/`): NIM-specific knowledge (env vars, GPU matrix, profiles)

## Key Design Principles

1. **Protocol-Based Extensibility**: All major components use Python Protocols
2. **Immutable Data Models**: Pydantic models with `frozen=True`
3. **Dependency Injection**: Core classes accept dependencies via constructor
4. **Result Types**: Operations return typed result objects, not exceptions

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run CLI
nim-audit --help
```

## Commands

- `nim-audit diff <image1> <image2>` - Compare two NIM versions
- `nim-audit config --image <image>` - Analyze configuration
- `nim-audit compat --image <image> --gpu <gpu>` - Check GPU compatibility
- `nim-audit lint --image <image> --policy <policy.yaml>` - Lint against policy
- `nim-audit cluster --image <image>` - Cluster compatibility scan
- `nim-audit fingerprint <image>` - Generate behavioral fingerprint
