# Security Policy

## Supported Versions

AgentGate is currently in alpha status. Security updates are provided for the latest release only.

| Version | Supported          |
| ------- | ------------------ |
| 0.2.x   | :white_check_mark: |
| 0.1.x   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability in AgentGate, please report it responsibly:

### How to Report

1. **Email**: Send details to the repository maintainer (see GitHub profile)
2. **Include**:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Any suggested fixes (optional)

### What to Expect

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 7 days
- **Resolution Timeline**: Depends on severity (see below)

### Severity Levels

| Severity | Description | Target Resolution |
|----------|-------------|-------------------|
| Critical | Remote code execution, authentication bypass | 24-48 hours |
| High | Data exposure, privilege escalation | 7 days |
| Medium | Denial of service, information disclosure | 30 days |
| Low | Minor issues, hardening recommendations | 90 days |

## Security Model

AgentGate implements a **containment-first** security architecture:

### Defense in Depth

1. **Policy Gates**: Every tool call is evaluated against OPA policies
2. **Kill Switches**: Real-time termination at session, tool, or global level
3. **Credential Brokering**: Time-bound, scope-limited access tokens
4. **Evidence Trails**: Append-only audit logs with cryptographic integrity

### Threat Model

AgentGate is designed to protect against:

- **Agent hijacking**: Malicious prompts causing unintended actions
- **Tool abuse**: Unauthorized use of sensitive tools
- **Policy bypass**: Attempts to circumvent security rules
- **Audit tampering**: Modification of evidence trails

### Known Limitations

This is a **reference implementation** and has limitations:

- Not hardened for production deployment
- Credential broker is a stub (integrate with Vault/KMS)
- Single-node only (no clustering)
- No compliance certifications (FedRAMP, SOC2, etc.)

## Security Best Practices

When deploying AgentGate:

### Configuration

```bash
# Generate secure keys
export AGENTGATE_ADMIN_API_KEY=$(openssl rand -hex 32)
export AGENTGATE_SIGNING_KEY=$(openssl rand -hex 32)
export AGENTGATE_APPROVAL_TOKEN=$(openssl rand -hex 16)
export AGENTGATE_WEBHOOK_SECRET=$(openssl rand -hex 32)
```

### Production Deployment

1. Use `docker-compose.prod.yml` for hardened containers
2. Run behind a reverse proxy with TLS
3. Enable rate limiting at the infrastructure level
4. Monitor `/metrics` endpoint for anomalies
5. Configure webhook alerts for kill switch activations

### Network Security

- Restrict Redis and OPA to internal networks only
- Use TLS for all external connections
- Implement IP allowlisting where possible

## Dependency Security

We maintain security through:

- **Automated scanning**: `pip-audit` in CI pipeline
- **SBOM generation**: CycloneDX bill of materials
- **Dependency updates**: Regular review of dependencies
- **Pre-commit hooks**: Security checks before commit

Generate an SBOM for your deployment:

```bash
make sbom
```

## Acknowledgments

We appreciate responsible security researchers who help improve AgentGate. Contributors who report valid security issues will be acknowledged (with permission) in release notes.

---

*This security policy is subject to change. Last updated: January 2026.*
