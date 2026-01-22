# Contributing to AgentGate

Thank you for your interest in contributing to AgentGate! This document provides guidelines and information for contributors.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md).

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:

1. A clear, descriptive title
2. Steps to reproduce the issue
3. Expected behavior vs actual behavior
4. Your environment (Python version, OS, etc.)
5. Any relevant logs or error messages

### Suggesting Features

Feature suggestions are welcome! Please open an issue with:

1. A clear description of the feature
2. The problem it solves or use case it addresses
3. Any implementation ideas you have

### Security Vulnerabilities

**Do not open public issues for security vulnerabilities.** Please see our [Security Policy](SECURITY.md) for responsible disclosure guidelines.

## Development Setup

### Prerequisites

- Python 3.12+
- Docker and Docker Compose
- Git

### Getting Started

```bash
# Clone the repository
git clone https://github.com/jlov7/agentgate.git
cd agentgate

# Create virtual environment and install dependencies
make setup

# Install pre-commit hooks
make install-hooks

# Start development services
make dev
```

### Running Tests

```bash
# Run all tests
make test

# Run adversarial security tests
make test-adversarial

# Run tests with coverage
make coverage
```

### Code Quality

We use several tools to maintain code quality:

```bash
# Run linter and type checker
make lint

# Auto-format code
make format

# Run all pre-commit hooks
make pre-commit

# Run security audit
make audit
```

## Pull Request Process

### Before Submitting

1. **Fork the repository** and create your branch from `main`
2. **Write tests** for any new functionality
3. **Run the full test suite** (`make test-all`)
4. **Run linting** (`make lint`)
5. **Update documentation** if needed
6. **Add a changelog entry** if the change is user-facing

### PR Guidelines

1. **Keep PRs focused** — One feature or fix per PR
2. **Write clear commit messages** — See [Conventional Commits](https://www.conventionalcommits.org/)
3. **Include tests** — All new code should have test coverage
4. **Update docs** — Keep README and docstrings current
5. **Be responsive** — Address review feedback promptly

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, etc.)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:
```
feat(metrics): add Prometheus endpoint
fix(killswitch): handle Redis connection timeout
docs(readme): add webhook configuration section
```

## Architecture Guidelines

### Code Style

- Follow PEP 8 with a line length of 100 characters
- Use type hints for all function signatures
- Write docstrings for all public functions and classes
- Keep functions focused and under 50 lines when possible

### Security Principles

AgentGate follows a "deny by default" security model:

1. **Fail closed** — If in doubt, deny the request
2. **Defense in depth** — Multiple layers of protection
3. **Least privilege** — Minimum necessary permissions
4. **Audit everything** — Log all decisions for review

### Testing Philosophy

1. **Unit tests** for individual components
2. **Adversarial tests** for security scenarios
3. **Integration tests** for end-to-end flows
4. **Test edge cases** and error conditions

## Project Structure

```
agentgate/
├── src/agentgate/          # Core implementation
│   ├── main.py             # FastAPI application
│   ├── gateway.py          # Request handling
│   ├── policy.py           # OPA integration
│   ├── killswitch.py       # Kill switch controller
│   ├── traces.py           # Trace store
│   ├── evidence.py         # Evidence exporter
│   ├── metrics.py          # Prometheus metrics
│   ├── webhooks.py         # Webhook notifications
│   └── models.py           # Pydantic models
├── policies/               # OPA/Rego policies
├── tests/                  # Test suite
│   ├── adversarial/        # Security tests
│   └── *.py                # Unit tests
├── demo/                   # Demo agent
└── examples/               # Sample outputs
```

## Getting Help

- **Questions**: Open a [Discussion](https://github.com/jlov7/agentgate/discussions)
- **Bugs**: Open an [Issue](https://github.com/jlov7/agentgate/issues)
- **Security**: See [SECURITY.md](SECURITY.md)

## License

By contributing, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).

---

Thank you for contributing to AgentGate! 🎉
