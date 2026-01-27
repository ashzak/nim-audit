# nim-audit User Guide

A professional CLI tool for auditing NVIDIA NIM (NVIDIA Inference Microservices) containers.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Commands Reference](#commands-reference)
  - [diff](#diff---compare-container-versions)
  - [config](#config---analyze-configuration)
  - [compat](#compat---check-gpu-compatibility)
  - [lint](#lint---policy-validation)
  - [fingerprint](#fingerprint---behavioral-analysis)
  - [cluster](#cluster---kubernetes-compatibility)
  - [env](#env---environment-variable-tools)
- [Real-World Use Cases](#real-world-use-cases)
- [Configuration](#configuration)
- [Output Formats](#output-formats)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Python**: 3.11 or higher
- **Operating System**: Linux, macOS, or Windows
- **Docker**: Required for local image inspection (optional for registry-only operations)
- **kubectl**: Required for cluster scanning (optional)

### For NVIDIA NGC Registry Access

- NVIDIA NGC account (free at [ngc.nvidia.com](https://ngc.nvidia.com))
- NGC API key (generate from NGC dashboard)

### For Kubernetes Cluster Scanning

- Valid kubeconfig with cluster access
- kubectl installed and configured

---

## Installation

### From Source (Development)

```bash
# Clone the repository
git clone https://github.com/your-org/nim-audit.git
cd nim-audit

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install in development mode
pip install -e .

# Verify installation
nim-audit --help
```

### Dependencies

The tool automatically installs these dependencies:
- **typer** - CLI framework
- **rich** - Terminal formatting
- **pydantic** - Data validation
- **docker** - Docker SDK
- **httpx** - HTTP client for registries
- **PyYAML** - YAML parsing

---

## Quick Start

### 1. Compare Two NIM Versions

```bash
# See what changed between versions
nim-audit diff nvcr.io/nim/meta/llama3-8b-instruct:1.0.0 \
               nvcr.io/nim/meta/llama3-8b-instruct:1.1.0
```

### 2. Check GPU Compatibility

```bash
# Will my A10 GPU work with this image?
nim-audit compat --image nvcr.io/nim/meta/llama3-8b-instruct:1.1.0 --gpu A10
```

### 3. Analyze Configuration

```bash
# Understand the impact of my environment settings
nim-audit config --image nvcr.io/nim/meta/llama3-8b-instruct:1.1.0 \
                 --env-file production.env
```

### 4. Lint Environment Variables

```bash
# Check my .env file for issues
nim-audit env lint --env-file production.env
```

---

## Commands Reference

### `diff` - Compare Container Versions

Compare two NIM container versions to understand what changed.

**Usage:**
```bash
nim-audit diff <source-image> <target-image> [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--format, -f` | Output format: terminal, json, markdown (default: terminal) |
| `--output, -o` | Write output to file |
| `--breaking-only` | Only show breaking changes |
| `--category, -c` | Filter by category (metadata, model, api, config, etc.) |

**Examples:**

```bash
# Basic diff between versions
nim-audit diff nvcr.io/nim/llama3:1.0.0 nvcr.io/nim/llama3:1.1.0

# Only show breaking changes
nim-audit diff nvcr.io/nim/llama3:1.0.0 nvcr.io/nim/llama3:1.1.0 --breaking-only

# Output as JSON for CI/CD pipelines
nim-audit diff nvcr.io/nim/llama3:1.0.0 nvcr.io/nim/llama3:1.1.0 \
    --format json --output diff-report.json

# Filter to only API changes
nim-audit diff nvcr.io/nim/llama3:1.0.0 nvcr.io/nim/llama3:1.1.0 \
    --category api

# Generate markdown report
nim-audit diff nvcr.io/nim/llama3:1.0.0 nvcr.io/nim/llama3:1.1.0 \
    --format markdown --output UPGRADE_NOTES.md
```

**Sample Output:**
```
╭─────────────────────────── Diff Report ───────────────────────────╮
│ Source: nvcr.io/nim/llama3:1.0.0                                  │
│ Target: nvcr.io/nim/llama3:1.1.0                                  │
╰───────────────────────────────────────────────────────────────────╯

              Summary
┌──────────────────┬───────┐
│ Total Changes    │ 12    │
│ Added            │ 3     │
│ Removed          │ 1     │
│ Modified         │ 8     │
│ Breaking Changes │ 2     │
└──────────────────┴───────┘

⚠️  Breaking Changes
┏━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Category    ┃ Description                                        ┃
┡━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ api         │ Endpoint /v1/chat/completions response format...   │
│ environment │ NIM_MAX_BATCH_SIZE default changed from 4 to 8     │
└─────────────┴────────────────────────────────────────────────────┘
```

---

### `config` - Analyze Configuration

Analyze NIM container configuration with impact assessment.

**Usage:**
```bash
nim-audit config --image <image> [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--image, -i` | NIM image reference (required) |
| `--env-file, -e` | Path to .env file to analyze |
| `--format, -f` | Output format: terminal, json (default: terminal) |
| `--output, -o` | Write output to file |
| `--validate` | Validate configuration values |
| `--all, -a` | Show all options including unset |

**Examples:**

```bash
# Basic configuration analysis
nim-audit config --image nvcr.io/nim/llama3:1.1.0

# Analyze with your production environment file
nim-audit config --image nvcr.io/nim/llama3:1.1.0 \
                 --env-file production.env

# Validate configuration values
nim-audit config --image nvcr.io/nim/llama3:1.1.0 \
                 --env-file production.env --validate

# Show all config options (including defaults)
nim-audit config --image nvcr.io/nim/llama3:1.1.0 --all

# Export as JSON for documentation
nim-audit config --image nvcr.io/nim/llama3:1.1.0 \
                 --format json --output config-doc.json
```

**Sample Output:**
```
╭──────────────────────── NIM Config Analysis ─────────────────────────╮
│ Image: nvcr.io/nim/llama3:1.1.0                                      │
╰──────────────────────────────────────────────────────────────────────╯

⚠️  Warnings
  ! NIM_MAX_BATCH_SIZE=64 may cause OOM on GPUs with <40GB memory

                         Configuration
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ Variable              ┃ Value ┃ Default ┃ Impact   ┃ Description   ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ NIM_MAX_BATCH_SIZE    │ 64    │ 4       │ HIGH     │ Maximum batch │
│ NIM_LOG_LEVEL         │ INFO  │ INFO    │ LOW      │ Logging level │
│ NIM_TENSOR_PARALLEL   │ 2     │ 1       │ MEDIUM   │ Tensor paral. │
└───────────────────────┴───────┴─────────┴──────────┴───────────────┘

Recommendations
  - Consider reducing NIM_MAX_BATCH_SIZE for lower memory usage
  - NIM_TENSOR_PARALLEL=2 requires multi-GPU setup
```

---

### `compat` - Check GPU Compatibility

Verify GPU and driver compatibility before deployment.

**Usage:**
```bash
nim-audit compat --image <image> [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--image, -i` | NIM image reference (required) |
| `--gpu, -g` | Target GPU (A100, H100, L4, A10, T4, etc.) |
| `--driver, -d` | NVIDIA driver version |
| `--cuda, -c` | CUDA version |
| `--format, -f` | Output format: terminal, json |
| `--detect` | Auto-detect local GPU and driver |

**Supported GPUs:**
A10, A100, H100, L4, L40, L40S, T4, V100, A6000, RTX 4090, RTX 6000

**Examples:**

```bash
# Check compatibility with A100 GPU
nim-audit compat --image nvcr.io/nim/llama3:1.1.0 --gpu A100

# Check with specific driver version
nim-audit compat --image nvcr.io/nim/llama3:1.1.0 \
                 --gpu A10 --driver 535.104.05

# Auto-detect local GPU configuration
nim-audit compat --image nvcr.io/nim/llama3:1.1.0 --detect

# Check multiple requirements
nim-audit compat --image nvcr.io/nim/llama3:1.1.0 \
                 --gpu L4 --driver 525.85.12 --cuda 12.0

# JSON output for automation
nim-audit compat --image nvcr.io/nim/llama3:1.1.0 \
                 --gpu A10 --format json
```

**Sample Output:**
```
╭─────────────────────── Compatibility Report ────────────────────────╮
│ Image: nvcr.io/nim/llama3:1.1.0                                     │
│ Status: ✅ COMPATIBLE                                               │
╰─────────────────────────────────────────────────────────────────────╯

                    Requirements Check
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Requirement            ┃ Required   ┃ Actual     ┃ Status    ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━┩
│ Compute Capability     │ >= 8.0     │ 8.6        │ ✅ Pass   │
│ GPU Memory             │ >= 24 GB   │ 24 GB      │ ✅ Pass   │
│ Driver Version         │ >= 525.0   │ 535.104    │ ✅ Pass   │
│ GPU Model              │ Supported  │ A10        │ ✅ Pass   │
└────────────────────────┴────────────┴────────────┴───────────┘
```

**Exit Codes:**
- `0`: Compatible
- `1`: Not compatible (for CI/CD integration)

---

### `lint` - Policy Validation

Validate containers against enterprise policies.

**Usage:**
```bash
nim-audit lint --image <image> [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--image, -i` | NIM image reference (required) |
| `--policy, -p` | Custom policy YAML file |
| `--format, -f` | Output format: terminal, json |
| `--no-builtin` | Disable built-in rules |
| `--severity, -s` | Minimum severity: info, warning, error |

**Built-in Rules:**
| Rule ID | Description |
|---------|-------------|
| `nim-001` | Require version label |
| `nim-002` | Container must not run as root |
| `nim-003` | Require model name label |
| `nim-004` | Check exposed ports |
| `nim-005` | No sensitive environment variables |

**Examples:**

```bash
# Basic lint with built-in rules
nim-audit lint --image nvcr.io/nim/llama3:1.1.0

# Apply custom enterprise policy
nim-audit lint --image nvcr.io/nim/llama3:1.1.0 \
               --policy enterprise-policy.yaml

# Only show errors (skip warnings and info)
nim-audit lint --image nvcr.io/nim/llama3:1.1.0 --severity error

# Disable built-in rules, use only custom
nim-audit lint --image nvcr.io/nim/llama3:1.1.0 \
               --policy custom.yaml --no-builtin

# JSON output for CI/CD
nim-audit lint --image nvcr.io/nim/llama3:1.1.0 --format json
```

**Custom Policy Example (`enterprise-policy.yaml`):**
```yaml
name: Enterprise NIM Policy
version: 1.0.0
description: Enterprise security and compliance rules

rules:
  - id: ent-001
    name: require-security-scan
    description: Image must have security scan label
    severity: error
    condition: labels['security.scan.status'] == 'passed'
    remediation: Run security scan and add label

  - id: ent-002
    name: max-image-size
    description: Image size must be under 50GB
    severity: warning
    condition: total_size < 50_000_000_000
    remediation: Optimize image layers to reduce size
```

**Sample Output:**
```
╭──────────────────────────── Lint Report ────────────────────────────╮
│ Image: nvcr.io/nim/llama3:1.1.0                                     │
│ Policy: Enterprise NIM Policy v1.0.0                                │
│ Status: ❌ FAILED                                                   │
╰─────────────────────────────────────────────────────────────────────╯

           Summary
┌──────────────┬─────┐
│ Total Rules  │ 7   │
│ Errors       │ 1   │
│ Warnings     │ 2   │
│ Info         │ 0   │
└──────────────┴─────┘

                              Violations
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Severity  ┃ Rule                   ┃ Remediation                     ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ ERROR     │ require-security-scan  │ Run security scan and add label │
│ WARNING   │ max-image-size         │ Optimize image layers           │
│ WARNING   │ nim-002                │ Use non-root user               │
└───────────┴────────────────────────┴─────────────────────────────────┘
```

---

### `fingerprint` - Behavioral Analysis

Generate and compare behavioral fingerprints of running NIM containers.

**Usage:**
```bash
# Generate fingerprint
nim-audit fingerprint --image <image> --endpoint <url>

# Compare fingerprints
nim-audit fingerprint compare <source.json> <target.json>
```

**Options (generate):**
| Option | Description |
|--------|-------------|
| `--image, -i` | NIM image reference (required) |
| `--endpoint, -e` | Running NIM endpoint URL (required) |
| `--output, -o` | Save fingerprint to file |
| `--format, -f` | Output format: terminal, json |

**Options (compare):**
| Option | Description |
|--------|-------------|
| `--tolerance, -t` | Similarity tolerance 0.0-1.0 (default: 0.05) |
| `--format, -f` | Output format: terminal, json |

**Examples:**

```bash
# Generate fingerprint from running container
nim-audit fingerprint --image nvcr.io/nim/llama3:1.0.0 \
                      --endpoint http://localhost:8000 \
                      --output v1.0.0-fingerprint.json

# Generate fingerprint for new version
nim-audit fingerprint --image nvcr.io/nim/llama3:1.1.0 \
                      --endpoint http://localhost:8000 \
                      --output v1.1.0-fingerprint.json

# Compare behavioral differences
nim-audit fingerprint compare v1.0.0-fingerprint.json \
                              v1.1.0-fingerprint.json

# Stricter comparison (1% tolerance)
nim-audit fingerprint compare v1.0.0-fingerprint.json \
                              v1.1.0-fingerprint.json \
                              --tolerance 0.01
```

**Sample Output:**
```
╭─────────────────────── Fingerprint Comparison ──────────────────────╮
│ Source: v1.0.0-fingerprint.json                                     │
│ Target: v1.1.0-fingerprint.json                                     │
│ Status: ✅ SIMILAR (97.5% similarity)                               │
╰─────────────────────────────────────────────────────────────────────╯

             Comparison Summary
┌─────────────────────────┬────────────┐
│ Identical Responses     │ 39/40      │
│ Different Responses     │ 1/40       │
│ Similarity Score        │ 97.5%      │
│ Latency Change          │ -5.2%      │
└─────────────────────────┴────────────┘

Response Differences
┏━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Prompt    ┃ Difference                                              ┃
┡━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ math-007  │ Minor formatting change in step-by-step explanation     │
└───────────┴─────────────────────────────────────────────────────────┘
```

---

### `cluster` - Kubernetes Compatibility

Scan Kubernetes cluster nodes for NIM compatibility.

**Usage:**
```bash
nim-audit cluster --image <image> [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--image, -i` | NIM image reference (required) |
| `--kubeconfig, -k` | Path to kubeconfig file |
| `--namespace, -n` | Kubernetes namespace |
| `--context, -c` | Kubernetes context |
| `--format, -f` | Output format: terminal, json |

**Examples:**

```bash
# Scan cluster with default kubeconfig
nim-audit cluster --image nvcr.io/nim/llama3:1.1.0

# Use specific kubeconfig
nim-audit cluster --image nvcr.io/nim/llama3:1.1.0 \
                  --kubeconfig ~/.kube/prod-config

# Use specific context
nim-audit cluster --image nvcr.io/nim/llama3:1.1.0 \
                  --context production-cluster

# JSON output for automation
nim-audit cluster --image nvcr.io/nim/llama3:1.1.0 --format json
```

**Sample Output:**
```
╭────────────────────────── Cluster Scan ─────────────────────────────╮
│ Image: nvcr.io/nim/llama3:1.1.0                                     │
│ Compatible Nodes: 3/5                                               │
╰─────────────────────────────────────────────────────────────────────╯

                        Node Compatibility
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Node              ┃ GPU     ┃ Count   ┃ Status    ┃ Issues         ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ gpu-node-01       │ A100    │ 8       │ ✅ Pass   │ -              │
│ gpu-node-02       │ A100    │ 8       │ ✅ Pass   │ -              │
│ gpu-node-03       │ A10     │ 4       │ ✅ Pass   │ -              │
│ gpu-node-04       │ T4      │ 4       │ ❌ Fail   │ Memory < 24GB  │
│ gpu-node-05       │ V100    │ 8       │ ❌ Fail   │ Driver 470.x   │
└───────────────────┴─────────┴─────────┴───────────┴────────────────┘

⚠️  Warnings
  - 2 nodes are not compatible with this image
  - gpu-node-04: Consider upgrading to A10 or higher
  - gpu-node-05: Driver upgrade required (525.0+)
```

---

### `env` - Environment Variable Tools

Comprehensive environment variable analysis suite.

#### `env lint`

Lint environment variables against registry and custom rules.

**Usage:**
```bash
nim-audit env lint --env-file <file> [OPTIONS]
```

**Options:**
| Option | Description |
|--------|-------------|
| `--env-file, -e` | Path to .env file (required) |
| `--rules, -r` | Custom rules YAML file |
| `--registry` | Custom registry YAML file |
| `--format, -f` | Output format: terminal, json |

**Examples:**

```bash
# Basic lint
nim-audit env lint --env-file production.env

# With custom rules
nim-audit env lint --env-file production.env --rules rules.yaml

# JSON output
nim-audit env lint --env-file production.env --format json
```

**Sample Output:**
```
╭───────────────────── Environment Lint Report ───────────────────────╮
│ File: production.env                                                │
│ Status: ⚠️  WARN                                                    │
╰─────────────────────────────────────────────────────────────────────╯

    Summary
┌──────────┬───┐
│ Failures │ 0 │
│ Warnings │ 2 │
│ Info     │ 0 │
└──────────┴───┘

                              Findings
┏━━━━━━━━━━┳━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┓
┃ Severity ┃ ID            ┃ Variable           ┃ Message              ┃
┡━━━━━━━━━━╇━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━┩
│ WARN     │ ENV-UNKNOWN   │ CUSTOM_SETTING     │ Not in registry      │
│ WARN     │ ENV-MEMORY    │ NIM_MAX_BATCH_SIZE │ Increases memory     │
└──────────┴───────────────┴────────────────────┴──────────────────────┘
```

#### `env describe`

Get detailed information about a known environment variable.

**Usage:**
```bash
nim-audit env describe <variable-name>
```

**Examples:**

```bash
# Describe a variable
nim-audit env describe NIM_MAX_BATCH_SIZE

# JSON output
nim-audit env describe NIM_TENSOR_PARALLEL_SIZE --format json
```

**Sample Output:**
```
╭─────────────────────── Environment Variable ────────────────────────╮
│ NIM_MAX_BATCH_SIZE                                                  │
╰─────────────────────────────────────────────────────────────────────╯

 Type             int
 Scope            runtime
 Default          4
 Confidence       MED
 Precedence       env_file > runtime_params > image_default

Affects
  - throughput: +
  - latency: ±
  - memory: ++

⚠️  Failure Modes
  ! Too high can trigger OOM (KV cache / activations).
```

#### `env diff`

Compare two environment files with risk assessment.

**Usage:**
```bash
nim-audit env diff <old.env> <new.env> [OPTIONS]
```

**Examples:**

```bash
# Compare environment files
nim-audit env diff staging.env production.env

# JSON output
nim-audit env diff staging.env production.env --format json
```

**Sample Output:**
```
╭────────────────────────── Environment Diff ─────────────────────────╮
│ Old: staging.env                                                    │
│ New: production.env                                                 │
╰─────────────────────────────────────────────────────────────────────╯

    Summary
┌─────────┬───┐
│ Added   │ 1 │
│ Removed │ 0 │
│ Changed │ 2 │
│ Risky   │ 1 │
└─────────┴───┘

Added Variables
  + NIM_TENSOR_PARALLEL_SIZE

               Changed Variables
┏━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┓
┃ Variable             ┃ Old Value ┃ New Value ┃
┡━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━┩
│ NIM_MAX_BATCH_SIZE   │ 4         │ 32        │
│ NIM_LOG_LEVEL        │ DEBUG     │ INFO      │
└──────────────────────┴───────────┴───────────┘
```

#### `env registry-list`

List all known environment variables in the registry.

**Usage:**
```bash
nim-audit env registry-list [OPTIONS]
```

**Examples:**

```bash
# List all variables
nim-audit env registry-list

# JSON output
nim-audit env registry-list --format json
```

---

## Real-World Use Cases

### Use Case 1: Pre-Upgrade Validation

Before upgrading NIM in production, validate compatibility and understand changes:

```bash
# Step 1: Check what changed
nim-audit diff nvcr.io/nim/llama3:1.0.0 nvcr.io/nim/llama3:1.1.0 \
    --format markdown --output upgrade-notes.md

# Step 2: Verify GPU compatibility
nim-audit compat --image nvcr.io/nim/llama3:1.1.0 --gpu A100

# Step 3: Compare environment requirements
nim-audit env diff current.env recommended.env

# Step 4: Behavioral testing (if needed)
nim-audit fingerprint compare v1.0.0.json v1.1.0.json
```

### Use Case 2: CI/CD Pipeline Integration

Add nim-audit to your CI/CD pipeline:

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
        run: nim-audit env lint --env-file .env.nim --format json

      - name: Check compatibility
        run: |
          nim-audit compat \
            --image ${{ vars.NIM_IMAGE }} \
            --gpu A100 \
            --format json

      - name: Policy check
        run: |
          nim-audit lint \
            --image ${{ vars.NIM_IMAGE }} \
            --policy policies/enterprise.yaml \
            --format json
```

### Use Case 3: Kubernetes Deployment Planning

Before deploying to a new cluster:

```bash
# Scan entire cluster
nim-audit cluster --image nvcr.io/nim/llama3:1.1.0 \
    --kubeconfig ~/.kube/prod-config \
    --format json --output cluster-report.json

# Generate human-readable report
nim-audit cluster --image nvcr.io/nim/llama3:1.1.0 \
    --kubeconfig ~/.kube/prod-config
```

### Use Case 4: Environment Optimization

Optimize your NIM configuration:

```bash
# Analyze current configuration
nim-audit config --image nvcr.io/nim/llama3:1.1.0 \
    --env-file production.env --all

# Check specific variables
nim-audit env describe NIM_MAX_BATCH_SIZE
nim-audit env describe NIM_TENSOR_PARALLEL_SIZE

# Validate before applying changes
nim-audit env lint --env-file optimized.env

# Compare before/after
nim-audit env diff production.env optimized.env
```

### Use Case 5: Security and Compliance Audit

Regular security audits:

```bash
# Run compliance check
nim-audit lint --image nvcr.io/nim/llama3:1.1.0 \
    --policy security-policy.yaml \
    --severity error

# Check for sensitive variables
nim-audit env lint --env-file production.env \
    --rules security-rules.yaml
```

---

## Configuration

### Configuration File

Create `~/.nim-audit.yaml` or `.nim-audit.yaml` in your project:

```yaml
# Cache settings
cache:
  enabled: true
  directory: ~/.cache/nim-audit
  ttl: 3600  # seconds

# Registry settings
registry:
  default_registry: ngc
  ngc_api_key: ${NGC_API_KEY}  # Reference env var

# Output settings
output:
  default_format: terminal
  color: true
  verbose: false

# Lint settings
lint:
  include_builtin: true
  default_policy: ~/.nim-audit/enterprise.yaml
  fail_on_warning: false

# Image aliases for convenience
aliases:
  llama3: nvcr.io/nim/meta/llama3-8b-instruct:latest
  llama3-70b: nvcr.io/nim/meta/llama3-70b-instruct:latest
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `NGC_API_KEY` | NVIDIA NGC API key |
| `DOCKER_CONFIG` | Docker config directory |
| `NIM_AUDIT_CONFIG` | Override config file path |
| `NIM_AUDIT_CACHE_DIR` | Override cache directory |
| `NIM_AUDIT_NO_COLOR` | Disable colored output |

---

## Output Formats

All commands support multiple output formats:

### Terminal (Default)

Rich formatted output with colors and tables. Best for interactive use.

```bash
nim-audit diff image1 image2  # Default
nim-audit diff image1 image2 --format terminal
```

### JSON

Machine-readable JSON output. Best for CI/CD and automation.

```bash
nim-audit diff image1 image2 --format json
nim-audit diff image1 image2 --format json --output report.json
```

### Markdown

Markdown formatted reports. Best for documentation and PRs.

```bash
nim-audit diff image1 image2 --format markdown
nim-audit diff image1 image2 --format markdown --output CHANGELOG.md
```

---

## Troubleshooting

### Common Issues

#### "Image not found" errors

```bash
# For NGC images, ensure you're logged in
docker login nvcr.io

# Set NGC API key
export NGC_API_KEY=your-api-key
```

#### "Permission denied" for Docker

```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Or run with sudo (not recommended for production)
sudo nim-audit compat --image nvcr.io/nim/llama3:1.1.0
```

#### kubectl context issues

```bash
# Verify current context
kubectl config current-context

# Use specific context
nim-audit cluster --image nvcr.io/nim/llama3:1.1.0 \
    --context my-cluster
```

#### Cache issues

```bash
# Clear cache
rm -rf ~/.cache/nim-audit

# Disable cache temporarily
NIM_AUDIT_CACHE_DIR=/dev/null nim-audit diff image1 image2
```

### Getting Help

```bash
# General help
nim-audit --help

# Command-specific help
nim-audit diff --help
nim-audit env lint --help

# Version info
nim-audit version
```

### Debug Mode

Enable verbose output for troubleshooting:

```bash
nim-audit --verbose diff image1 image2
```

---

## Summary

nim-audit provides comprehensive auditing capabilities for NVIDIA NIM containers:

| Command | Purpose |
|---------|---------|
| `diff` | Compare versions, detect breaking changes |
| `config` | Analyze configuration impact |
| `compat` | Verify GPU/driver compatibility |
| `lint` | Validate against policies |
| `fingerprint` | Behavioral comparison |
| `cluster` | K8s cluster compatibility |
| `env` | Environment variable analysis |

Use nim-audit to ensure safe upgrades, optimal configurations, and policy compliance in your NIM deployments.
