# AgentGate Production Dockerfile
# Multi-stage build for minimal, secure image

# Build stage
FROM python:3.12-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

# Production stage
FROM python:3.12-slim as production

# Security: Create non-root user
RUN groupadd --gid 1000 agentgate && \
    useradd --uid 1000 --gid 1000 --shell /bin/false agentgate

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --chown=agentgate:agentgate src/ ./src/
COPY --chown=agentgate:agentgate policies/ ./policies/

# Create directories for runtime data
RUN mkdir -p /app/traces && chown agentgate:agentgate /app/traces

# Security: Switch to non-root user
USER agentgate

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

# Expose port
EXPOSE 8000

# Environment defaults
ENV AGENTGATE_LOG_LEVEL=INFO \
    AGENTGATE_TRACE_DB=/app/traces/traces.db \
    AGENTGATE_POLICY_PATH=/app/policies \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Run the application
CMD ["python", "-m", "agentgate", "--host", "0.0.0.0", "--port", "8000"]
