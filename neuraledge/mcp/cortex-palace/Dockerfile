# cortex-mcp — CORTEX-PALACE MCP bridge for NeuralEDGE Agent
# Slim Python 3.13. Runs the FastMCP server via stdio or SSE transport.

FROM python:3.13-slim AS base

# Build-time hygiene
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Non-root user so container DefaultRunAsUser policies pass.
RUN groupadd -r cortex && useradd -r -g cortex -d /app -s /usr/sbin/nologin cortex

WORKDIR /app

# Install runtime deps first for cache efficiency.
COPY pyproject.toml ./
RUN pip install --upgrade pip \
 && pip install \
        "mcp>=1.2.0" \
        "pydantic>=2.7" \
        "httpx>=0.27" \
        "anyio>=4.0" \
        "structlog>=24.1" \
        "python-dotenv>=1.0"

# App source.
COPY cortex_mcp ./cortex_mcp

# Install the package itself (no deps re-install).
RUN pip install --no-deps -e .

USER cortex

# Default mode is stub so the container is usable out of the box.
ENV CORTEX_MODE=stub \
    CORTEX_MCP_TRANSPORT=sse \
    HOST=0.0.0.0 \
    PORT=8765 \
    CORTEX_LOG_LEVEL=INFO

EXPOSE 8765

# Healthcheck calls the bridge's own status path. Stub mode always 0.
HEALTHCHECK --interval=30s --timeout=8s --start-period=10s --retries=3 \
  CMD python -m cortex_mcp.healthcheck || exit 1

ENTRYPOINT ["python", "-m", "cortex_mcp.server"]
