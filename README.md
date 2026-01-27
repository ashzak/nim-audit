# nim-audit

A professional, modular Python tool for auditing NVIDIA NIM containers with CLI + library interfaces.

## Installation

```bash
pip install nim-audit
```

For development:
```bash
pip install -e ".[dev]"
```

## CLI Usage

```bash
# Compare two NIM versions
nim-audit diff nvcr.io/nim/llama3:1.5.0 nvcr.io/nim/llama3:1.6.0

# Analyze configuration
nim-audit config --image nvcr.io/nim/llama3:1.6.0 --env-file prod.env

# Check GPU compatibility
nim-audit compat --image nvcr.io/nim/llama3:1.6.0 --gpu A10 --driver 550.54

# Lint against policy
nim-audit lint --image nvcr.io/nim/llama3:1.6.0 --policy enterprise.yaml

# Cluster compatibility scan
nim-audit cluster --image nvcr.io/nim/llama3:1.6.0 --kubeconfig ~/.kube/config

# Generate behavioral fingerprint
nim-audit fingerprint --image nvcr.io/nim/llama3:1.6.0 --endpoint http://localhost:8000
```

## Library API

```python
from nim_audit import NIMImage, DiffEngine, ConfigAnalyzer, CompatChecker

# Load images
img1 = NIMImage.from_local("nvcr.io/nim/llama3:1.5.0")
img2 = NIMImage.from_local("nvcr.io/nim/llama3:1.6.0")

# Diff
engine = DiffEngine()
result = engine.diff(img1, img2)
print(result.report.breaking_changes)

# Config analysis
analyzer = ConfigAnalyzer()
config = analyzer.analyze(img2, env={"NIM_MAX_BATCH_SIZE": "64"})
for entry in config.report.entries:
    print(f"{entry.name}: {entry.impact}")

# Compatibility check
checker = CompatChecker()
result = checker.check(img2, gpu="A10", driver_version="550.54")
print(f"Compatible: {result.report.compatible}")
```

## Features

- **Diff Engine**: Compare container metadata, environment variables, layers, and detect breaking changes
- **Config Analyzer**: Analyze NIM environment variables with impact assessment
- **Compatibility Checker**: Validate GPU and driver requirements
- **Policy Linter**: Rule-based validation against enterprise policies
- **Behavioral Fingerprinting**: Generate and compare runtime signatures
- **Cluster Scanner**: Check compatibility across Kubernetes nodes

## License

MIT
