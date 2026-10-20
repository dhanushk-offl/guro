# Contributing to Guro

Thank you for your interest in contributing to Guro. This document outlines the technical standards and processes required for contributing to this project.

## Development Environment Setup

Use Python 3.9 or later. Package metadata and dependency groups live in `pyproject.toml`.

1. **Clone the repository**:
   ```bash
   git clone https://github.com/dhanushk-offl/guro.git
   cd guro
   ```

2. **Initialize a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**:
   ```bash
   pip install -e ".[test]"
   ```

## Architectural Guidelines

- **Statelessness**: Core logic (monitoring, benchmarking) should remain decoupled from the CLI interface where possible.
- **Robustness**: Subprocess calls (e.g., `nvidia-smi`, `sensors`) must handle exceptions and varying output formats gracefully. Always use UTF-8 decoding and prefer regex-free parsing when feasible.
- **UI Performance**: Updates to the TUI should be handled via `rich.live` to minimize terminal flickering. Large layouts should be split into logical components.

## Testing Standards

All new features or bug fixes must be accompanied by relevant unit or integration tests.

- **Mocking**: Use `unittest.mock` to simulate hardware environments (e.g., mocking sensor providers, vendor-command outputs, workloads, or clocks) to ensure tests can run on any CI/CD environment.
- **Execution**:
  ```bash
  python -m pytest tests/
  ```
- **Coverage**: Maintain or improve the current test coverage for core modules.
- **Workload isolation**: Unit tests must use controlled workloads and clocks rather than running full benchmark presets.
- **Package verification**: Build with `python -m build`, install the wheel in a separate environment, and smoke-test `guro --version` and `guro doctor --format json` outside the source checkout.

## Pull Request Process

1. **Branching**: Create a feature branch from `master` and target `master` in the pull request.
2. **Commit Messages**: Use descriptive, imperative commit messages (e.g., "Add support for integrated Intel GPUs").
3. **Verification**: Ensure all tests pass and the code adheres to PEP 8 standards.
4. **Documentation**: Update the `README.md` or internal docstrings if your changes modify the public API or behavior.

## Code of Conduct

Maintain a professional and respectful environment for all contributors.

---
Technical questions can be directed to the repository maintainers through GitHub Issues.
