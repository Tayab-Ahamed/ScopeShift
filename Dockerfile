FROM python:3.11-slim

# Prevent Python from writing bytecode and enable immediate log streaming
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOST=0.0.0.0 \
    PORT=8765 \
    CONTAINER=1

WORKDIR /app

# Install curl for healthcheck and ca-certificates for TLS
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies first for layer caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root system user and group
RUN addgroup --system scopeshift && adduser --system --group scopeshift

# Copy project files
COPY . .

# Ensure working directory and database permissions belong to non-root user
RUN chown -R scopeshift:scopeshift /app

# Run as non-root user
USER scopeshift

# Expose default HTTP port
EXPOSE 8765

# Container healthcheck querying /api/health
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://127.0.0.1:${PORT}/api/health || exit 1

# Start ScopeShift server
CMD ["python", "demo_server.py"]
