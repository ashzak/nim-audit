<p align="center">
  <h1 align="center">nim-audit</h1>
  <p align="center">
    <strong>Stop deploying NIM containers blind.</strong>
  </p>
  <p align="center">
    A professional CLI tool for auditing NVIDIA NIM containers before they hit production.
  </p>
</p>

<p align="center">
  <a href="https://github.com/ashzak/nim-audit/blob/main/LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <a href="https://www.python.org/downloads/"><img src="https://img.shields.io/badge/python-3.11+-blue.svg" alt="Python"></a>
  <a href="https://github.com/ashzak/nim-audit/stargazers"><img src="https://img.shields.io/github/stars/ashzak/nim-audit?style=social" alt="Stars"></a>
</p>

<p align="center">
  <a href="#installation">Installation</a> •
  <a href="#quick-start">Quick Start</a> •
  <a href="#commands">Commands</a> •
  <a href="docs/USER_GUIDE.md">User Guide</a>
</p>

---

## Why nim-audit?

Ever upgraded a NIM container and had everything crash 10 minutes later?

**nim-audit catches what humans miss:**

- 🔄 **Breaking changes** between container versions
- 🎮 **GPU compatibility** issues before deployment
- ⚙️ **Environment variable** risks and impacts
- 📋 **Policy violations** that slip through review
- 🔍 **Behavioral drift** between model versions

One command before every upgrade. Never be surprised again.

---

## Installation

```bash
pip install nim-audit
```

**Requirements:** Python 3.11+

For development:
```bash
git clone https://github.com/ashzak/nim-audit.git
cd nim-audit
pip install -e ".[dev]"
```

---

## Quick Start

### Compare versions before upgrading

```bash
nim-audit diff nvcr.io/nim/llama3:1.0.0 nvcr.io/nim/llama3:1.1.0
```

```
╭─────────────────────────── Diff Report ───────────────────────────╮
│ Source: nvcr.io/nim/llama3:1.0.0                                  │
│ Target: nvcr.io/nim/llama3:1.1.0                                  │
╰───────────────────────────────────────────────────────────────────╯

⚠️  Breaking Changes Detected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• API: /v1/completions response schema changed
• Config: NIM_MAX_BATCH_SIZE default: 4 → 8
• Requirement: Min GPU memory increased to 24GB
```

### Check GPU compatibility

```bash
nim-audit compat --image nvcr.io/nim/llama3:1.1.0 --gpu A10
```

```
╭─────────────────────── Compatibility Report ────────────────────────╮
│ Image: nvcr.io/nim/llama3:1.1.0                                     │
│ Status: ✅ COMPATIBLE                                               │
╰─────────────────────────────────────────────────────────────────────╯
```

### Lint your environment file

```bash
nim-audit env lint --env-file production.env
```

```
╭───────────────────── Environment Lint Report ───────────────────────╮
│ Status: ⚠️  WARN                                                    │
╰─────────────────────────────────────────────────────────────────────╯

┃ Severity ┃ Variable           ┃ Message                             ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ WARN     │ NIM_MAX_BATCH_SIZE │ Registry marks as increasing memory │
```

---

## Commands

| Command | Description |
|---------|-------------|
| [`diff`](#diff) | Compare two NIM versions, detect breaking changes |
| [`config`](#config) | Analyze configuration with impact assessment |
| [`compat`](#compat) | Check GPU and driver compatibility |
| [`lint`](#lint) | Validate against enterprise policies |
| [`fingerprint`](#fingerprint) | Compare runtime behavioral signatures |
| [`cluster`](#cluster) | Scan Kubernetes cluster compatibility |
| [`env`](#env) | Environment variable analysis suite |

---

### `diff`

Compare two NIM container versions:

```bash
# Basic diff
nim-audit diff old:tag new:tag

# Only breaking changes
nim-audit diff old:tag new:tag --breaking-only

# JSON output for CI/CD
nim-audit diff old:tag new:tag --format json --output report.json

# Filter by category
nim-audit diff old:tag new:tag --category api
```

**Categories:** `metadata`, `model`, `tokenizer`, `api`, `runtime`, `layer`, `config`, `environment`

---

### `config`

Analyze NIM configuration and environment variables:

```bash
# Analyze image configuration
nim-audit config --image nvcr.io/nim/llama3:1.1.0

# With your env file
nim-audit config --image nvcr.io/nim/llama3:1.1.0 --env-file prod.env

# Validate configuration
nim-audit config --image nvcr.io/nim/llama3:1.1.0 --env-file prod.env --validate

# Show all options including defaults
nim-audit config --image nvcr.io/nim/llama3:1.1.0 --all
```

---

### `compat`

Check GPU and driver compatibility:

```bash
# Check specific GPU
nim-audit compat --image nvcr.io/nim/llama3:1.1.0 --gpu A100

# With driver version
nim-audit compat --image nvcr.io/nim/llama3:1.1.0 --gpu A10 --driver 535.104.05

# Auto-detect local GPU
nim-audit compat --image nvcr.io/nim/llama3:1.1.0 --detect
```

**Supported GPUs:** A10, A100, H100, L4, L40, L40S, T4, V100, A6000, RTX 4090, RTX 6000

---

### `lint`

Validate containers against policies:

```bash
# Lint with built-in rules
nim-audit lint --image nvcr.io/nim/llama3:1.1.0

# Custom enterprise policy
nim-audit lint --image nvcr.io/nim/llama3:1.1.0 --policy enterprise.yaml

# Only show errors
nim-audit lint --image nvcr.io/nim/llama3:1.1.0 --severity error
```

**Built-in rules:**
- `nim-001`: Require version label
- `nim-002`: No root user
- `nim-003`: Require model name
- `nim-004`: Check exposed ports
- `nim-005`: No sensitive environment variables

<details>
<summary><strong>Custom Policy Example</strong></summary>

```yaml
name: enterprise-policy
version: "1.0.0"

rules:
  - id: ent-001
    name: require-security-scan
    description: Image must have security scan label
    severity: error
    condition: labels['security.scan.status'] == 'passed'
    remediation: Run security scan and add label

  - id: ent-002
    name: max-batch-size
    description: Batch size must not exceed 64
    severity: warning
    condition: int(env.get('NIM_MAX_BATCH_SIZE', '1')) <= 64
```

</details>

---

### `fingerprint`

Generate and compare behavioral signatures:

```bash
# Generate fingerprint from running container
nim-audit fingerprint --image nvcr.io/nim/llama3:1.0.0 \
                      --endpoint http://localhost:8000 \
                      --output v1.0.0.json

# Compare two fingerprints
nim-audit fingerprint compare v1.0.0.json v1.1.0.json --tolerance 0.05
```

---

### `cluster`

Scan Kubernetes cluster for NIM compatibility:

```bash
# Scan cluster
nim-audit cluster --image nvcr.io/nim/llama3:1.1.0

# Specific context
nim-audit cluster --image nvcr.io/nim/llama3:1.1.0 --context production
```

---

### `env`

Environment variable analysis tools:

```bash
# Lint environment file
nim-audit env lint --env-file prod.env

# Describe a variable
nim-audit env describe NIM_MAX_BATCH_SIZE

# Diff two env files
nim-audit env diff staging.env production.env

# List all known variables
nim-audit env registry-list
```

---

## Library API

Use nim-audit programmatically:

```python
from nim_audit import NIMImage, DiffEngine, ConfigAnalyzer, CompatChecker

# Load images
img1 = NIMImage.from_local("nvcr.io/nim/llama3:1.0.0")
img2 = NIMImage.from_local("nvcr.io/nim/llama3:1.1.0")

# Diff
engine = DiffEngine()
result = engine.diff(img1, img2)
for bc in result.report.breaking_changes:
    print(f"Breaking: {bc.title}")

# Config analysis
analyzer = ConfigAnalyzer()
result = analyzer.analyze(img2, env={"NIM_MAX_BATCH_SIZE": "64"})
for entry in result.report.entries:
    print(f"{entry.name}: {entry.impact.level}")

# Compatibility
checker = CompatChecker()
result = checker.check(img2, gpu="A100")
print(f"Compatible: {result.report.compatible}")
```

---

## CI/CD Integration

Add nim-audit to your pipeline:

```yaml
# .github/workflows/nim-validate.yml
name: NIM Validation

on:
  pull_request:
    paths:
      - 'k8s/nim/*.yaml'
      - '.env.nim'

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install nim-audit
        run: pip install nim-audit

      - name: Lint environment
        run: nim-audit env lint --env-file .env.nim

      - name: Check compatibility
        run: nim-audit compat --image ${{ vars.NIM_IMAGE }} --gpu A100

      - name: Policy check
        run: nim-audit lint --image ${{ vars.NIM_IMAGE }} --policy policies/enterprise.yaml
```

---

## Configuration

Create `~/.nim-audit.yaml`:

```yaml
cache:
  enabled: true
  ttl: 3600

registry:
  ngc_api_key: ${NGC_API_KEY}

output:
  default_format: terminal
  color: true

lint:
  include_builtin: true
  fail_on_warning: false

# Shortcuts for common images
aliases:
  llama3: nvcr.io/nim/meta/llama3-8b-instruct:latest
  llama3-70b: nvcr.io/nim/meta/llama3-70b-instruct:latest
```

**Environment Variables:**
- `NGC_API_KEY`: NVIDIA NGC API key
- `NIM_AUDIT_CONFIG`: Config file override
- `NIM_AUDIT_NO_COLOR`: Disable colors

---

## Documentation

- **[User Guide](docs/USER_GUIDE.md)** - Comprehensive usage documentation
- **[CLI Reference](docs/USER_GUIDE.md#commands-reference)** - All commands and options

---

## Architecture

```
nim-audit/
├── src/nim_audit/
│   ├── cli/          # CLI commands (Typer)
│   ├── core/         # Core domain logic
│   │   └── env/      # Environment analysis
│   ├── extractors/   # Artifact extractors
│   ├── registry/     # Container registry clients
│   ├── renderers/    # Output formatters
│   ├── models/       # Pydantic data models
│   ├── knowledge/    # NIM knowledge base
│   └── utils/        # Utilities
└── tests/
    ├── unit/         # Unit tests
    └── integration/  # Integration tests
```

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Make your changes
4. Run tests (`pytest`)
5. Submit a pull request

---

## License

[MIT](LICENSE) - Use it however you want.

---

<p align="center">
  <strong>Built to prevent production incidents.</strong><br>
  <sub>Star ⭐ if this saved you from a 3am page.</sub>
</p>
