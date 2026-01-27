# nim-audit

A professional, modular Python tool for auditing NVIDIA NIM containers with CLI + library interfaces.

## Features

- **Diff Engine**: Compare container metadata, environment variables, layers, and detect breaking changes
- **Config Analyzer**: Analyze NIM environment variables with impact assessment
- **Compatibility Checker**: Validate GPU and driver requirements against NVIDIA's compatibility matrix
- **Policy Linter**: Rule-based validation against enterprise policies with custom rule support
- **Behavioral Fingerprinting**: Generate and compare runtime behavioral signatures
- **Cluster Scanner**: Check compatibility across Kubernetes nodes

## Installation

```bash
pip install nim-audit
```

For development:
```bash
pip install -e ".[dev]"
```

## Quick Start

### CLI Usage

```bash
# Compare two NIM versions
nim-audit diff nvcr.io/nim/llama3:1.5.0 nvcr.io/nim/llama3:1.6.0

# Analyze configuration
nim-audit config --image nvcr.io/nim/llama3:1.6.0 --env-file prod.env

# Check GPU compatibility
nim-audit compat --image nvcr.io/nim/llama3:1.6.0 --gpu A100 --driver 550.54

# Lint against policy
nim-audit lint --image nvcr.io/nim/llama3:1.6.0 --policy enterprise.yaml

# Cluster compatibility scan
nim-audit cluster --image nvcr.io/nim/llama3:1.6.0 --kubeconfig ~/.kube/config

# Generate behavioral fingerprint
nim-audit fingerprint --image nvcr.io/nim/llama3:1.6.0 --endpoint http://localhost:8000
```

### Library API

```python
from nim_audit import NIMImage, DiffEngine, ConfigAnalyzer, CompatChecker, PolicyLinter

# Load images
img1 = NIMImage.from_local("nvcr.io/nim/llama3:1.5.0")
img2 = NIMImage.from_local("nvcr.io/nim/llama3:1.6.0")

# Diff two images
engine = DiffEngine()
result = engine.diff(img1, img2)
if result.success:
    print(f"Total changes: {result.report.total_changes}")
    for bc in result.report.breaking_changes:
        print(f"Breaking: {bc.title}")

# Config analysis
analyzer = ConfigAnalyzer()
config_result = analyzer.analyze(img2, env={"NIM_MAX_BATCH_SIZE": "64"})
for entry in config_result.report.entries:
    print(f"{entry.name}: {entry.value} (impact: {entry.impact})")

# Compatibility check
checker = CompatChecker()
compat_result = checker.check(img2, gpu="A100", driver_version="550.54")
print(f"Compatible: {compat_result.report.compatible}")

# Policy linting
linter = PolicyLinter()
lint_result = linter.lint(img2)
for violation in lint_result.violations:
    print(f"{violation.rule.severity}: {violation.message}")
```

## Detailed Usage

### Diff Command

Compare two NIM container versions to detect changes:

```bash
# Basic diff
nim-audit diff old:tag new:tag

# JSON output
nim-audit diff old:tag new:tag --format json --output report.json

# Show only breaking changes
nim-audit diff old:tag new:tag --breaking-only

# Filter by category
nim-audit diff old:tag new:tag --category environment
```

Categories: `metadata`, `model`, `tokenizer`, `api`, `runtime`, `layer`, `config`, `environment`

### Config Command

Analyze NIM configuration and environment variables:

```bash
# Analyze image configuration
nim-audit config --image nvcr.io/nim/llama3:1.6.0

# With environment overrides
nim-audit config --image nvcr.io/nim/llama3:1.6.0 --env NIM_MAX_BATCH_SIZE=64

# With env file
nim-audit config --image nvcr.io/nim/llama3:1.6.0 --env-file production.env

# Show only high-impact settings
nim-audit config --image nvcr.io/nim/llama3:1.6.0 --high-impact-only
```

### Compat Command

Check GPU and driver compatibility:

```bash
# Check with specific GPU
nim-audit compat --image nvcr.io/nim/llama3:1.6.0 --gpu A100

# With driver version
nim-audit compat --image nvcr.io/nim/llama3:1.6.0 --gpu A100 --driver 550.54.15

# With CUDA version
nim-audit compat --image nvcr.io/nim/llama3:1.6.0 --gpu H100 --cuda 12.2
```

Supported GPUs: A10, A100, H100, L4, L40, L40S, T4, V100, A6000, RTX 4090, RTX 6000

### Lint Command

Validate images against policies:

```bash
# Lint with built-in rules
nim-audit lint --image nvcr.io/nim/llama3:1.6.0

# With custom policy
nim-audit lint --image nvcr.io/nim/llama3:1.6.0 --policy enterprise.yaml

# Exclude built-in rules
nim-audit lint --image nvcr.io/nim/llama3:1.6.0 --policy custom.yaml --no-builtin
```

Built-in rules:
- `nim-001`: Require version label
- `nim-002`: No root user
- `nim-003`: Require model name
- `nim-004`: Check exposed ports
- `nim-005`: No sensitive environment variables

### Custom Policies

Create custom policy files in YAML:

```yaml
name: enterprise-policy
version: "1.0.0"
description: Enterprise compliance rules

rules:
  - id: ent-001
    name: require-support-label
    description: Images must have support contact label
    severity: error
    category: metadata
    condition: "labels.get('support.contact') is not None"
    rationale: Support contact required for enterprise deployment
    remediation: Add support.contact label to image

  - id: ent-002
    name: max-batch-size
    description: Batch size must not exceed 64
    severity: warning
    category: configuration
    condition: "int(env.get('NIM_MAX_BATCH_SIZE', '1')) <= 64"
    rationale: Large batch sizes may cause memory issues
    remediation: Reduce NIM_MAX_BATCH_SIZE to 64 or less
```

## Configuration

nim-audit can be configured via YAML files in these locations (in order of precedence):

1. `.nim-audit.yaml` in current directory
2. `~/.nim-audit.yaml`
3. `~/.nim-audit/config.yaml`
4. `~/.config/nim-audit/config.yaml`

Example configuration:

```yaml
cache:
  enabled: true
  directory: ~/.cache/nim-audit
  ttl: 3600

registry:
  default_registry: ngc
  ngc_api_key: ${NGC_API_KEY}

output:
  default_format: terminal
  color: true
  verbose: false

lint:
  include_builtin: true
  default_policy: ~/.nim-audit/enterprise.yaml
  fail_on_warning: false

plugins:
  - my_custom_plugin
  - company_nim_rules

aliases:
  llama: nvcr.io/nim/llama3:latest
  mistral: nvcr.io/nim/mistral:latest
```

## Plugins

nim-audit supports plugins for extending functionality:

```python
# my_plugin.py
from nim_audit.utils.plugins import PluginContext

class MyPlugin:
    name = "my-plugin"
    version = "1.0.0"

    def init(self, context: PluginContext) -> None:
        # Register custom extractor
        context.register_extractor(MyCustomExtractor())

        # Register custom renderer
        context.register_renderer("custom", MyRenderer())

        # Register hooks
        context.register_hook("before_diff", self.on_diff)

    def on_diff(self, source, target):
        print(f"Diffing {source} and {target}")

    def cleanup(self) -> None:
        pass

plugin = MyPlugin()
```

Load plugins via config or CLI:

```bash
nim-audit --plugin my_plugin diff img1 img2
```

## Output Formats

All commands support multiple output formats:

- `terminal`: Rich terminal output with colors (default)
- `json`: Machine-readable JSON
- `markdown`: Markdown report

```bash
nim-audit diff img1 img2 --format json --output report.json
nim-audit lint --image img --format markdown --output report.md
```

## Environment Variables

- `NGC_API_KEY`: NVIDIA NGC API key for registry authentication
- `DOCKER_CONFIG`: Path to Docker config for registry auth
- `NIM_AUDIT_CONFIG`: Path to config file
- `NIM_AUDIT_CACHE_DIR`: Cache directory override
- `NIM_AUDIT_NO_COLOR`: Disable colored output

## Development

```bash
# Clone repository
git clone https://github.com/example/nim-audit.git
cd nim-audit

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=nim_audit

# Type checking
mypy src/nim_audit

# Linting
ruff check src/nim_audit
```

## Architecture

```
nim-audit/
├── src/nim_audit/
│   ├── cli/          # CLI commands (Typer)
│   ├── core/         # Core domain logic
│   ├── extractors/   # Pluggable artifact extractors
│   ├── registry/     # Container registry clients
│   ├── renderers/    # Output format handlers
│   ├── models/       # Pydantic data models
│   ├── knowledge/    # NIM-specific knowledge base
│   └── utils/        # Utilities
└── tests/
    ├── unit/
    └── integration/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

MIT
